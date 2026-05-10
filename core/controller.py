"""
Central controller implementing M-of-N consensus logic.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from config import settings
from core.database import (
    Trigger, TriggerEvent, Contact, Payload, SystemState,
    SessionLocal,
)
from core.notifications import NotificationEngine

logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    FIRED = "fired"


@dataclass
class ConsensusResult:
    total_triggers: int
    failed_triggers: int
    warning_triggers: int
    ok_triggers: int
    threshold_m: int
    should_fire: bool
    status: SystemStatus
    failed_trigger_names: List[str] = field(default_factory=list)


class EchoController:
    """
    Central controller for the Echo Protocol.
    Implements M-of-N consensus logic for dead man's switch.
    """

    def __init__(self):
        self.notification_engine = NotificationEngine()
        self.trigger_handlers = {}

    def register_trigger_handler(self, trigger_type: str, handler):
        """Register a trigger handler class."""
        self.trigger_handlers[trigger_type] = handler

    def check_trigger(self, trigger: Trigger, db: Session) -> str:
        """
        Check a single trigger's status.
        Returns: 'ok', 'warning', or 'failed'
        """
        handler_class = self.trigger_handlers.get(trigger.trigger_type)
        if not handler_class:
            logger.warning(f"No handler for trigger type: {trigger.trigger_type}")
            return "ok"

        handler = handler_class(trigger)

        try:
            last_activity = handler.get_last_activity()
            if last_activity:
                trigger.last_activity = last_activity

            trigger.last_check = datetime.utcnow()

            elapsed = 0.0
            if trigger.last_activity:
                elapsed = (datetime.utcnow() - trigger.last_activity).total_seconds()
                threshold = trigger.threshold_seconds
                warning_threshold = threshold * 0.75

                if elapsed >= threshold:
                    status = "failed"
                elif elapsed >= warning_threshold:
                    status = "warning"
                else:
                    status = "ok"
            else:
                status = "ok"

            # Log state change
            if status != trigger.status:
                event = TriggerEvent(
                    trigger_id=trigger.id,
                    event_type=status,
                    message=f"Status changed from {trigger.status} to {status}",
                    event_metadata={"elapsed_seconds": elapsed},
                )
                db.add(event)

            trigger.status = status
            db.commit()
            return status

        except Exception as e:
            logger.error(f"Error checking trigger {trigger.name}: {e}")
            return trigger.status  # Maintain previous status on error

    def evaluate_consensus(self, db: Session) -> ConsensusResult:
        """Evaluate M-of-N consensus across all enabled triggers."""
        triggers = db.query(Trigger).filter(Trigger.enabled == True).all()

        if not triggers:
            return ConsensusResult(
                total_triggers=0,
                failed_triggers=0,
                warning_triggers=0,
                ok_triggers=0,
                threshold_m=settings.CONSENSUS_M,
                should_fire=False,
                status=SystemStatus.OK,
            )

        failed = []
        warning = []
        ok = []

        for trigger in triggers:
            status = self.check_trigger(trigger, db)
            if status == "failed":
                failed.append(trigger.name)
            elif status == "warning":
                warning.append(trigger.name)
            else:
                ok.append(trigger.name)

        should_fire = len(failed) >= settings.CONSENSUS_M

        if should_fire:
            status = SystemStatus.FIRED
        elif failed:
            status = SystemStatus.CRITICAL
        elif warning:
            status = SystemStatus.WARNING
        else:
            status = SystemStatus.OK

        return ConsensusResult(
            total_triggers=len(triggers),
            failed_triggers=len(failed),
            warning_triggers=len(warning),
            ok_triggers=len(ok),
            threshold_m=settings.CONSENSUS_M,
            should_fire=should_fire,
            status=status,
            failed_trigger_names=failed,
        )

    def execute_switch(self, db: Session, consensus: ConsensusResult):
        """Execute the dead man's switch — release payloads and notify contacts."""
        logger.critical("EXECUTING DEAD MAN'S SWITCH")

        # Update system state
        state = db.query(SystemState).filter(SystemState.key == "switch_fired").first()
        if not state:
            state = SystemState(key="switch_fired", value="true")
            db.add(state)
        else:
            state.value = "true"

        fired_state = SystemState(
            key="switch_fired_at",
            value=datetime.utcnow().isoformat(),
        )
        db.merge(fired_state)
        db.commit()

        contacts = (
            db.query(Contact)
            .filter(Contact.enabled == True)
            .order_by(Contact.priority)
            .all()
        )
        payloads = db.query(Payload).filter(Payload.released == False).all()

        subject = "⚠️ ECHO PROTOCOL ACTIVATED"
        message = (
            f"This is an automated message from the Echo Protocol dead man's switch system.\n\n"
            f"The switch has been triggered because {consensus.failed_triggers} out of "
            f"{consensus.total_triggers} activity monitors failed to detect activity "
            f"within their configured thresholds.\n\n"
            f"Failed monitors: {', '.join(consensus.failed_trigger_names)}\n\n"
            f"Triggered at: {datetime.utcnow().isoformat()} UTC\n\n"
            f"Payloads released:\n"
        )

        for payload in payloads:
            payload.released = True
            payload.released_at = datetime.utcnow()
            message += f"\n- {payload.name} ({payload.payload_type})"
            if payload.payload_type == "message":
                message += f"\n  Content: {payload.content_encrypted}"

        db.commit()

        results = self.notification_engine.notify_contacts(
            contacts=contacts,
            subject=subject,
            message=message,
            payload_data={
                "fired_at": datetime.utcnow().isoformat(),
                "failed_triggers": consensus.failed_trigger_names,
                "payloads_released": [p.name for p in payloads],
            },
        )

        success_count = sum(1 for r in results if r.success)
        logger.info(f"Notifications sent: {success_count}/{len(results)} successful")
        return results

    def record_activity(self, trigger_id: int, db: Session) -> bool:
        """Record activity for a specific trigger (manual check-in)."""
        trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            return False

        trigger.last_activity = datetime.utcnow()
        trigger.status = "ok"

        event = TriggerEvent(
            trigger_id=trigger.id,
            event_type="activity",
            message="Manual activity recorded",
        )
        db.add(event)
        db.commit()
        return True

    def reset_system(self, db: Session) -> bool:
        """Reset the system after a false positive or test."""
        triggers = db.query(Trigger).all()
        for trigger in triggers:
            trigger.status = "ok"
            trigger.last_activity = datetime.utcnow()

        # Use synchronize_session='fetch' for safety with SQLAlchemy 2.x
        db.query(SystemState).filter(
            SystemState.key.in_(["switch_fired", "switch_fired_at", "last_critical_warning"])
        ).delete(synchronize_session="fetch")

        payloads = db.query(Payload).filter(Payload.released == True).all()
        for payload in payloads:
            payload.released = False
            payload.released_at = None

        db.commit()
        logger.info("System reset completed")
        return True

    def run_check_cycle(self):
        """Run a complete check cycle — evaluate all triggers and fire if needed."""
        db = SessionLocal()
        try:
            fired_state = db.query(SystemState).filter(
                SystemState.key == "switch_fired"
            ).first()

            if fired_state and fired_state.value == "true":
                logger.info("Switch already fired, skipping check cycle")
                return

            consensus = self.evaluate_consensus(db)

            logger.info(
                f"Check cycle complete: {consensus.ok_triggers} OK, "
                f"{consensus.warning_triggers} warning, {consensus.failed_triggers} failed"
            )

            if consensus.should_fire:
                grace_seconds = settings.CHECK_INTERVAL * settings.GRACE_PERIOD_MULTIPLIER

                last_warning = db.query(SystemState).filter(
                    SystemState.key == "last_critical_warning"
                ).first()

                if not last_warning:
                    last_warning = SystemState(
                        key="last_critical_warning",
                        value=datetime.utcnow().isoformat(),
                    )
                    db.add(last_warning)
                    db.commit()
                    logger.warning("Critical state detected, starting grace period")
                else:
                    warning_time = datetime.fromisoformat(last_warning.value)
                    elapsed = (datetime.utcnow() - warning_time).total_seconds()

                    if elapsed >= grace_seconds:
                        self.execute_switch(db, consensus)
                    else:
                        remaining = grace_seconds - elapsed
                        logger.warning(
                            f"Critical state continues, {remaining:.0f}s remaining in grace period"
                        )
            else:
                db.query(SystemState).filter(
                    SystemState.key == "last_critical_warning"
                ).delete(synchronize_session="fetch")
                db.commit()

        finally:
            db.close()

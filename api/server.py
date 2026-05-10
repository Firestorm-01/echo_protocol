"""
REST API server for the Echo Protocol.
"""

import logging
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from config import settings
from core.database import (
    init_db, SessionLocal, Trigger, Contact, Payload, TriggerEvent, SystemState,
)
from core.controller import EchoController
from triggers import TRIGGER_REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="../dashboard/templates")
CORS(app)
app.secret_key = settings.API_SECRET_KEY

controller = EchoController()
for _type, _cls in TRIGGER_REGISTRY.items():
    controller.register_trigger_handler(_type, _cls)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def require_api_key(f):
    """Decorator: require X-API-Key header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != settings.API_SECRET_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
def get_status():
    db = SessionLocal()
    try:
        consensus = controller.evaluate_consensus(db)
        fired_state = db.query(SystemState).filter(SystemState.key == "switch_fired").first()
        return jsonify({
            "status": consensus.status.value,
            "total_triggers": consensus.total_triggers,
            "ok_triggers": consensus.ok_triggers,
            "warning_triggers": consensus.warning_triggers,
            "failed_triggers": consensus.failed_triggers,
            "threshold_m": consensus.threshold_m,
            "should_fire": consensus.should_fire,
            "failed_trigger_names": consensus.failed_trigger_names,
            "switch_fired": fired_state.value == "true" if fired_state else False,
            "timestamp": datetime.utcnow().isoformat(),
        })
    finally:
        db.close()


@app.route("/api/reset", methods=["POST"])
@require_api_key
def reset_system():
    db = SessionLocal()
    try:
        controller.reset_system(db)
        return jsonify({"status": "reset", "timestamp": datetime.utcnow().isoformat()})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------

@app.route("/api/triggers", methods=["GET"])
def list_triggers():
    db = SessionLocal()
    try:
        triggers = db.query(Trigger).all()
        return jsonify({
            "triggers": [
                {
                    "id": t.id,
                    "name": t.name,
                    "type": t.trigger_type,
                    "enabled": t.enabled,
                    "status": t.status,
                    "threshold_seconds": t.threshold_seconds,
                    "last_activity": t.last_activity.isoformat() if t.last_activity else None,
                    "last_check": t.last_check.isoformat() if t.last_check else None,
                }
                for t in triggers
            ]
        })
    finally:
        db.close()


@app.route("/api/triggers", methods=["POST"])
@require_api_key
def create_trigger():
    data = request.json or {}
    trigger_type = data.get("type")
    if trigger_type not in TRIGGER_REGISTRY:
        return jsonify({"error": f"Unknown trigger type: {trigger_type}"}), 400

    db = SessionLocal()
    try:
        defaults = settings.TRIGGER_DEFAULTS.get(trigger_type, {})
        trigger = Trigger(
            name=data.get("name", f"{trigger_type} Trigger"),
            trigger_type=trigger_type,
            enabled=data.get("enabled", True),
            threshold_seconds=data.get(
                "threshold_seconds", defaults.get("threshold_seconds", 86400)
            ),
            config=data.get("config", {}),
            last_activity=datetime.utcnow(),
        )
        db.add(trigger)
        db.commit()
        db.refresh(trigger)
        return jsonify({"id": trigger.id, "name": trigger.name, "type": trigger.trigger_type, "status": "created"}), 201
    finally:
        db.close()


@app.route("/api/triggers/<int:trigger_id>", methods=["GET"])
def get_trigger(trigger_id: int):
    db = SessionLocal()
    try:
        trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            return jsonify({"error": "Trigger not found"}), 404
        return jsonify({
            "id": trigger.id,
            "name": trigger.name,
            "type": trigger.trigger_type,
            "enabled": trigger.enabled,
            "status": trigger.status,
            "threshold_seconds": trigger.threshold_seconds,
            "config": trigger.config,
            "last_activity": trigger.last_activity.isoformat() if trigger.last_activity else None,
            "last_check": trigger.last_check.isoformat() if trigger.last_check else None,
            "created_at": trigger.created_at.isoformat(),
        })
    finally:
        db.close()


@app.route("/api/triggers/<int:trigger_id>", methods=["PATCH"])
@require_api_key
def update_trigger(trigger_id: int):
    data = request.json or {}
    db = SessionLocal()
    try:
        trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            return jsonify({"error": "Trigger not found"}), 404

        if "name" in data:
            trigger.name = data["name"]
        if "enabled" in data:
            trigger.enabled = data["enabled"]
        if "threshold_seconds" in data:
            trigger.threshold_seconds = data["threshold_seconds"]
        if "config" in data:
            # Merge existing config with new values
            merged = dict(trigger.config or {})
            merged.update(data["config"])
            trigger.config = merged

        db.commit()
        return jsonify({"status": "updated", "id": trigger_id})
    finally:
        db.close()


@app.route("/api/triggers/<int:trigger_id>", methods=["DELETE"])
@require_api_key
def delete_trigger(trigger_id: int):
    db = SessionLocal()
    try:
        trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            return jsonify({"error": "Trigger not found"}), 404
        db.delete(trigger)
        db.commit()
        return jsonify({"status": "deleted", "id": trigger_id})
    finally:
        db.close()


@app.route("/api/triggers/<int:trigger_id>/activity", methods=["POST"])
def record_trigger_activity(trigger_id: int):
    db = SessionLocal()
    try:
        trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            return jsonify({"error": "Trigger not found"}), 404

        handler_class = TRIGGER_REGISTRY.get(trigger.trigger_type)
        result = {"status": "recorded", "timestamp": datetime.utcnow().isoformat()}

        if handler_class:
            handler = handler_class(trigger)
            data = request.json or {}

            if hasattr(handler, "checkin"):
                result = handler.checkin()
            elif hasattr(handler, "report_activity"):
                result = handler.report_activity(data.get("minutes", 1))
            elif hasattr(handler, "record_heartbeat"):
                result = handler.record_heartbeat(data.get("device_id", "default"))
            elif hasattr(handler, "update_location"):
                result = handler.update_location(data.get("lat"), data.get("lon"))

            # Persist any config mutations back to DB
            trigger.config = handler.config

        trigger.last_activity = datetime.utcnow()
        trigger.status = "ok"
        db.commit()
        return jsonify(result)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

@app.route("/api/contacts", methods=["GET"])
def list_contacts():
    db = SessionLocal()
    try:
        contacts = db.query(Contact).order_by(Contact.priority).all()
        return jsonify({
            "contacts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "email": c.email,
                    "phone": c.phone,
                    "webhook_url": c.webhook_url,
                    "priority": c.priority,
                    "enabled": c.enabled,
                }
                for c in contacts
            ]
        })
    finally:
        db.close()


@app.route("/api/contacts", methods=["POST"])
@require_api_key
def create_contact():
    data = request.json or {}
    db = SessionLocal()
    try:
        contact = Contact(
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            webhook_url=data.get("webhook_url"),
            priority=data.get("priority", 1),
            enabled=data.get("enabled", True),
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return jsonify({"id": contact.id, "status": "created"}), 201
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

@app.route("/api/payloads", methods=["GET"])
@require_api_key
def list_payloads():
    db = SessionLocal()
    try:
        payloads = db.query(Payload).all()
        return jsonify({
            "payloads": [
                {
                    "id": p.id,
                    "name": p.name,
                    "type": p.payload_type,
                    "released": p.released,
                    "released_at": p.released_at.isoformat() if p.released_at else None,
                    "created_at": p.created_at.isoformat(),
                }
                for p in payloads
            ]
        })
    finally:
        db.close()


@app.route("/api/payloads", methods=["POST"])
@require_api_key
def create_payload():
    data = request.json or {}
    db = SessionLocal()
    try:
        payload = Payload(
            name=data.get("name"),
            payload_type=data.get("type", "message"),
            content_encrypted=data.get("content"),   # encrypt in production
            recipients=data.get("recipients", []),
        )
        db.add(payload)
        db.commit()
        db.refresh(payload)
        return jsonify({"id": payload.id, "status": "created"}), 201
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Trigger type info
# ---------------------------------------------------------------------------

@app.route("/api/trigger-types", methods=["GET"])
def list_trigger_types():
    return jsonify({
        "trigger_types": {
            name: {
                "config_schema": cls.get_config_schema(),
                "default_threshold": settings.TRIGGER_DEFAULTS.get(name, {}).get(
                    "threshold_seconds", 86400
                ),
            }
            for name, cls in TRIGGER_REGISTRY.items()
        }
    })


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


def run_server():
    init_db()
    app.run(host=settings.API_HOST, port=settings.API_PORT, debug=False)


if __name__ == "__main__":
    run_server()

#!/usr/bin/env python3
"""
Echo Protocol — Dead Man's Switch System
Main entry point: runs the API server and background scheduler.
"""

import logging
import signal
import sys

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings
from core.database import init_db
from core.controller import EchoController
from triggers import TRIGGER_REGISTRY
from api.server import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("echo_protocol.log"),
    ],
)
logger = logging.getLogger(__name__)

controller = EchoController()


def setup_controller():
    for trigger_type, handler_class in TRIGGER_REGISTRY.items():
        controller.register_trigger_handler(trigger_type, handler_class)
    logger.info(f"Registered {len(TRIGGER_REGISTRY)} trigger handlers")


def run_check_cycle():
    try:
        controller.run_check_cycle()
    except Exception as e:
        logger.error(f"Error in check cycle: {e}", exc_info=True)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_check_cycle,
        "interval",
        seconds=settings.CHECK_INTERVAL,
        id="main_check_cycle",
        name="Main trigger check cycle",
        replace_existing=True,
    )
    return scheduler


def signal_handler(signum, frame):
    logger.info("Shutdown signal received, cleaning up…")
    sys.exit(0)


def main():
    logger.info("=" * 60)
    logger.info("Starting Echo Protocol Dead Man's Switch System")
    logger.info("=" * 60)

    init_db()
    setup_controller()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Background scheduler started")

    # Run an immediate check on startup
    run_check_cycle()

    logger.info(f"Starting API server on {settings.API_HOST}:{settings.API_PORT}")
    logger.info("Dashboard → http://localhost:5000")

    try:
        app.run(
            host=settings.API_HOST,
            port=settings.API_PORT,
            debug=False,
            use_reloader=False,   # prevent duplicate scheduler on reload
        )
    finally:
        scheduler.shutdown()
        logger.info("Echo Protocol shutdown complete")


if __name__ == "__main__":
    main()

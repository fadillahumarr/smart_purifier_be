import asyncio
import logging

from app.workers.alert_worker import run_alert_worker

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    asyncio.run(run_alert_worker())

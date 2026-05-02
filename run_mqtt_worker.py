import asyncio
import logging

from app.workers.mqtt_worker import run_mqtt_worker

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    asyncio.run(run_mqtt_worker())

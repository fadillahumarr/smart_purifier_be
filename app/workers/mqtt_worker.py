import asyncio
import json
import logging

import aiomqtt
from pydantic import ValidationError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.schemas.mqtt import (
    MqttAIDecisionPayload,
    MqttCycleResultPayload,
    MqttCycleStatePayload,
    MqttDeviceStatusPayload,
    MqttSensorReadingsPayload,
)
from app.services.mqtt_service import (
    handle_ai_decision,
    handle_cycle_result,
    handle_cycle_state,
    handle_device_status,
    handle_sensor_readings,
)

logger = logging.getLogger(__name__)

TOPIC_STATUS = "smart-water/+/status"
TOPIC_CYCLE_STATE = "smart-water/+/cycle/state"
TOPIC_SENSORS = "smart-water/+/sensors"
TOPIC_AI_DECISION = "smart-water/+/ai-decision"
TOPIC_CYCLE_RESULT = "smart-water/+/cycle/result"


async def process_message(topic: str, payload_bytes: bytes) -> None:
    payload_raw = payload_bytes.decode("utf-8")
    data = json.loads(payload_raw)

    async with AsyncSessionLocal() as session:
        if topic.endswith("/status"):
            payload = MqttDeviceStatusPayload.model_validate(data)
            await handle_device_status(session, payload)
            return

        if topic.endswith("/cycle/state"):
            payload = MqttCycleStatePayload.model_validate(data)
            await handle_cycle_state(session, payload)
            return

        if topic.endswith("/sensors"):
            payload = MqttSensorReadingsPayload.model_validate(data)
            await handle_sensor_readings(session, payload)
            return

        if topic.endswith("/ai-decision"):
            payload = MqttAIDecisionPayload.model_validate(data)
            await handle_ai_decision(session, payload)
            return

        if topic.endswith("/cycle/result"):
            payload = MqttCycleResultPayload.model_validate(data)
            await handle_cycle_result(session, payload)
            return

        logger.warning("Unhandled MQTT topic: %s", topic)


async def run_mqtt_worker() -> None:
    while True:
        try:
            logger.info("Connecting to MQTT broker %s:%s",
                        settings.MQTT_HOST, settings.MQTT_PORT)

            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USERNAME or None,
                password=settings.MQTT_PASSWORD or None,
            ) as client:
                await client.subscribe(TOPIC_STATUS)
                await client.subscribe(TOPIC_CYCLE_STATE)
                await client.subscribe(TOPIC_SENSORS)
                await client.subscribe(TOPIC_AI_DECISION)
                await client.subscribe(TOPIC_CYCLE_RESULT)

                logger.info("MQTT subscribed to all topics")

                async for message in client.messages:
                    try:
                        await process_message(str(message.topic), message.payload)
                    except ValidationError as e:
                        logger.exception(
                            "Invalid MQTT payload on topic %s: %s", message.topic, e)
                    except Exception:
                        logger.exception(
                            "Failed processing MQTT message on topic %s", message.topic)

        except Exception:
            logger.exception(
                "MQTT worker disconnected, retrying in 5 seconds...")
            await asyncio.sleep(5)

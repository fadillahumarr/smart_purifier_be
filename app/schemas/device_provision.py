from pydantic import BaseModel, Field


class DeviceProvisionRequest(BaseModel):
    mac_address: str = Field(max_length=50)
    firmware_version: str | None = None


class DeviceProvisionResponse(BaseModel):
    device_code: str
    mqtt_topic_base: str
    mqtt_host: str
    mqtt_port: int

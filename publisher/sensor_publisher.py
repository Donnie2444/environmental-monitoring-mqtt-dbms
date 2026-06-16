import json
import os
import random
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "environmental/sensors")

SENSORS = [
    {"sensor_id": "S001", "location": "Room A"},
    {"sensor_id": "S002", "location": "Room B"},
    {"sensor_id": "S003", "location": "Laboratory"},
]


def create_sensor_reading() -> dict:
    """Create one simulated environmental sensor reading."""
    sensor = random.choice(SENSORS)

    return {
        "sensor_id": sensor["sensor_id"],
        "location": sensor["location"],
        "temperature": round(random.uniform(18.0, 38.0), 2),
        "humidity": round(random.uniform(35.0, 85.0), 2),
        "air_quality": random.randint(30, 180),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def main() -> None:
    client = mqtt.Client(client_id="environmental_sensor_publisher")
    client.connect(BROKER_HOST, BROKER_PORT)

    print(f"Connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
    print(f"Publishing sensor data to topic: {TOPIC}")
    print("Press CTRL+C to stop.\n")

    try:
        while True:
            reading = create_sensor_reading()
            message = json.dumps(reading)
            client.publish(TOPIC, message)
            print(f"Published: {message}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nPublisher stopped by user.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()

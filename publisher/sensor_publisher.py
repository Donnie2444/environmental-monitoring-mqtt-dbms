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

# One topic per database. The topic decides WHICH database stores the message,
# and each topic carries a DIFFERENT KIND of data.
TOPIC_NETWORK = os.getenv("MQTT_TOPIC_NETWORK", "environmental/network")        # -> Neo4j  (topology)
TOPIC_READINGS = os.getenv("MQTT_TOPIC_READINGS", "environmental/readings")     # -> MySQL  (measurements + alerts)
TOPIC_TELEMETRY = os.getenv("MQTT_TOPIC_TELEMETRY", "environmental/telemetry")  # -> MongoDB (raw + metadata)

# Sensor topology. Sent to Neo4j. Describes WHERE each sensor sits.
SENSOR_NETWORK = [
    {"sensor_id": "S001", "sensor_type": "Environmental Sensor",
     "room": "Room A", "floor": 1, "building": "Computer Science Building"},
    {"sensor_id": "S002", "sensor_type": "Environmental Sensor",
     "room": "Room B", "floor": 1, "building": "Computer Science Building"},
    {"sensor_id": "S003", "sensor_type": "Environmental Sensor",
     "room": "Laboratory", "floor": 2, "building": "Computer Science Building"},
]

FIRMWARE_VERSIONS = ["v1.0.3", "v1.2.0", "v2.0.1"]


def publish_network(client) -> None:
    """Send the sensor topology to Neo4j (re-sent periodically; MERGE makes it safe)."""
    for node in SENSOR_NETWORK:
        client.publish(TOPIC_NETWORK, json.dumps(node))
    print("Published sensor network (topology) -> Neo4j")


def create_reading() -> dict:
    """One measurement. Goes to MySQL, which auto-generates the reading_id."""
    sensor = random.choice(SENSOR_NETWORK)
    return {
        "sensor_id": sensor["sensor_id"],
        "temperature": round(random.uniform(18.0, 38.0), 2),
        "humidity": round(random.uniform(35.0, 85.0), 2),
        "air_quality": random.randint(30, 180),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_telemetry(reading: dict) -> dict:
    """Raw device message for MongoDB, with flexible metadata that varies per message."""
    document = {
        "sensor_id": reading["sensor_id"],
        "temperature": reading["temperature"],
        "humidity": reading["humidity"],
        "air_quality": reading["air_quality"],
        "timestamp": reading["timestamp"],
        "device": {
            "battery_level": random.randint(20, 100),
            "firmware_version": random.choice(FIRMWARE_VERSIONS),
        },
    }
    if random.random() < 0.5:
        document["device"]["signal_strength_dbm"] = random.randint(-90, -40)
    if random.random() < 0.25:
        document["device"]["error_code"] = random.choice(
            ["E12_SENSOR_DRIFT", "E05_LOW_BATTERY", "E21_TIMEOUT"]
        )
    if random.random() < 0.15:
        document["maintenance_note"] = "Calibration recommended"
    return document


def main() -> None:
    client = mqtt.Client(client_id="environmental_sensor_publisher")
    client.connect(BROKER_HOST, BROKER_PORT)
    client.loop_start()

    print(f"Connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
    print("Publishing to topics:")
    print(f"  - {TOPIC_NETWORK}   (topology      -> Neo4j)")
    print(f"  - {TOPIC_READINGS}  (measurements  -> MySQL)")
    print(f"  - {TOPIC_TELEMETRY} (raw telemetry -> MongoDB)")
    print("Press CTRL+C to stop.\n")

    publish_network(client)

    cycle = 0
    try:
        while True:
            reading = create_reading()
            telemetry = build_telemetry(reading)

            client.publish(TOPIC_READINGS, json.dumps(reading))
            client.publish(TOPIC_TELEMETRY, json.dumps(telemetry))

            print(
                f"Published | Sensor={reading['sensor_id']} | "
                f"Temp={reading['temperature']} | Humidity={reading['humidity']} | "
                f"AQ={reading['air_quality']} -> readings (MySQL) + telemetry (MongoDB)"
            )

            cycle += 1
            if cycle % 20 == 0:
                publish_network(client)

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nPublisher stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

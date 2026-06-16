import json
import os
from datetime import datetime
from typing import Optional, Tuple

import mysql.connector
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pymongo import MongoClient

load_dotenv()

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "environmental/sensors")

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3308")),
    "user": os.getenv("MYSQL_USER", "envuser"),
    "password": os.getenv("MYSQL_PASSWORD", "envpass"),
    "database": os.getenv("MYSQL_DATABASE", "env_monitoring"),
}

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://root:rootpass@localhost:27018/")
MONGODB_DB = os.getenv("MONGODB_DB", "env_monitoring")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "sensor_messages")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

mysql_connection = mysql.connector.connect(**MYSQL_CONFIG)
mongo_client = MongoClient(MONGODB_URI)
mongo_collection = mongo_client[MONGODB_DB][MONGODB_COLLECTION]
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def classify_reading(temperature: float, humidity: float, air_quality: int) -> Tuple[str, Optional[str], Optional[str]]:
    """Classify the reading and return status, alert_type, and alert_message."""
    if temperature > 35:
        return "DANGER", "HIGH_TEMPERATURE", "Temperature is above the dangerous threshold."

    if humidity > 80:
        return "DANGER", "HIGH_HUMIDITY", "Humidity is above the dangerous threshold."

    if air_quality > 150:
        return "DANGER", "POOR_AIR_QUALITY", "Air quality is poor and above the dangerous threshold."

    if temperature > 30 or humidity > 70 or air_quality > 100:
        return "WARNING", "ENVIRONMENT_WARNING", "One or more environmental values are above the normal range."

    return "NORMAL", None, None


def insert_mysql(data: dict, status: str, alert_type: Optional[str], alert_message: Optional[str]) -> int:
    cursor = mysql_connection.cursor()

    insert_reading_query = """
        INSERT INTO readings
        (sensor_id, temperature, humidity, air_quality, reading_time, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        insert_reading_query,
        (
            data["sensor_id"],
            data["temperature"],
            data["humidity"],
            data["air_quality"],
            data["timestamp"],
            status,
        ),
    )

    reading_id = cursor.lastrowid

    if alert_type and alert_message:
        insert_alert_query = """
            INSERT INTO alerts
            (reading_id, sensor_id, alert_type, message, alert_time)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(
            insert_alert_query,
            (reading_id, data["sensor_id"], alert_type, alert_message, data["timestamp"]),
        )

    mysql_connection.commit()
    cursor.close()
    return reading_id


def insert_mongodb(data: dict, status: str, alert_type: Optional[str], alert_message: Optional[str], reading_id: int) -> None:
    document = {
        "mysql_reading_id": reading_id,
        "sensor_id": data["sensor_id"],
        "location": data["location"],
        "temperature": data["temperature"],
        "humidity": data["humidity"],
        "air_quality": data["air_quality"],
        "timestamp": data["timestamp"],
        "status": status,
        "alert": {
            "alert_type": alert_type,
            "message": alert_message,
        } if alert_type else None,
        "stored_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    mongo_collection.insert_one(document)


def insert_neo4j(data: dict, status: str, alert_type: Optional[str], alert_message: Optional[str], reading_id: int) -> None:
    with neo4j_driver.session() as session:
        session.run(
            """
            MERGE (s:Sensor {sensor_id: $sensor_id})
            SET s.sensor_type = 'Environmental Sensor'
            MERGE (l:Location {name: $location})
            MERGE (s)-[:LOCATED_IN]->(l)
            CREATE (r:Reading {
                reading_id: $reading_id,
                temperature: $temperature,
                humidity: $humidity,
                air_quality: $air_quality,
                timestamp: $timestamp,
                status: $status
            })
            CREATE (s)-[:PRODUCED]->(r)
            """,
            sensor_id=data["sensor_id"],
            location=data["location"],
            reading_id=reading_id,
            temperature=data["temperature"],
            humidity=data["humidity"],
            air_quality=data["air_quality"],
            timestamp=data["timestamp"],
            status=status,
        )

        if alert_type and alert_message:
            session.run(
                """
                MATCH (r:Reading {reading_id: $reading_id})
                CREATE (a:Alert {
                    alert_type: $alert_type,
                    message: $alert_message,
                    timestamp: $timestamp
                })
                CREATE (r)-[:TRIGGERED]->(a)
                """,
                reading_id=reading_id,
                alert_type=alert_type,
                alert_message=alert_message,
                timestamp=data["timestamp"],
            )


def process_message(message_payload: bytes) -> None:
    data = json.loads(message_payload.decode("utf-8"))

    status, alert_type, alert_message = classify_reading(
        data["temperature"],
        data["humidity"],
        data["air_quality"],
    )

    reading_id = insert_mysql(data, status, alert_type, alert_message)
    insert_mongodb(data, status, alert_type, alert_message, reading_id)
    insert_neo4j(data, status, alert_type, alert_message, reading_id)

    print(
        f"Stored reading #{reading_id} | "
        f"Sensor={data['sensor_id']} | "
        f"Status={status} | "
        f"Temp={data['temperature']} | "
        f"Humidity={data['humidity']} | "
        f"AQ={data['air_quality']}"
    )


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        print(f"Subscribed to topic: {MQTT_TOPIC}\n")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    try:
        process_message(msg.payload)
    except Exception as error:
        print(f"Error processing message: {error}")


def main() -> None:
    client = mqtt.Client(client_id="environmental_monitoring_subscriber")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

    print("Subscriber is running. Press CTRL+C to stop.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nSubscriber stopped by user.")
    finally:
        mysql_connection.close()
        mongo_client.close()
        neo4j_driver.close()
        client.disconnect()


if __name__ == "__main__":
    main()

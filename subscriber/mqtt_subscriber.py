import json
import os
import time
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

# The topic a message arrives on decides which database stores it.
TOPIC_NETWORK = os.getenv("MQTT_TOPIC_NETWORK", "environmental/network")        # -> Neo4j
TOPIC_READINGS = os.getenv("MQTT_TOPIC_READINGS", "environmental/readings")     # -> MySQL
TOPIC_TELEMETRY = os.getenv("MQTT_TOPIC_TELEMETRY", "environmental/telemetry")  # -> MongoDB

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

# -------------------- Performance metrics (Track point 5) --------------------
PERF = {
    "MySQL":   {"count": 0, "total_ms": 0.0},
    "MongoDB": {"count": 0, "total_ms": 0.0},
    "Neo4j":   {"count": 0, "total_ms": 0.0},
}
FIRST_MESSAGE_TIME = None
ERROR_COUNT = 0


def classify_reading(temperature: float, humidity: float, air_quality: int) -> Tuple[str, Optional[str]]:
    """Classify a reading and return (status, alert_type). The human-readable
    message for each alert_type lives once in the MySQL alert_types table."""
    if temperature > 35:
        return "DANGER", "HIGH_TEMPERATURE"
    if humidity > 80:
        return "DANGER", "HIGH_HUMIDITY"
    if air_quality > 150:
        return "DANGER", "POOR_AIR_QUALITY"
    if temperature > 30 or humidity > 70 or air_quality > 100:
        return "WARNING", "ENVIRONMENT_WARNING"
    return "NORMAL", None


# -------------------- MySQL: structured readings + alerts --------------------
def insert_mysql(data: dict) -> Tuple[int, str]:
    """Insert the reading (auto-increment reading_id) and, if needed, the alert.
    The alert stores only alert_type; its message is looked up from alert_types.
    Returns (reading_id, status)."""
    status, alert_type = classify_reading(
        data["temperature"], data["humidity"], data["air_quality"]
    )

    cursor = mysql_connection.cursor()
    cursor.execute(
        """
        INSERT INTO readings
        (sensor_id, temperature, humidity, air_quality, reading_time, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (data["sensor_id"], data["temperature"], data["humidity"],
         data["air_quality"], data["timestamp"], status),
    )
    reading_id = cursor.lastrowid  # MySQL generated the id

    if alert_type:
        cursor.execute(
            """
            INSERT INTO alerts
            (reading_id, sensor_id, alert_type, alert_time)
            VALUES (%s, %s, %s, %s)
            """,
            (reading_id, data["sensor_id"], alert_type, data["timestamp"]),
        )

    mysql_connection.commit()
    cursor.close()
    return reading_id, status


# -------------------- MongoDB: raw telemetry + flexible metadata --------------------
def insert_mongodb(data: dict) -> None:
    """Store the raw device message exactly as it arrived (unprocessed)."""
    document = dict(data)
    document["stored_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mongo_collection.insert_one(document)


# -------------------- Neo4j: sensor / location network ONLY --------------------
def insert_neo4j_network(data: dict) -> None:
    """Build the topology graph: Sensor -> Room -> Floor -> Building."""
    with neo4j_driver.session() as session:
        session.run(
            """
            MERGE (b:Building {name: $building})
            MERGE (f:Floor {number: $floor})
            MERGE (r:Room {name: $room})
            MERGE (s:Sensor {sensor_id: $sensor_id})
            SET s.sensor_type = $sensor_type
            MERGE (f)-[:IN_BUILDING]->(b)
            MERGE (r)-[:ON_FLOOR]->(f)
            MERGE (s)-[:LOCATED_IN]->(r)
            """,
            sensor_id=data["sensor_id"], sensor_type=data["sensor_type"],
            room=data["room"], floor=data["floor"], building=data["building"],
        )


def record(target: str, elapsed_ms: float) -> None:
    """Accumulate timing for the performance summary."""
    PERF[target]["count"] += 1
    PERF[target]["total_ms"] += elapsed_ms


def route_message(topic: str, payload: bytes) -> None:
    """Send the message to the right database BASED ON ITS TOPIC, timing each write."""
    global FIRST_MESSAGE_TIME
    if FIRST_MESSAGE_TIME is None:
        FIRST_MESSAGE_TIME = time.time()

    data = json.loads(payload.decode("utf-8"))

    if topic == TOPIC_READINGS:
        start = time.perf_counter()
        reading_id, status = insert_mysql(data)
        ms = (time.perf_counter() - start) * 1000
        record("MySQL", ms)
        print(f"[MySQL  ] reading #{reading_id} | Sensor={data['sensor_id']} | "
              f"Status={status} | Temp={data['temperature']} | AQ={data['air_quality']} | {ms:.1f} ms")

    elif topic == TOPIC_TELEMETRY:
        start = time.perf_counter()
        insert_mongodb(data)
        ms = (time.perf_counter() - start) * 1000
        record("MongoDB", ms)
        extra = [k for k in ("error_code", "signal_strength_dbm") if k in data.get("device", {})]
        extra_note = f" | extra={','.join(extra)}" if extra else ""
        print(f"[MongoDB] Sensor={data['sensor_id']} | raw telemetry stored | {ms:.1f} ms{extra_note}")

    elif topic == TOPIC_NETWORK:
        start = time.perf_counter()
        insert_neo4j_network(data)
        ms = (time.perf_counter() - start) * 1000
        record("Neo4j", ms)
        print(f"[Neo4j  ] network | {data['sensor_id']} -> {data['room']} "
              f"-> Floor {data['floor']} -> {data['building']} | {ms:.1f} ms")

    else:
        print(f"Unknown topic '{topic}', message ignored.")


def print_performance_summary() -> None:
    """Print processing speed, per-database latency, and reliability (Track point 5)."""
    total = sum(db["count"] for db in PERF.values())
    elapsed = (time.time() - FIRST_MESSAGE_TIME) if FIRST_MESSAGE_TIME else 0.0

    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Run time:          {elapsed:.1f} s")
    print(f"Messages stored:   {total}  "
          f"(MySQL {PERF['MySQL']['count']}, "
          f"MongoDB {PERF['MongoDB']['count']}, "
          f"Neo4j {PERF['Neo4j']['count']})")
    if elapsed > 0:
        print(f"Throughput:        {total / elapsed:.2f} messages/sec")
    print("Avg write latency:")
    for name, db in PERF.items():
        avg = (db["total_ms"] / db["count"]) if db["count"] else 0.0
        print(f"   - {name:<8} {avg:6.2f} ms  ({db['count']} writes)")
    print(f"Errors:            {ERROR_COUNT}")
    print("=" * 60)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        for topic in (TOPIC_NETWORK, TOPIC_READINGS, TOPIC_TELEMETRY):
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")
        print()
    else:
        print(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    global ERROR_COUNT
    try:
        route_message(msg.topic, msg.payload)
    except Exception as error:
        ERROR_COUNT += 1
        print(f"Error processing message on '{msg.topic}': {error}")


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
        print_performance_summary()
        mysql_connection.close()
        mongo_client.close()
        neo4j_driver.close()
        client.disconnect()


if __name__ == "__main__":
    main()

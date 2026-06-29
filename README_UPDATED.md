# IoT-Based Environmental Monitoring System

This DBMS project implements an IoT-style environmental monitoring pipeline using MQTT, Python, MySQL, MongoDB, Neo4j, Docker, and Streamlit.

The system simulates environmental sensors that generate temperature, humidity, and air-quality data. The data is published through MQTT and processed by a Python subscriber. The subscriber stores different types of MQTT messages in different databases based on the MQTT topic.

---

## Main idea

The final project uses topic-based routing:

```text
environmental/readings   -> MySQL
environmental/telemetry  -> MongoDB
environmental/network    -> Neo4j
```

This means each database stores the type of data that fits its model:

- **MySQL** stores structured readings and alerts.
- **MongoDB** stores raw telemetry messages with flexible metadata.
- **Neo4j** stores the sensor/location network as a graph.

---

## Architecture

```text
Python Sensor Publisher
        |
        | publishes MQTT messages
        v
Mosquitto MQTT Broker
        |
        | forwards subscribed topics
        v
Python MQTT Subscriber
        |
        | topic-based routing
        |
        +--> environmental/readings  --> MySQL
        |
        +--> environmental/telemetry --> MongoDB
        |
        +--> environmental/network   --> Neo4j
        |
        v
Streamlit Dashboard
```

---

## MQTT topics

```text
environmental/network
```

Stores sensor topology in Neo4j:

```text
Sensor -> Room -> Floor -> Building
```

```text
environmental/readings
```

Stores structured sensor readings in MySQL:

```text
sensor_id, temperature, humidity, air_quality, reading_time, status
```

```text
environmental/telemetry
```

Stores raw telemetry in MongoDB:

```text
sensor_id, environmental values, device metadata, battery level, firmware version, optional signal strength, optional error code
```

---

## Project structure

```text
environmental_monitoring_mqtt/
├── config/
├── dashboard/
│   └── app.py
├── database/
│   ├── mysql_schema.sql
│   └── test_queries.sql
├── mosquitto/
│   └── config/
│       └── mosquitto.conf
├── publisher/
│   └── sensor_publisher.py
├── subscriber/
│   └── mqtt_subscriber.py
├── report/
├── screenshots/
├── docker-compose.yml
├── requirements.txt
├── requirements_dashboard.txt
├── README.md
├── README_dashboard.md
└── PRESENTATION_COMMANDS.md
```

---

## Start Docker services

```bash
docker compose up -d
```

Check containers:

```bash
docker compose ps -a
```

Expected containers:

```text
env_mqtt_broker
env_mysql_db
env_mongodb_db
env_neo4j_db
```

---

## Prepare Python environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements_dashboard.txt
copy .env.example .env
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Linux/macOS/WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements_dashboard.txt
cp .env.example .env
```

---

## Run subscriber

Open Terminal 1:

```bash
python subscriber/mqtt_subscriber.py
```

Expected output:

```text
Subscribed to topic: environmental/network
Subscribed to topic: environmental/readings
Subscribed to topic: environmental/telemetry
```

---

## Run publisher

Open Terminal 2:

```bash
python publisher/sensor_publisher.py
```

The publisher sends:

```text
topology      -> environmental/network    -> Neo4j
measurements  -> environmental/readings   -> MySQL
raw telemetry -> environmental/telemetry  -> MongoDB
```

---

## Run dashboard

Open Terminal 3:

```bash
streamlit run dashboard/app.py
```

Open:

```text
http://localhost:8501
```

---

## Database access

MySQL:

```bash
docker exec -it env_mysql_db mysql -u envuser -penvpass env_monitoring
```

MongoDB:

```bash
docker exec -it env_mongodb_db mongosh -u root -p rootpass --authenticationDatabase admin
```

Neo4j browser:

```text
http://localhost:7474
```

Neo4j login:

```text
username: neo4j
password: password123
```

---

## Useful MySQL queries

```sql
SELECT *
FROM readings
ORDER BY reading_id DESC
LIMIT 10;
```

```sql
SELECT sensor_id, COUNT(*) AS total_readings
FROM readings
GROUP BY sensor_id;
```

```sql
SELECT status, COUNT(*) AS total
FROM readings
GROUP BY status;
```

```sql
SELECT
    a.alert_id,
    a.reading_id,
    a.sensor_id,
    a.alert_type,
    t.default_message AS message,
    a.alert_time
FROM alerts a
JOIN alert_types t
    ON a.alert_type = t.alert_type
ORDER BY a.alert_id DESC
LIMIT 10;
```

---

## Useful MongoDB queries

```javascript
use env_monitoring
```

```javascript
db.sensor_messages.find().limit(5).pretty()
```

```javascript
db.sensor_messages.countDocuments()
```

```javascript
db.sensor_messages.find({"device.signal_strength_dbm": {$exists: true}}).pretty()
```

```javascript
db.sensor_messages.find({"device.error_code": {$exists: true}}).pretty()
```

---

## Useful Neo4j queries

```cypher
MATCH p=()-[]->()
RETURN p
LIMIT 25;
```

```cypher
MATCH p=(s:Sensor)-[:LOCATED_IN]->(r:Room)
RETURN p;
```

```cypher
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS count
ORDER BY count DESC;
```

```cypher
MATCH ()-[r]->()
RETURN type(r) AS relationship, count(*) AS count
ORDER BY count DESC;
```

```cypher
MATCH (s:Sensor)-[:LOCATED_IN]->(r:Room)-[:ON_FLOOR]->(f:Floor)-[:IN_BUILDING]->(b:Building)
RETURN
    s.sensor_id AS sensor_id,
    r.name AS room,
    f.number AS floor,
    b.name AS building
ORDER BY sensor_id;
```

---

## What this project demonstrates

This project demonstrates:

- MQTT-based communication between simulated IoT devices and a Python application
- real-time message reception using the Paho MQTT library
- topic-based routing of MQTT messages
- relational storage in MySQL
- document storage in MongoDB
- graph storage in Neo4j
- simple performance measurement using write latency and throughput
- dashboard visualization using Streamlit
- cross-database linking using `sensor_id`

---

## Short explanation

A Python publisher simulates environmental sensors and sends data to Mosquitto through MQTT. A Python subscriber receives messages from three topics and routes each message to the correct database. MySQL stores structured measurements and alerts. MongoDB stores raw telemetry with flexible metadata. Neo4j stores the sensor/location topology. The Streamlit dashboard reads from all three databases and presents the final monitoring result.

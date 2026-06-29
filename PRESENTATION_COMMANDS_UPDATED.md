# Environmental Monitoring Project — Presentation Commands

This file contains the commands needed to run and demonstrate the final environmental monitoring project.

The final version uses **topic-based routing**:

```text
environmental/network    -> Neo4j    -> sensor/location topology
environmental/readings   -> MySQL    -> structured readings and alerts
environmental/telemetry  -> MongoDB  -> raw telemetry with flexible device metadata
```

The project uses:

- Docker
- Eclipse Mosquitto MQTT broker
- MySQL
- MongoDB
- Neo4j
- Python publisher
- Python subscriber
- Streamlit dashboard

---

# 1. Go to the project folder

```powershell
cd C:\Users\adona.LAPTOP-FTQ3C4HH\Downloads\environmental_monitoring_mqtt_starter\environmental_monitoring_mqtt
```

Check files:

```powershell
dir
```

Expected important files and folders:

```text
docker-compose.yml
publisher
subscriber
dashboard
database
requirements.txt
requirements_dashboard.txt
README.md
README_dashboard.md
PRESENTATION_COMMANDS.md
report
screenshots
```

---

# 2. Start Docker containers

Start all services:

```powershell
docker compose up -d
```

Check container status:

```powershell
docker compose ps -a
```

Expected containers:

```text
env_mqtt_broker
env_mysql_db
env_mongodb_db
env_neo4j_db
```

All services should show `Up`.

---

# 3. Stop Docker containers

Stop containers but keep database data:

```powershell
docker compose down
```

Full reset including database volumes:

```powershell
docker compose down -v
```

Important: `docker compose down -v` deletes Docker volumes, so MySQL, MongoDB, and Neo4j stored data will be removed.

---

# 4. Create and activate Python virtual environment

Create the virtual environment:

```powershell
python -m venv .venv
```

Alternative:

```powershell
py -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Expected result:

```text
(.venv)
```

---

# 5. Install requirements

Install main project requirements:

```powershell
python -m pip install -r requirements.txt
```

Install dashboard requirements:

```powershell
python -m pip install -r requirements_dashboard.txt
```

Check installed packages:

```powershell
pip list
```

Main libraries used:

```text
paho-mqtt
mysql-connector-python
pymongo
neo4j
python-dotenv
streamlit
pandas
```

---

# 6. Run the MQTT subscriber

Open Terminal 1.

Go to the project folder:

```powershell
cd C:\Users\adona.LAPTOP-FTQ3C4HH\Downloads\environmental_monitoring_mqtt_starter\environmental_monitoring_mqtt
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the subscriber:

```powershell
python subscriber\mqtt_subscriber.py
```

Expected output:

```text
Subscriber is running. Press CTRL+C to stop.
Connected to MQTT broker at localhost:1883
Subscribed to topic: environmental/network
Subscribed to topic: environmental/readings
Subscribed to topic: environmental/telemetry
```

Explanation:

The subscriber listens to three MQTT topics. It routes each message to the correct database based on the topic:

```text
environmental/network    -> Neo4j
environmental/readings   -> MySQL
environmental/telemetry  -> MongoDB
```

Keep this terminal open.

---

# 7. Run the sensor publisher

Open Terminal 2.

Go to the project folder:

```powershell
cd C:\Users\adona.LAPTOP-FTQ3C4HH\Downloads\environmental_monitoring_mqtt_starter\environmental_monitoring_mqtt
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the publisher:

```powershell
python publisher\sensor_publisher.py
```

Expected output:

```text
Connected to MQTT broker at localhost:1883
Publishing to topics:
  - environmental/network   (topology      -> Neo4j)
  - environmental/readings  (measurements  -> MySQL)
  - environmental/telemetry (raw telemetry -> MongoDB)
```

Explanation:

The publisher simulates environmental sensors. It publishes:

- sensor topology to Neo4j through `environmental/network`
- structured measurements to MySQL through `environmental/readings`
- raw telemetry with flexible metadata to MongoDB through `environmental/telemetry`

---

# 8. Check MySQL

Open Terminal 3.

Enter the MySQL container:

```powershell
docker exec -it env_mysql_db mysql -u envuser -penvpass env_monitoring
```

Show tables:

```sql
SHOW TABLES;
```

Expected tables:

```text
alert_types
alerts
readings
```

Show latest readings:

```sql
SELECT *
FROM readings
ORDER BY reading_id DESC
LIMIT 10;
```

Count readings:

```sql
SELECT COUNT(*) AS total_readings
FROM readings;
```

Show readings grouped by sensor:

```sql
SELECT sensor_id, COUNT(*) AS total_readings
FROM readings
GROUP BY sensor_id;
```

Show status distribution:

```sql
SELECT status, COUNT(*) AS total
FROM readings
GROUP BY status;
```

Show average environmental values per sensor:

```sql
SELECT
    sensor_id,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(AVG(humidity), 2) AS avg_humidity,
    ROUND(AVG(air_quality), 2) AS avg_air_quality
FROM readings
GROUP BY sensor_id;
```

Show latest alerts with readable messages:

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

Exit MySQL:

```sql
exit;
```

---

# 9. Check MongoDB

Enter the MongoDB container:

```powershell
docker exec -it env_mongodb_db mongosh -u root -p rootpass --authenticationDatabase admin
```

Show databases:

```javascript
show dbs
```

Use the project database:

```javascript
use env_monitoring
```

Show collections:

```javascript
show collections
```

Expected collection:

```text
sensor_messages
```

Show raw telemetry documents:

```javascript
db.sensor_messages.find().pretty()
```

Show first 5 documents:

```javascript
db.sensor_messages.find().limit(5).pretty()
```

Count documents:

```javascript
db.sensor_messages.countDocuments()
```

Find telemetry for one sensor:

```javascript
db.sensor_messages.find({sensor_id: "S001"}).pretty()
```

Show latest telemetry documents:

```javascript
db.sensor_messages.find().sort({_id: -1}).limit(5).pretty()
```

Find telemetry messages that contain signal strength metadata:

```javascript
db.sensor_messages.find({"device.signal_strength_dbm": {$exists: true}}).pretty()
```

Find telemetry messages that contain error codes:

```javascript
db.sensor_messages.find({"device.error_code": {$exists: true}}).pretty()
```

Analyze firmware versions:

```javascript
db.sensor_messages.aggregate([
  {
    $group: {
      _id: "$device.firmware_version",
      total_messages: { $sum: 1 }
    }
  },
  { $sort: { total_messages: -1 } }
])
```

Exit MongoDB:

```javascript
exit
```

---

# 10. Check Neo4j

Open the Neo4j browser:

```text
http://localhost:7474
```

Login:

```text
Username: neo4j
Password: password123
```

Show the full sensor/location network:

```cypher
MATCH p=()-[]->()
RETURN p
LIMIT 25;
```

Show all sensors:

```cypher
MATCH (s:Sensor)
RETURN s;
```

Show all rooms:

```cypher
MATCH (r:Room)
RETURN r;
```

Show all floors:

```cypher
MATCH (f:Floor)
RETURN f;
```

Show all buildings:

```cypher
MATCH (b:Building)
RETURN b;
```

Show sensor-to-room relationships:

```cypher
MATCH p=(s:Sensor)-[:LOCATED_IN]->(r:Room)
RETURN p;
```

Show room-to-floor relationships:

```cypher
MATCH p=(r:Room)-[:ON_FLOOR]->(f:Floor)
RETURN p;
```

Show floor-to-building relationships:

```cypher
MATCH p=(f:Floor)-[:IN_BUILDING]->(b:Building)
RETURN p;
```

Count nodes by label:

```cypher
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS count
ORDER BY count DESC;
```

Count relationships by type:

```cypher
MATCH ()-[r]->()
RETURN type(r) AS relationship, count(*) AS count
ORDER BY count DESC;
```

Show complete sensor placement:

```cypher
MATCH (s:Sensor)-[:LOCATED_IN]->(r:Room)-[:ON_FLOOR]->(f:Floor)-[:IN_BUILDING]->(b:Building)
RETURN
    s.sensor_id AS sensor_id,
    s.sensor_type AS sensor_type,
    r.name AS room,
    f.number AS floor,
    b.name AS building
ORDER BY sensor_id;
```

---

# 11. Run the Streamlit dashboard

Open Terminal 4.

Go to the project folder:

```powershell
cd C:\Users\adona.LAPTOP-FTQ3C4HH\Downloads\environmental_monitoring_mqtt_starter\environmental_monitoring_mqtt
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the dashboard:

```powershell
streamlit run dashboard\app.py
```

Open the dashboard:

```text
http://localhost:8501
```

The dashboard shows:

- MySQL connection status and latest structured readings
- MongoDB connection status and raw telemetry documents
- Neo4j connection status and sensor/location network summary
- environmental values over time
- sensor locations joined from Neo4j using `sensor_id`

---

# 12. Useful Docker commands

Check running containers:

```powershell
docker ps
```

Check all containers:

```powershell
docker ps -a
```

Check Compose containers:

```powershell
docker compose ps -a
```

Restart containers:

```powershell
docker compose restart
```

Stop project containers:

```powershell
docker compose down
```

View Docker logs:

```powershell
docker compose logs
```

View logs for one service:

```powershell
docker compose logs mosquitto
docker compose logs mysql
docker compose logs mongodb
docker compose logs neo4j
```

---

# 13. Recommended screenshot list for the final report

```text
01_project_folder.png
02_docker_compose_up.png
03_docker_services_started.png
04_venv_and_requirements.png
05_subscriber_three_topics.png
06_publisher_three_topics.png
07_subscriber_routing_output.png
08_mysql_latest_readings.png
09_mysql_grouped_by_sensor.png
10_mysql_alerts_join_alert_types.png
11_mongodb_shell_connection.png
12_mongodb_collections.png
13_mongodb_raw_telemetry_documents.png
14_neo4j_full_network.png
15_neo4j_located_in_relationships.png
16_neo4j_labels_relationship_types.png
17_dashboard_connection_status.png
18_dashboard_system_overview.png
19_dashboard_mysql_readings.png
20_dashboard_environmental_chart.png
21_dashboard_mongodb_telemetry.png
22_dashboard_neo4j_summary.png
```

Save screenshots in:

```text
report/screenshots
```

---

# 14. Short project explanation for presentation

This project implements an IoT environmental monitoring pipeline using MQTT, Python, and three database platforms.

A Python publisher simulates environmental sensors and publishes different types of messages to three MQTT topics. The `environmental/readings` topic carries structured environmental measurements and is stored in MySQL. The `environmental/telemetry` topic carries raw telemetry with flexible device metadata and is stored in MongoDB. The `environmental/network` topic carries sensor placement information and is stored in Neo4j as a graph.

A Python subscriber receives the MQTT messages, processes them, classifies readings as NORMAL, WARNING, or DANGER, creates alerts when needed, and writes each message to the correct database based on its topic.

MySQL is used for structured readings and alerts. MongoDB is used for flexible raw telemetry. Neo4j is used for the sensor/location network. Docker Compose runs the MQTT broker and all databases, and a Streamlit dashboard visualizes the final result from all three platforms.

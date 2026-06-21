# Environmental Monitoring Project — Presentation Commands

This file contains all commands needed to run and demonstrate the environmental monitoring project.

The project uses:

- Docker
- Mosquitto MQTT broker
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

Expected important files/folders:

```text
docker-compose.yml
publisher
subscriber
dashboard
requirements.txt
requirements_dashboard.txt
README.md
PRESENTATION_COMMANDS.md
report
```

---

# 2. Start Docker containers

Start all containers:

```powershell
docker compose up -d
```

Check containers:

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

All should show:

```text
Up
```

---

# 3. Stop Docker containers

Stop containers but keep database data:

```powershell
docker compose down
```

Full reset including deleting database data:

```powershell
docker compose down -v
```

Warning:

```text
docker compose down -v
```

deletes Docker volumes, so old MySQL, MongoDB, and Neo4j data may disappear.

---

# 4. Create Python virtual environment

Create virtual environment using `python`:

```powershell
python -m venv .venv
```

Alternative using `py`:

```powershell
py -m venv .venv
```

Activate virtual environment:

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

Example:

```text
(.venv) PS C:\Users\adona...
```

---

# 5. Install requirements

Install main project requirements:

```powershell
pip install -r requirements.txt
```

Install dashboard requirements:

```powershell
pip install -r requirements_dashboard.txt
```

Check installed packages:

```powershell
pip list
```

---

# 6. Run the MQTT subscriber

Open Terminal 1.

Go to project folder:

```powershell
cd C:\Users\adona.LAPTOP-FTQ3C4HH\Downloads\environmental_monitoring_mqtt_starter\environmental_monitoring_mqtt
```

Activate virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run subscriber:

```powershell
python subscriber\mqtt_subscriber.py
```

Explanation:

The subscriber listens to MQTT messages and stores received sensor data in MySQL, MongoDB, and Neo4j.

Keep this terminal open.

---

# 7. Run the sensor publisher

Open Terminal 2.

Go to project folder:

```powershell
cd C:\Users\adona.LAPTOP-FTQ3C4HH\Downloads\environmental_monitoring_mqtt_starter\environmental_monitoring_mqtt
```

Activate virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run publisher:

```powershell
python publisher\sensor_publisher.py
```

Explanation:

The publisher simulates environmental sensors and sends readings to the Mosquitto MQTT broker.

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

Show sensors:

```sql
SELECT * FROM sensors;
```

Show readings:

```sql
SELECT * FROM readings LIMIT 10;
```

Count readings:

```sql
SELECT COUNT(*) FROM readings;
```

Show latest readings:

```sql
SELECT * FROM readings ORDER BY reading_id DESC LIMIT 5;
```

Show average sensor values:

```sql
SELECT 
    AVG(temperature) AS avg_temperature,
    AVG(humidity) AS avg_humidity,
    AVG(air_quality) AS avg_air_quality
FROM readings;
```

Show readings grouped by sensor:

```sql
SELECT sensor_id, COUNT(*) AS total_readings
FROM readings
GROUP BY sensor_id;
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

Show all sensor documents:

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

Find documents for one sensor:

```javascript
db.sensor_messages.find({sensor_id: "S001"}).pretty()
```

Show latest documents:

```javascript
db.sensor_messages.find().sort({_id: -1}).limit(5).pretty()
```

Exit MongoDB:

```javascript
exit
```

---

# 10. Check Neo4j

Open browser:

```text
http://localhost:7474
```

Login:

```text
Username: neo4j
Password: password
```

Show all graph data:

```cypher
MATCH (n) RETURN n;
```

Show all sensors:

```cypher
MATCH (s:Sensor) RETURN s;
```

Show all locations:

```cypher
MATCH (l:Location) RETURN l;
```

Show readings:

```cypher
MATCH (r:Reading) RETURN r LIMIT 25;
```

Show sensor-location relationships:

```cypher
MATCH (s:Sensor)-[r:LOCATED_IN]->(l:Location)
RETURN s, r, l;
```

Show sensor-reading relationships:

```cypher
MATCH (s:Sensor)-[r:GENERATED]->(reading:Reading)
RETURN s, r, reading
LIMIT 25;
```

Count all nodes:

```cypher
MATCH (n)
RETURN count(n) AS total_nodes;
```

Count all relationships:

```cypher
MATCH ()-[r]->()
RETURN count(r) AS total_relationships;
```

Count readings per sensor:

```cypher
MATCH (s:Sensor)-[:GENERATED]->(r:Reading)
RETURN s.sensor_id AS sensor, count(r) AS total_readings;
```

---

# 11. Run Streamlit dashboard

Open Terminal 4.

Go to project folder:

```powershell
cd C:\Users\adona.LAPTOP-FTQ3C4HH\Downloads\environmental_monitoring_mqtt_starter\environmental_monitoring_mqtt
```

Activate virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run dashboard:

```powershell
streamlit run dashboard\app.py
```

Open browser:

```text
http://localhost:8501
```

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

---

# 13. Screenshot list for report

Recommended screenshots:

```text
01_project_folder.png
02_docker_compose_up.png
03_docker_ps.png
04_venv_active.png
05_subscriber_running.png
06_publisher_running.png
07_mysql_tables.png
08_mysql_readings.png
09_mongodb_collections.png
10_mongodb_documents.png
11_neo4j_graph.png
12_dashboard.png
```

Save screenshots in:

```text
report/screenshots
```

---

# 14. Short project explanation

This project simulates an IoT environmental monitoring system.

A Python publisher generates environmental sensor readings such as temperature, humidity, and air quality. These readings are sent as JSON messages to a Mosquitto MQTT broker.

A Python subscriber listens to the MQTT topic, receives the messages, parses the JSON data, and stores the information in three different database systems.

MySQL is used for structured relational storage.

MongoDB is used for raw JSON-like sensor documents.

Neo4j is used to represent sensors, locations, and readings as graph nodes and relationships.

Docker Compose is used to run Mosquitto, MySQL, MongoDB, and Neo4j as containers.

Finally, a Streamlit dashboard visualizes the collected environmental data.
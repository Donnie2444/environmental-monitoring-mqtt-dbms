# Environmental Monitoring Dashboard

This dashboard belongs to the final Environmental Monitoring MQTT project.

It reads from three different database platforms:

- **MySQL** for structured readings and alerts
- **MongoDB** for raw telemetry with flexible device metadata
- **Neo4j** for the sensor/location network

The dashboard does not store data by itself. It displays the data that was already produced by the MQTT publisher, routed by the MQTT subscriber, and saved in the correct database.

---

## Project flow

```text
Python Publisher
    -> environmental/readings
        -> Python Subscriber
            -> MySQL readings + alerts

Python Publisher
    -> environmental/telemetry
        -> Python Subscriber
            -> MongoDB raw telemetry

Python Publisher
    -> environmental/network
        -> Python Subscriber
            -> Neo4j sensor/location graph
```

The dashboard combines these results in one interface. It also links MySQL readings to Neo4j locations using `sensor_id`.

---

## Folder placement

The dashboard folder should be inside the main project folder:

```text
environmental_monitoring_mqtt/
├── docker-compose.yml
├── database/
├── publisher/
│   └── sensor_publisher.py
├── subscriber/
│   └── mqtt_subscriber.py
├── dashboard/
│   └── app.py
├── requirements.txt
├── requirements_dashboard.txt
├── .env.example
└── README_dashboard.md
```

---

## Install dashboard requirements

Activate the Python virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dashboard dependencies:

```powershell
python -m pip install -r requirements_dashboard.txt
```

---

## Start Docker containers

The dashboard needs the database containers to be running:

```powershell
docker compose up -d
docker compose ps -a
```

Required containers:

```text
env_mqtt_broker
env_mysql_db
env_mongodb_db
env_neo4j_db
```

---

## Run the MQTT subscriber

Open a terminal and run:

```powershell
python subscriber\mqtt_subscriber.py
```

The subscriber should connect to Mosquitto and subscribe to:

```text
environmental/network
environmental/readings
environmental/telemetry
```

---

## Run the MQTT publisher

Open another terminal and run:

```powershell
python publisher\sensor_publisher.py
```

The publisher sends:

```text
environmental/network    -> topology      -> Neo4j
environmental/readings   -> measurements  -> MySQL
environmental/telemetry  -> raw telemetry -> MongoDB
```

---

## Run the dashboard

Open another terminal and run:

```powershell
streamlit run dashboard\app.py
```

The dashboard opens at:

```text
http://localhost:8501
```

---

## Default dashboard connections

MySQL:

```text
host: 127.0.0.1
port: 3308
user: envuser
password: envpass
database: env_monitoring
```

MongoDB:

```text
mongodb://root:rootpass@localhost:27018/
database: env_monitoring
collection: sensor_messages
```

Neo4j:

```text
bolt://localhost:7687
user: neo4j
password: password123
```

---

## What the dashboard shows

The dashboard includes:

- database connection status for MySQL, MongoDB, and Neo4j
- total number of MySQL readings
- total number of MongoDB telemetry documents
- number of Neo4j nodes and relationships
- latest MySQL readings
- environmental values over time
- status distribution of NORMAL, WARNING, and DANGER readings
- raw telemetry documents from MongoDB
- device metadata such as firmware version, signal strength, and error codes
- Neo4j node labels and relationship types
- sensor placement table from Neo4j

---

## Cross-database link

The dashboard links data across databases using `sensor_id`.

MySQL stores the readings:

```text
S001, temperature, humidity, air_quality, status
```

Neo4j stores the location:

```text
S001 -> Room A -> Floor 1 -> Computer Science Building
```

The dashboard uses this shared `sensor_id` to display readings together with their physical locations.

---

## Troubleshooting

If MySQL does not connect, check that the MySQL container is running and that port `3308` is not blocked.

If MongoDB does not connect, check that the MongoDB container is running and that the URI uses port `27018`.

If Neo4j does not connect, check that Neo4j is running on Bolt port `7687` and that the password is `password123`.

If the dashboard opens but shows no data, run the subscriber first and then run the publisher for at least a few seconds.

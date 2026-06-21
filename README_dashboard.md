# Environmental Monitoring Dashboard

This dashboard is for the Environmental Monitoring MQTT project.

It connects to:

- MySQL for structured sensor readings
- MongoDB for raw MQTT messages
- Neo4j for graph nodes and relationships

## Folder placement

Put the dashboard folder inside your main project folder:

```text
environmental_monitoring_mqtt/
├── docker-compose.yml
├── publisher/
├── subscriber/
├── dashboard/
│   └── app.py
└── requirements_dashboard.txt
```

## Install dashboard requirements

Activate your virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then install:

```powershell
pip install -r requirements_dashboard.txt
```

## Start containers

```powershell
docker compose up -d
docker compose ps -a
```

Make sure these are running:

```text
env_mqtt_broker
env_mysql_db
env_mongodb_db
env_neo4j_db
```

## Run subscriber

```powershell
python subscriber\mqtt_subscriber.py
```

## Run publisher

Open another terminal:

```powershell
python publisher\sensor_publisher.py
```

## Run dashboard

Open another terminal:

```powershell
streamlit run dashboard\app.py
```

The dashboard opens at:

```text
http://localhost:8501
```

## Default connections used by the dashboard

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
```

Neo4j:

```text
bolt://localhost:7687
user: neo4j
password: password
```

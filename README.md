# IoT-Based Environmental Monitoring System

This DBMS project simulates IoT environmental sensors that measure temperature, humidity, and air quality.
The readings are sent through MQTT, processed using Python, and stored in MySQL, MongoDB, and Neo4j.

## Architecture

Python Publisher -> Mosquitto MQTT Broker -> Python Subscriber -> MySQL + MongoDB + Neo4j

## Start Docker services

```bash
docker compose up -d
```

## Check containers

```bash
docker ps
```

## Prepare Python environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On Linux/macOS/WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run subscriber

Open Terminal 1:

```bash
python subscriber/mqtt_subscriber.py
```

## Run publisher

Open Terminal 2:

```bash
python publisher/sensor_publisher.py
```

## Useful access links

- Neo4j browser: http://localhost:7474
- Neo4j username: neo4j
- Neo4j password: password123
- MySQL host: 127.0.0.1
- MySQL port: 3308
- MySQL user: envuser
- MySQL password: envpass
- MongoDB host port: 27018

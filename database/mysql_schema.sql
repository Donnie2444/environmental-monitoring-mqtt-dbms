CREATE DATABASE IF NOT EXISTS env_monitoring;
USE env_monitoring;

-- MySQL owns the structured measurements and their alerts.
-- Sensor/location topology lives in Neo4j; raw telemetry lives in MongoDB.

CREATE TABLE IF NOT EXISTS readings (
    reading_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(20) NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity DECIMAL(5,2) NOT NULL,
    air_quality INT NOT NULL,
    reading_time DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lookup table (3NF): each alert_type maps to exactly one message.
-- Storing the message here once removes the transitive dependency that would
-- otherwise repeat the same text in every alert row.
CREATE TABLE IF NOT EXISTS alert_types (
    alert_type VARCHAR(50) PRIMARY KEY,
    default_message VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    reading_id BIGINT NOT NULL,
    sensor_id VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    alert_time DATETIME NOT NULL,
    FOREIGN KEY (reading_id) REFERENCES readings(reading_id),
    FOREIGN KEY (alert_type) REFERENCES alert_types(alert_type)
);

-- The message lives ONCE, here.
INSERT IGNORE INTO alert_types (alert_type, default_message) VALUES
('HIGH_TEMPERATURE',    'Temperature is above the dangerous threshold.'),
('HIGH_HUMIDITY',       'Humidity is above the dangerous threshold.'),
('POOR_AIR_QUALITY',    'Air quality is poor and above the dangerous threshold.'),
('ENVIRONMENT_WARNING', 'One or more environmental values are above the normal range.');

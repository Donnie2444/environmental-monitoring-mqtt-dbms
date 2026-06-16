CREATE DATABASE IF NOT EXISTS env_monitoring;
USE env_monitoring;

CREATE TABLE IF NOT EXISTS locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    room_name VARCHAR(100) NOT NULL UNIQUE,
    floor_number INT,
    building_name VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS sensors (
    sensor_id VARCHAR(20) PRIMARY KEY,
    sensor_type VARCHAR(50) NOT NULL,
    location_id INT NOT NULL,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE TABLE IF NOT EXISTS readings (
    reading_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(20) NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity DECIMAL(5,2) NOT NULL,
    air_quality INT NOT NULL,
    reading_time DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    reading_id BIGINT NOT NULL,
    sensor_id VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    message VARCHAR(255) NOT NULL,
    alert_time DATETIME NOT NULL,
    FOREIGN KEY (reading_id) REFERENCES readings(reading_id),
    FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id)
);

INSERT IGNORE INTO locations (room_name, floor_number, building_name) VALUES
('Room A', 1, 'Computer Science Building'),
('Room B', 1, 'Computer Science Building'),
('Laboratory', 2, 'Computer Science Building');

INSERT IGNORE INTO sensors (sensor_id, sensor_type, location_id) VALUES
('S001', 'Environmental Sensor', (SELECT location_id FROM locations WHERE room_name = 'Room A')),
('S002', 'Environmental Sensor', (SELECT location_id FROM locations WHERE room_name = 'Room B')),
('S003', 'Environmental Sensor', (SELECT location_id FROM locations WHERE room_name = 'Laboratory'));

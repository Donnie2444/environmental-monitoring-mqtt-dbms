USE env_monitoring;

SELECT * FROM locations;
SELECT * FROM sensors;
SELECT * FROM readings ORDER BY reading_id DESC LIMIT 10;
SELECT * FROM alerts ORDER BY alert_id DESC LIMIT 10;

SELECT sensor_id, COUNT(*) AS total_readings
FROM readings
GROUP BY sensor_id;

SELECT status, COUNT(*) AS total
FROM readings
GROUP BY status;

USE env_monitoring;

-- Most recent readings (reading_id is auto-increment, so DESC = newest first)
SELECT * FROM readings ORDER BY reading_id DESC LIMIT 10;

-- The alert_type lookup table (message stored once per type)
SELECT * FROM alert_types;

-- Most recent alerts WITH their message, recovered by joining alert_types (3NF)
SELECT a.alert_id, a.reading_id, a.sensor_id, a.alert_type,
       t.default_message AS message, a.alert_time
FROM alerts a
JOIN alert_types t ON a.alert_type = t.alert_type
ORDER BY a.alert_id DESC
LIMIT 10;

-- Totals and breakdowns
SELECT COUNT(*) AS total_readings FROM readings;

SELECT sensor_id, COUNT(*) AS total_readings
FROM readings
GROUP BY sensor_id;

SELECT status, COUNT(*) AS total
FROM readings
GROUP BY status;

SELECT alert_type, COUNT(*) AS total
FROM alerts
GROUP BY alert_type;

SELECT
    sensor_id,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(AVG(humidity), 2)    AS avg_humidity,
    ROUND(AVG(air_quality), 2) AS avg_air_quality
FROM readings
GROUP BY sensor_id;

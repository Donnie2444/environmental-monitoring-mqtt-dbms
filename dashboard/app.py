import os
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import mysql.connector
except Exception:
    mysql = None

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None


# ============================================================
# Environmental Monitoring Dashboard
# Each database stores a DIFFERENT kind of data:
#   1. MySQL   -> structured readings + alerts (measurements)
#   2. MongoDB -> raw telemetry with flexible device metadata
#   3. Neo4j   -> the sensor/location network (topology)
# The dashboard links MySQL readings to Neo4j locations by sensor_id.
# ============================================================


st.set_page_config(
    page_title="Environmental Monitoring Dashboard",
    page_icon="🌿",
    layout="wide"
)


# ---------- Small CSS for a cleaner dashboard ----------
st.markdown(
    """
    <style>
    .main { background-color: #f7f9fb; }
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3 { color: #1f2937; }
    </style>
    """,
    unsafe_allow_html=True
)


# ---------- Sidebar settings ----------
st.sidebar.title("⚙️ Connection Settings")

MYSQL_HOST = st.sidebar.text_input("MySQL host", os.getenv("MYSQL_HOST", "127.0.0.1"))
MYSQL_PORT = st.sidebar.number_input("MySQL port", value=int(os.getenv("MYSQL_PORT", "3308")))
MYSQL_USER = st.sidebar.text_input("MySQL user", os.getenv("MYSQL_USER", "envuser"))
MYSQL_PASSWORD = st.sidebar.text_input("MySQL password", os.getenv("MYSQL_PASSWORD", "envpass"), type="password")
MYSQL_DATABASE = st.sidebar.text_input("MySQL database", os.getenv("MYSQL_DATABASE", "env_monitoring"))

MONGO_URI = st.sidebar.text_input("MongoDB URI", os.getenv("MONGODB_URI", "mongodb://root:rootpass@localhost:27018/"))
MONGO_DATABASE = st.sidebar.text_input("MongoDB database", os.getenv("MONGODB_DB", "env_monitoring"))

NEO4J_URI = st.sidebar.text_input("Neo4j URI", os.getenv("NEO4J_URI", "bolt://localhost:7687"))
NEO4J_USER = st.sidebar.text_input("Neo4j user", os.getenv("NEO4J_USER", "neo4j"))
NEO4J_PASSWORD = st.sidebar.text_input("Neo4j password", os.getenv("NEO4J_PASSWORD", "password123"), type="password")

st.sidebar.info("Keep Docker containers running before opening the dashboard.")


# ---------- Helper functions ----------
def find_column(df, possible_names):
    """Find a column even if the exact name is slightly different."""
    lower_map = {col.lower(): col for col in df.columns}
    for name in possible_names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None


def clean_readings_dataframe(df):
    """Make the readings table easier to display and chart."""
    if df.empty:
        return df

    df = df.copy()

    timestamp_col = find_column(df, ["timestamp", "created_at", "reading_time", "time", "date_time"])
    if timestamp_col:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
        df = df.sort_values(timestamp_col)

    temp_col = find_column(df, ["temperature", "temp"])
    hum_col = find_column(df, ["humidity", "hum"])
    aq_col = find_column(df, ["air_quality", "airquality", "aq", "air_quality_index"])

    for col in [temp_col, hum_col, aq_col]:
        if col:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


@st.cache_data(ttl=5)
def load_mysql_data():
    """Connect to MySQL and load the structured readings."""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST, port=int(MYSQL_PORT), user=MYSQL_USER,
            password=MYSQL_PASSWORD, database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        if "readings" not in tables:
            return pd.DataFrame(), tables, "No 'readings' table found in MySQL."

        df = pd.read_sql("SELECT * FROM `readings` LIMIT 1000", conn)
        df = clean_readings_dataframe(df)

        cursor.close()
        conn.close()
        return df, tables, None
    except Exception as e:
        return pd.DataFrame(), [], str(e)


@st.cache_data(ttl=5)
def load_mongo_data():
    """Connect to MongoDB and load the raw telemetry messages."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")

        db = client[MONGO_DATABASE]
        collections = db.list_collection_names()

        selected = "sensor_messages" if "sensor_messages" in collections else (collections[0] if collections else None)
        if selected is None:
            return pd.DataFrame(), collections, 0, "No collections found in MongoDB."

        collection = db[selected]
        total_docs = collection.count_documents({})
        docs = list(collection.find().sort("_id", -1).limit(1000))
        for doc in docs:
            doc["_id"] = str(doc["_id"])

        df = pd.json_normalize(docs)  # flatten nested device metadata into columns
        client.close()
        return df, collections, total_docs, None
    except Exception as e:
        return pd.DataFrame(), [], 0, str(e)


@st.cache_data(ttl=5)
def load_neo4j_data():
    """Connect to Neo4j and read the sensor/location network."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]

            label_rows = session.run("""
                MATCH (n) UNWIND labels(n) AS label
                RETURN label, count(*) AS count ORDER BY count DESC
            """).data()

            relationship_rows = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS relationship, count(*) AS count ORDER BY count DESC
            """).data()

            # The sensor -> room mapping. This is the link used to join MySQL by sensor_id.
            location_rows = session.run("""
                MATCH (s:Sensor)-[:LOCATED_IN]->(r:Room)
                RETURN s.sensor_id AS sensor_id, r.name AS room
            """).data()

        driver.close()
        labels_df = pd.DataFrame(label_rows)
        rels_df = pd.DataFrame(relationship_rows)
        sensor_location = {row["sensor_id"]: row["room"] for row in location_rows}
        return node_count, rel_count, labels_df, rels_df, sensor_location, None
    except Exception as e:
        return 0, 0, pd.DataFrame(), pd.DataFrame(), {}, str(e)


# ---------- Page title ----------
st.title("🌿 Environmental Monitoring Dashboard")
st.write(
    "Each database stores a different kind of data: "
    "**MySQL** holds the structured readings and alerts, "
    "**MongoDB** holds the raw telemetry with flexible device metadata, and "
    "**Neo4j** holds the sensor/location network. "
    "The dashboard links MySQL readings to their location through Neo4j using `sensor_id`."
)


# ---------- Load data ----------
mysql_df, mysql_tables, mysql_error = load_mysql_data()
mongo_df, mongo_collections, mongo_total, mongo_error = load_mongo_data()
neo4j_nodes, neo4j_relationships, neo4j_labels_df, neo4j_rels_df, sensor_location, neo4j_error = load_neo4j_data()


# ---------- Connection status ----------
st.subheader("Database Connection Status")
c1, c2, c3 = st.columns(3)
with c1:
    if mysql_error:
        st.error("MySQL not connected"); st.caption(mysql_error)
    else:
        st.success("MySQL connected"); st.caption(f"Tables: {', '.join(mysql_tables) if mysql_tables else 'None'}")
with c2:
    if mongo_error:
        st.error("MongoDB not connected"); st.caption(mongo_error)
    else:
        st.success("MongoDB connected"); st.caption(f"Collections: {', '.join(mongo_collections) if mongo_collections else 'None'}")
with c3:
    if neo4j_error:
        st.error("Neo4j not connected"); st.caption(neo4j_error)
    else:
        st.success("Neo4j connected"); st.caption("Sensor/location network is reachable")

st.divider()


# ---------- Metrics ----------
st.subheader("System Overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric("MySQL readings", len(mysql_df))
m2.metric("MongoDB documents", mongo_total)
m3.metric("Neo4j nodes (network)", neo4j_nodes)
m4.metric("Neo4j relationships", neo4j_relationships)

st.divider()


# ---------- Main charts from MySQL (with location joined from Neo4j) ----------
st.subheader("Sensor Readings from MySQL")

if mysql_df.empty:
    st.warning("No MySQL readings found yet. Run the subscriber and publisher first.")
else:
    timestamp_col = find_column(mysql_df, ["created_at", "reading_time", "timestamp", "time"])
    sensor_col = find_column(mysql_df, ["sensor_id", "sensor", "device_id"])
    temp_col = find_column(mysql_df, ["temperature", "temp"])
    hum_col = find_column(mysql_df, ["humidity", "hum"])
    aq_col = find_column(mysql_df, ["air_quality", "airquality", "aq"])
    status_col = find_column(mysql_df, ["status", "condition", "level"])

    # CROSS-DATABASE JOIN: MySQL has sensor_id, Neo4j knows where that sensor is.
    if sensor_col and sensor_location:
        mysql_df["location"] = mysql_df[sensor_col].map(sensor_location)

    latest_df = mysql_df.tail(10).sort_index(ascending=False)
    st.write("Latest readings:")
    st.dataframe(latest_df, use_container_width=True)

    chart_cols = [c for c in [temp_col, hum_col, aq_col] if c]
    if timestamp_col and chart_cols:
        chart_df = mysql_df[[timestamp_col] + chart_cols].dropna()
        if not chart_df.empty:
            st.write("Environmental values over time:")
            st.line_chart(chart_df.set_index(timestamp_col))

    col_a, col_b = st.columns(2)
    with col_a:
        if status_col:
            st.write("Status distribution:")
            st.bar_chart(mysql_df[status_col].value_counts())
    with col_b:
        if "location" in mysql_df and mysql_df["location"].notna().any():
            st.write("Readings by location (joined from Neo4j):")
            st.bar_chart(mysql_df["location"].value_counts())

st.divider()


# ---------- MongoDB raw telemetry ----------
st.subheader("Raw Telemetry from MongoDB")
if mongo_df.empty:
    st.warning("No MongoDB documents found yet.")
else:
    st.write("MongoDB stores the raw device messages, including flexible metadata that varies per message.")
    st.dataframe(mongo_df.head(20), use_container_width=True)

    # Highlight the flexible device metadata that only MongoDB holds.
    meta_cols = [c for c in mongo_df.columns if c.startswith("device.")]
    if "device.firmware_version" in mongo_df:
        st.write("Firmware versions reported (device metadata):")
        st.bar_chart(mongo_df["device.firmware_version"].value_counts())
    if "device.error_code" in mongo_df and mongo_df["device.error_code"].notna().any():
        st.write("Error codes reported (only present on some messages):")
        st.bar_chart(mongo_df["device.error_code"].value_counts())

st.divider()


# ---------- Neo4j network summary ----------
st.subheader("Neo4j Sensor / Location Network")
if neo4j_error:
    st.warning("Neo4j data cannot be shown because the connection failed.")
else:
    col1, col2 = st.columns(2)
    with col1:
        st.write("Node labels:")
        if neo4j_labels_df.empty:
            st.info("No Neo4j nodes found.")
        else:
            st.dataframe(neo4j_labels_df, use_container_width=True)
            if "label" in neo4j_labels_df and "count" in neo4j_labels_df:
                st.bar_chart(neo4j_labels_df.set_index("label")["count"])
    with col2:
        st.write("Relationship types:")
        if neo4j_rels_df.empty:
            st.info("No Neo4j relationships found.")
        else:
            st.dataframe(neo4j_rels_df, use_container_width=True)
            if "relationship" in neo4j_rels_df and "count" in neo4j_rels_df:
                st.bar_chart(neo4j_rels_df.set_index("relationship")["count"])

    if sensor_location:
        st.write("Sensor placements (from the graph):")
        st.dataframe(
            pd.DataFrame(list(sensor_location.items()), columns=["sensor_id", "room"]),
            use_container_width=True
        )

st.divider()


# ---------- Explanation section ----------
st.subheader("How this dashboard fits the project")
st.markdown(
    """
    **Project flow:**

    1. The Python publisher simulates environmental sensors.
    2. It publishes to three MQTT topics, one per database.
    3. The subscriber routes each message **based on its topic**:
       - `environmental/readings`  → **MySQL** (structured readings + alerts)
       - `environmental/telemetry` → **MongoDB** (raw message + flexible device metadata)
       - `environmental/network`   → **Neo4j** (sensor → room → floor → building)
    4. This dashboard reads all three and links them by `sensor_id` and `reading_id`.

    **Why three databases — each stores something the others cannot:**

    - **MySQL** — fixed columns, foreign keys, SQL aggregation → the measurements.
    - **MongoDB** — schema-free documents whose fields change per message → raw telemetry.
    - **Neo4j** — relationships between sensors, rooms, floors, and the building → the network.
    """
)


# ---------- Refresh button ----------
if st.button("Refresh dashboard"):
    st.cache_data.clear()
    st.rerun()

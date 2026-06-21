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
# Reads data from:
#   1. MySQL   -> structured sensor readings
#   2. MongoDB -> raw MQTT JSON messages
#   3. Neo4j   -> graph nodes and relationships
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
    .main {
        background-color: #f7f9fb;
    }
    .block-container {
        padding-top: 1.5rem;
    }
    .metric-card {
        background: white;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #e6e8eb;
        box-shadow: 0px 2px 10px rgba(0,0,0,0.04);
    }
    h1, h2, h3 {
        color: #1f2937;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ---------- Sidebar settings ----------
st.sidebar.title("⚙️ Connection Settings")

MYSQL_HOST = st.sidebar.text_input("MySQL host", os.getenv("MYSQL_HOST", "127.0.0.1"))
MYSQL_PORT = st.sidebar.number_input("MySQL port", value=int(os.getenv("MYSQL_PORT", "3308")))
MYSQL_USER = st.sidebar.text_input("MySQL user", os.getenv("MYSQL_USER", "envuser"))
MYSQL_PASSWORD = st.sidebar.text_input(
    "MySQL password",
    os.getenv("MYSQL_PASSWORD", "envpass"),
    type="password"
)
MYSQL_DATABASE = st.sidebar.text_input("MySQL database", os.getenv("MYSQL_DATABASE", "env_monitoring"))

MONGO_URI = st.sidebar.text_input(
    "MongoDB URI",
    os.getenv("MONGO_URI", "mongodb://root:rootpass@localhost:27018/")
)
MONGO_DATABASE = st.sidebar.text_input("MongoDB database", os.getenv("MONGO_DATABASE", "env_monitoring"))

NEO4J_URI = st.sidebar.text_input("Neo4j URI", os.getenv("NEO4J_URI", "bolt://localhost:7687"))
NEO4J_USER = st.sidebar.text_input("Neo4j user", os.getenv("NEO4J_USER", "neo4j"))
NEO4J_PASSWORD = st.sidebar.text_input(
    "Neo4j password",
    os.getenv("NEO4J_PASSWORD", "password"),
    type="password"
)

st.sidebar.info("Keep Docker containers running before opening the dashboard.")


# ---------- Helper functions ----------
def find_column(df, possible_names):
    """
    Finds a column even if the exact name is slightly different.
    Example: temperature, temp, Temperature.
    """
    lower_map = {col.lower(): col for col in df.columns}
    for name in possible_names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None


def clean_readings_dataframe(df):
    """
    Makes the readings table easier to display and chart.
    It tries to recognize common column names.
    """
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

    status_col = find_column(df, ["status", "condition", "level"])
    if not status_col and (temp_col or aq_col):
        def calculate_status(row):
            temp = row[temp_col] if temp_col else None
            aq = row[aq_col] if aq_col else None

            if pd.notna(temp) and temp >= 35:
                return "DANGER"
            if pd.notna(aq) and aq <= 40:
                return "DANGER"
            if pd.notna(temp) and temp >= 30:
                return "WARNING"
            if pd.notna(aq) and aq <= 60:
                return "WARNING"
            return "NORMAL"

        df["status"] = df.apply(calculate_status, axis=1)

    return df


@st.cache_data(ttl=5)
def load_mysql_data():
    """
    Connects to MySQL and loads sensor readings.
    The code checks common table names so it works even if your table name is
    readings or sensor_readings.
    """
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=int(MYSQL_PORT),
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )

        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        table_candidates = ["readings", "sensor_readings", "environment_readings", "mqtt_readings"]
        readings_table = None

        for table in table_candidates:
            if table in tables:
                readings_table = table
                break

        if readings_table is None and tables:
            readings_table = tables[0]

        if readings_table is None:
            return pd.DataFrame(), [], "No tables found in MySQL."

        query = f"SELECT * FROM `{readings_table}` LIMIT 1000"
        df = pd.read_sql(query, conn)
        df = clean_readings_dataframe(df)

        cursor.close()
        conn.close()

        return df, tables, None

    except Exception as e:
        return pd.DataFrame(), [], str(e)


@st.cache_data(ttl=5)
def load_mongo_data():
    """
    Connects to MongoDB and loads raw sensor messages.
    """
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")

        db = client[MONGO_DATABASE]
        collections = db.list_collection_names()

        collection_candidates = ["sensor_messages", "readings", "sensor_readings", "mqtt_messages"]
        selected_collection = None

        for collection in collection_candidates:
            if collection in collections:
                selected_collection = collection
                break

        if selected_collection is None and collections:
            selected_collection = collections[0]

        if selected_collection is None:
            return pd.DataFrame(), collections, 0, "No collections found in MongoDB."

        collection = db[selected_collection]
        total_docs = collection.count_documents({})
        docs = list(collection.find().sort("_id", -1).limit(1000))

        for doc in docs:
            doc["_id"] = str(doc["_id"])

        df = pd.DataFrame(docs)
        df = clean_readings_dataframe(df)

        client.close()

        return df, collections, total_docs, None

    except Exception as e:
        return pd.DataFrame(), [], 0, str(e)


@st.cache_data(ttl=5)
def load_neo4j_data():
    """
    Connects to Neo4j and counts graph nodes and relationships.
    """
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]

            label_rows = session.run("""
                MATCH (n)
                UNWIND labels(n) AS label
                RETURN label, count(*) AS count
                ORDER BY count DESC
            """).data()

            relationship_rows = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS relationship, count(*) AS count
                ORDER BY count DESC
            """).data()

        driver.close()

        labels_df = pd.DataFrame(label_rows)
        rels_df = pd.DataFrame(relationship_rows)

        return node_count, rel_count, labels_df, rels_df, None

    except Exception as e:
        return 0, 0, pd.DataFrame(), pd.DataFrame(), str(e)


# ---------- Page title ----------
st.title("🌿 Environmental Monitoring Dashboard")
st.write(
    "This dashboard shows data from the environmental MQTT project: "
    "**MySQL for structured readings**, **MongoDB for raw sensor messages**, "
    "and **Neo4j for graph relationships**."
)


# ---------- Load data ----------
mysql_df, mysql_tables, mysql_error = load_mysql_data()
mongo_df, mongo_collections, mongo_total, mongo_error = load_mongo_data()
neo4j_nodes, neo4j_relationships, neo4j_labels_df, neo4j_rels_df, neo4j_error = load_neo4j_data()


# ---------- Connection status ----------
st.subheader("Database Connection Status")

c1, c2, c3 = st.columns(3)

with c1:
    if mysql_error:
        st.error("MySQL not connected")
        st.caption(mysql_error)
    else:
        st.success("MySQL connected")
        st.caption(f"Tables: {', '.join(mysql_tables) if mysql_tables else 'No tables'}")

with c2:
    if mongo_error:
        st.error("MongoDB not connected")
        st.caption(mongo_error)
    else:
        st.success("MongoDB connected")
        st.caption(f"Collections: {', '.join(mongo_collections) if mongo_collections else 'No collections'}")

with c3:
    if neo4j_error:
        st.error("Neo4j not connected")
        st.caption(neo4j_error)
    else:
        st.success("Neo4j connected")
        st.caption("Graph database is reachable")


st.divider()


# ---------- Metrics ----------
st.subheader("System Overview")

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("MySQL rows", len(mysql_df))

with m2:
    st.metric("MongoDB documents", mongo_total)

with m3:
    st.metric("Neo4j nodes", neo4j_nodes)

with m4:
    st.metric("Neo4j relationships", neo4j_relationships)


st.divider()


# ---------- Main charts from MySQL ----------
st.subheader("Sensor Readings from MySQL")

if mysql_df.empty:
    st.warning("No MySQL readings found yet. Run the subscriber and publisher first.")
else:
    timestamp_col = find_column(mysql_df, ["timestamp", "created_at", "reading_time", "time", "date_time"])
    sensor_col = find_column(mysql_df, ["sensor_id", "sensor", "device_id"])
    location_col = find_column(mysql_df, ["location", "room", "area"])
    temp_col = find_column(mysql_df, ["temperature", "temp"])
    hum_col = find_column(mysql_df, ["humidity", "hum"])
    aq_col = find_column(mysql_df, ["air_quality", "airquality", "aq", "air_quality_index"])
    status_col = find_column(mysql_df, ["status", "condition", "level"])

    latest_df = mysql_df.tail(10).sort_index(ascending=False)
    st.write("Latest readings:")
    st.dataframe(latest_df, use_container_width=True)

    chart_cols = [col for col in [temp_col, hum_col, aq_col] if col]

    if timestamp_col and chart_cols:
        chart_df = mysql_df[[timestamp_col] + chart_cols].dropna()
        if not chart_df.empty:
            chart_df = chart_df.set_index(timestamp_col)
            st.write("Environmental values over time:")
            st.line_chart(chart_df)

    col_a, col_b = st.columns(2)

    with col_a:
        if status_col:
            st.write("Status distribution:")
            status_counts = mysql_df[status_col].value_counts()
            st.bar_chart(status_counts)

    with col_b:
        if location_col:
            st.write("Readings by location:")
            location_counts = mysql_df[location_col].value_counts()
            st.bar_chart(location_counts)


st.divider()


# ---------- MongoDB raw messages ----------
st.subheader("Raw MQTT Messages from MongoDB")

if mongo_df.empty:
    st.warning("No MongoDB documents found yet.")
else:
    st.write("MongoDB stores the raw JSON-like messages received from MQTT.")
    st.dataframe(mongo_df.head(20), use_container_width=True)


st.divider()


# ---------- Neo4j graph summary ----------
st.subheader("Neo4j Graph Summary")

if neo4j_error:
    st.warning("Neo4j data cannot be shown because the connection failed.")
else:
    col1, col2 = st.columns(2)

    with col1:
        st.write("Node labels:")
        if neo4j_labels_df.empty:
            st.info("No Neo4j labels found.")
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


st.divider()


# ---------- Explanation section ----------
st.subheader("How this dashboard fits the project")

st.markdown(
    """
    **Project flow:**

    1. The Python publisher simulates environmental sensors.
    2. The publisher sends sensor readings to the Mosquitto MQTT broker.
    3. The Python subscriber receives the MQTT messages.
    4. The subscriber stores structured readings in **MySQL**.
    5. The subscriber stores raw JSON messages in **MongoDB**.
    6. The subscriber stores sensor-location-reading relationships in **Neo4j**.
    7. This dashboard reads the stored data and visualizes it.

    **Why three databases are used:**

    - **MySQL** is used for structured relational data.
    - **MongoDB** is used for raw flexible JSON/document data.
    - **Neo4j** is used for graph relationships between sensors, locations, and readings.
    """
)


# ---------- Refresh button ----------
if st.button("Refresh dashboard"):
    st.cache_data.clear()
    st.rerun()

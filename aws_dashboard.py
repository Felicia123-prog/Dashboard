import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="📈 AWS Temperatuur – Suriname", layout="wide")

# 📥 Data inladen
df = pd.read_excel("data/awsdata.xlsx")

# 🧼 Kolommen opschonen
df["StationID"] = df["StationID"].fillna("").astype(str).str.strip()
df["Temperature"] = pd.to_numeric(df["Temperature"], errors="coerce")
df["Dag"] = pd.to_numeric(df["Dag"], errors="coerce")
df["Tijd"] = pd.to_datetime(df["Tijd"], format="%H:%M:%S", errors="coerce").dt.time

# 🕒 Tijdopbouw: combineer Dag + Tijd tot volledige datetime
df["Datum"] = pd.to_datetime(
    "2025-10-" + df["Dag"].astype(int).astype(str).str.zfill(2) + " " + df["Tijd"].astype(str),
    errors="coerce"
)

df = df.dropna(subset=["Datum", "Temperature"])

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", sorted(df["StationID"].unique()))
beschikbare_datums = sorted(df[df["StationID"] == station]["Datum"].dt.date.unique())
datum_keuze = st.sidebar.selectbox("Kies een dag", beschikbare_datums)

# 📅 Filtering
filtered = df[
    (df["StationID"] == station) &
    (df["Datum"].dt.date == datum_keuze)
]

st.title("🌡️ Temperatuurverloop – AWS")
st.markdown(f"**Station:** {station}  \n**Datum:** {datum_keuze}")

if filtered.empty:
    st.warning("📭 Geen temperatuurgegevens voor deze selectie.")
    st.stop()

# 🧪 Tijdcontrole (debug)
with st.expander("🧪 Tijdcontrole per rij (debug)", expanded=False):
    st.dataframe(
        filtered[["StationID", "Datum", "Temperature"]]
        .sort_values("Datum")
        .reset_index(drop=True)
    )

# 📊 Visualisatie
chart = alt.Chart(filtered).mark_line(color="orange").encode(
    x="Datum:T",
    y="Temperature:Q",
    tooltip=[alt.Tooltip("Datum:T"), alt.Tooltip("Temperature:Q", title="Temperatuur (°C)")]
).properties(title="Temperatuur binnen dag (°C)")

st.altair_chart(chart, use_container_width=True)
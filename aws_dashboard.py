import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="📊 Combinatiegrafiek Temperatuur – AWS Suriname", layout="wide")

# 📥 Data inladen
df = pd.read_excel("data/awsdata.xlsx")

# ✅ Kolomcheck
required_columns = ["StationID", "Year", "Month", "Day",
                    "AVG_Temperature", "Max_Temperature", "Min_Temperature"]
missing = [col for col in required_columns if col not in df.columns]
if missing:
    st.error(f"❌ Ontbrekende kolommen: {', '.join(missing)}")
    st.stop()

# 🧼 Opschonen
df["StationID"] = df["StationID"].fillna("").astype(str).str.strip()
df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
df["Month"] = pd.to_numeric(df["Month"], errors="coerce").astype("Int64")
df["Day"] = pd.to_numeric(df["Day"], errors="coerce").astype("Int64")
df = df.dropna(subset=["Year", "Month", "Day"])

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", sorted(df["StationID"].unique()))
jaar_opties = sorted(df[df["StationID"] == station]["Year"].dropna().unique())
gekozen_jaar = st.sidebar.selectbox("Kies een jaar", jaar_opties)
maand_opties = sorted(df[(df["StationID"] == station) & (df["Year"] == gekozen_jaar)]["Month"].dropna().unique())
gekozen_maand = st.sidebar.selectbox("Kies een maand", maand_opties)

# 📅 Filter data
maand_df = df[
    (df["StationID"] == station) &
    (df["Year"] == gekozen_jaar) &
    (df["Month"] == gekozen_maand)
].copy()

if maand_df.empty:
    st.warning("📭 Geen gegevens voor deze selectie.")
    st.stop()

# 📊 Dagelijkse aggregatie
dagelijks = (
    maand_df.groupby(["Year", "Month", "Day"], as_index=False)
    .agg({
        "AVG_Temperature": "mean",
        "Max_Temperature": "mean",
        "Min_Temperature": "mean"
    })
)

# 📈 Combinatiegrafiek
st.title("📊 Combinatiegrafiek Temperatuur – AWS")
st.markdown(f"**Station:** {station}  \n**Periode:** {int(gekozen_jaar)}-{str(int(gekozen_maand)).zfill(2)}")

bars = alt.Chart(dagelijks).mark_bar(color="skyblue").encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y("AVG_Temperature:Q", title="Temperatuur (°C)"),
    tooltip=[alt.Tooltip("Day:O", title="Dag"), alt.Tooltip("AVG_Temperature:Q", title="Gemiddelde (°C)")]
)

line_max = alt.Chart(dagelijks).mark_line(color="red").encode(
    x="Day:O",
    y="Max_Temperature:Q",
    tooltip=[alt.Tooltip("Max_Temperature:Q", title="Maximum (°C)")]
)

line_min = alt.Chart(dagelijks).mark_line(color="green").encode(
    x="Day:O",
    y="Min_Temperature:Q",
    tooltip=[alt.Tooltip("Min_Temperature:Q", title="Minimum (°C)")]
)

st.altair_chart(bars + line_max + line_min, use_container_width=True)

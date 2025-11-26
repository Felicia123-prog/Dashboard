import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="📦 Boxplot Temperatuur – AWS Suriname", layout="wide")

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

# 📊 Data herschikken voor boxplot
boxdata = maand_df.melt(
    id_vars=["Day"],
    value_vars=["AVG_Temperature", "Max_Temperature", "Min_Temperature"],
    var_name="Type",
    value_name="Temperatuur"
)

# 📈 Boxplot
st.title("📦 Boxplot Temperatuur – AWS")
st.markdown(f"**Station:** {station}  \n**Periode:** {int(gekozen_jaar)}-{str(int(gekozen_maand)).zfill(2)}")

chart = alt.Chart(boxdata).mark_boxplot(extent="min-max").encode(
    x=alt.X("Type:N", title="Temperatuurtype"),
    y=alt.Y("Temperatuur:Q", title="Temperatuur (°C)"),
    color="Type:N"
).properties(title="Boxplot van temperatuurtypes")

st.altair_chart(chart, use_container_width=True)

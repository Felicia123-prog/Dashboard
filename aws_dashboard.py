import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="AWS data van Suriname", layout="wide")

# 📥 Data inladen
df = pd.read_excel("data/awsdata.xlsx")

# ✅ Kolomcheck (inclusief Rainfall en ruimte voor uitbreiding)
required_columns = ["StationID", "Year", "Month", "Day",
                    "AVG_Temperature", "Max_Temperature", "Min_Temperature", "Rainfall"]
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

# 📊 Dagelijkse aggregatie (ruimte voor uitbreiding met nieuwe elementen)
dagelijks = (
    maand_df.groupby(["Year", "Month", "Day"], as_index=False)
    .agg({
        "AVG_Temperature": "mean",
        "Max_Temperature": "mean",
        "Min_Temperature": "mean",
        "Rainfall": "mean"
    })
)

# 🌍 Algemene titel
st.title("🌍 AWS data van Suriname")
st.markdown(f"**Station:** {station}  \n**Periode:** {int(gekozen_jaar)}-{str(gekozen_maand).zfill(2)}")

# 📈 Temperatuur grafiek
st.header("🌡️ Temperatuur (Gemiddelde, Maximum, Minimum)")
bars = alt.Chart(dagelijks).mark_bar(color="skyblue").encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y("AVG_Temperature:Q", title="Temperatuur (°C)"),
    tooltip=["Day", "AVG_Temperature"]
)
line_max = alt.Chart(dagelijks).mark_line(color="red").encode(
    x="Day:O", y="Max_Temperature:Q", tooltip=["Day", "Max_Temperature"]
)
line_min = alt.Chart(dagelijks).mark_line(color="green").encode(
    x="Day:O", y="Min_Temperature:Q", tooltip=["Day", "Min_Temperature"]
)
st.altair_chart(bars + line_max + line_min, use_container_width=True)

# 🎨 Legenda
st.markdown("""
<div style="margin-top: 10px;">
<b>Legenda:</b><br>
🟦 Gemiddelde temperatuur (AVG_Temperature)<br>
🔴 Maximum temperatuur (Max_Temperature)<br>
🟢 Minimum temperatuur (Min_Temperature)
</div>
""", unsafe_allow_html=True)

# 📤 Downloadknop Temperatuur (JPEG)
fig, ax = plt.subplots()
ax.bar(dagelijks["Day"], dagelijks["AVG_Temperature"], color="skyblue", label="Gemiddelde")
ax.plot(dagelijks["Day"], dagelijks["Max_Temperature"], color="red", label="Maximum")
ax.plot(dagelijks["Day"], dagelijks["Min_Temperature"], color="green", label="Minimum")
ax.set_title("Temperatuur")
ax.set_xlabel("Dag van de maand")
ax.set_ylabel("Temperatuur (°C)")
ax.legend()
fig.tight_layout()
jpeg_buffer = io.BytesIO()
fig.savefig(jpeg_buffer, format="jpeg")
st.download_button(
    label="📥 Download temperatuur grafiek (JPEG)",
    data=jpeg_buffer.getvalue(),
    file_name=f"{station}_{gekozen_jaar}-{str(gekozen_maand).zfill(2)}_temperatuur.jpeg",
    mime="image/jpeg"
)

# 🌧️ Neerslag grafiek
st.header("🌧️ Dagelijkse Neerslag")
rain_chart = alt.Chart(dagelijks).mark_bar(color="dodgerblue").encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y("Rainfall:Q", title="Neerslag (mm)"),
    tooltip=["Day", "Rainfall"]
).properties(title="Dagelijkse neerslag (mm)")
st.altair_chart(rain_chart, use_container_width=True)

# 📤 Downloadknop Neerslag (JPEG)
fig2, ax2 = plt.subplots()
ax2.bar(dagelijks["Day"], dagelijks["Rainfall"], color="dodgerblue", label="Neerslag")
ax2.set_title("Neerslag")
ax2.set_xlabel("Dag van de maand")
ax2.set_ylabel("Neerslag (mm)")
ax2.legend()
fig2.tight_layout()
jpeg_buffer2 = io.BytesIO()
fig2.savefig(jpeg_buffer2, format="jpeg")
st.download_button(
    label="📥 Download neerslag grafiek (JPEG)",
    data=jpeg_buffer2.getvalue(),
    file_name=f"{station}_{gekozen_jaar}-{str(gekozen_maand).zfill(2)}_neerslag.jpeg",
    mime="image/jpeg"
)

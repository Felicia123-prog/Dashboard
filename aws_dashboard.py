import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import io
import calendar

st.set_page_config(page_title="AWS data van Suriname", layout="wide")

# 📥 Data inladen
df = pd.read_excel("data/awsdata.xlsx")

# ✅ Kolomcheck
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

# 📊 Dagelijkse aggregatie
dagelijks = (
    maand_df.groupby(["Year", "Month", "Day"], as_index=False)
    .agg({
        "AVG_Temperature": "mean",
        "Max_Temperature": "mean",
        "Min_Temperature": "mean",
        "Rainfall": "mean",
        "WindSpeedAVG": "mean",       # gemiddelde windsnelheid
        "WindSpeedMax": "max",        # maximale windsnelheid
        "WindDirectionAVG": "mean"    # gemiddelde windrichting per dag
    })
)

# 🔢 Volledige dagreeks garanderen (1..aantal dagen van maand)
aantal_dagen = calendar.monthrange(int(gekozen_jaar), int(gekozen_maand))[1]
volledige_dagen = pd.DataFrame({"Day": list(range(1, aantal_dagen + 1))})
# Merge zodat alle dagen op de x-as komen
dagelijks_full = volledige_dagen.merge(dagelijks, on="Day", how="left")
dagelijks_full["Year"] = gekozen_jaar
dagelijks_full["Month"] = gekozen_maand

# 🌍 Algemene titel
st.title("🌍 AWS data van Suriname")
st.markdown(f"**Station:** {station}  \n**Periode:** {int(gekozen_jaar)}-{str(int(gekozen_maand)).zfill(2)}")

# =========================
# 🌡️ Temperatuursectie
# =========================
st.header("🌡️ Temperatuur (Gemiddelde, Maximum, Minimum)")

bars = alt.Chart(dagelijks_full).mark_bar(color="skyblue").encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y("AVG_Temperature:Q", title="Temperatuur (°C)"),
    tooltip=["Day", "AVG_Temperature"]
)

line_max = alt.Chart(dagelijks_full).mark_line(color="red").encode(
    x="Day:O", y="Max_Temperature:Q", tooltip=["Day", "Max_Temperature"]
)

line_min = alt.Chart(dagelijks_full).mark_line(color="green").encode(
    x="Day:O", y="Min_Temperature:Q", tooltip=["Day", "Min_Temperature"]
)

st.altair_chart(bars + line_max + line_min, use_container_width=True)

# 🎨 Legenda temperatuur
st.markdown("""
<div style="margin-top: 10px;">
<b>Legenda:</b><br>
🟦 Gemiddelde temperatuur (AVG_Temperature)<br>
🔴 Maximum temperatuur (Max_Temperature)<br>
🟢 Minimum temperatuur (Min_Temperature)
</div>
""", unsafe_allow_html=True)

# 📥 Download temperatuur JPEG
fig, ax = plt.subplots()
ax.bar(dagelijks_full["Day"], dagelijks_full["AVG_Temperature"], color="skyblue", label="Gemiddelde")
ax.plot(dagelijks_full["Day"], dagelijks_full["Max_Temperature"], color="red", label="Maximum")
ax.plot(dagelijks_full["Day"], dagelijks_full["Min_Temperature"], color="green", label="Minimum")
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

# =========================
# 🌧️ Neerslagsectie
# =========================
st.header("🌧️ Dagelijkse Neerslag")

# 🧠 Voor grafiek: status en zichtbaar 0.0 labels
rain_df = dagelijks_full.copy()

# Status bepalen: NA / Droog / Nat
def _status(val):
    if pd.isna(val):
        return "Geen data"
    return "Droge dag" if val < 1 else "Natte dag"

rain_df["Status"] = rain_df["Rainfall"].apply(_status)

# Voor weergave: droog = 0.0 (letterlijk tonen), nat = waarde
rain_df["Rainfall_display"] = rain_df["Rainfall"].apply(lambda x: 0.0 if (not pd.isna(x) and x < 1) else x)

# Kleuren
kleur_map = {
    "Geen data": "lightgray",
    "Droge dag": "green",
    "Natte dag": "dodgerblue"
}

# 📊 Staven (NA-dagen worden niet getekend als staaf)
bars_rain = alt.Chart(rain_df[rain_df["Status"] != "Geen data"]).mark_bar().encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y("Rainfall_display:Q", title="Neerslag (mm)"),
    color=alt.Color("Status:N", scale=alt.Scale(domain=list(kleur_map.keys()), range=list(kleur_map.values())),
                    legend=alt.Legend(title="Dagstatus")),
    tooltip=["Day", alt.Tooltip("Rainfall_display:Q", title="Neerslag (mm)"), "Status"]
)

# 🔘 Statuspunt onder de x-as voor NA-dagen
punten_na = alt.Chart(rain_df[rain_df["Status"] == "Geen data"]).mark_point(size=60, shape="circle", filled=True).encode(
    x=alt.X("Day:O"),
    y=alt.value(-1),  # onder de as
    color=alt.Color("Status:N", scale=alt.Scale(domain=list(kleur_map.keys()), range=list(kleur_map.values())),
                    legend=None),
    tooltip=["Day", "Status"]
)

# 🏷️ Tekstlabels "0.0" op droge dagen (zichtbaar op de basislijn)
labels_zero = alt.Chart(rain_df[rain_df["Status"] == "Droge dag"]).mark_text(
    dy=-4,  # net boven de as
    fontSize=11,
    color="green"
).encode(
    x=alt.X("Day:O"),
    y=alt.value(0),
    text=alt.value("0.0")
)

st.altair_chart(bars_rain + punten_na + labels_zero, use_container_width=True)

# 🎨 Legenda neerslag
st.markdown("""
<div style="margin-top: 10px;">
<b>Legenda:</b><br>
🔵 Natte dag (≥ 1 mm)<br>
🟩 Droge dag (< 1 mm → 0.0 mm zichtbaar)<br>
⚪️ Geen data beschikbaar (NA) – punt onder de as
</div>
""", unsafe_allow_html=True)

# 📥 Download neerslag JPEG (met 0.0 labels)
fig2, ax2 = plt.subplots()

for _, row in rain_df.iterrows():
    day = int(row["Day"])
    status = row["Status"]
    val = row["Rainfall"]
    if status == "Geen data":
        # klein grijs punt onder de as (visueel indicatief)
        ax2.plot(day, -0.2, marker="o", color="lightgray")
        continue
    # Droge dag: 0.0 en groen
    if val < 1:
        ax2.bar(day, 0.0, color="green")
        ax2.text(day, 0.1, "0.0", color="green", ha="center", va="bottom", fontsize=9)
    else:
        ax2.bar(day, val, color="dodgerblue")

ax2.set_title("Neerslag")
ax2.set_xlabel("Dag van de maand")
ax2.set_ylabel("Neerslag (mm)")
ax2.set_ylim(bottom=-0.5)  # ruimte voor NA-punten onder de as
fig2.tight_layout()

jpeg_buffer2 = io.BytesIO()
fig2.savefig(jpeg_buffer2, format="jpeg")
st.download_button(
    label="📥 Download neerslag grafiek (JPEG)",
    data=jpeg_buffer2.getvalue(),
    file_name=f"{station}_{gekozen_jaar}-{str(gekozen_maand).zfill(2)}_neerslag.jpeg",
    mime="image/jpeg"
)
# 🌬️ Dagelijkse Windsnelheid
st.header("🌬️ Dagelijkse Windsnelheid")

# 📊 Staafdiagram voor gemiddelde windsnelheid
bars_wind = alt.Chart(dagelijks).mark_bar(color="skyblue").encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y("WindSpeedAVG:Q", title="Gemiddelde windsnelheid"),
    tooltip=["Day", "WindSpeedAVG"]
)

# 📈 Lijn voor maximale windsnelheid
line_max_wind = alt.Chart(dagelijks).mark_line(color="red").encode(
    x="Day:O",
    y="WindSpeedMax:Q",
    tooltip=["Day", "WindSpeedMax"]
)

st.altair_chart(bars_wind + line_max_wind, use_container_width=True)

# 🎨 Legenda windsnelheid
st.markdown("""
<div style="margin-top: 10px;">
<b>Legenda:</b><br>
🟦 Gemiddelde windsnelheid (WindSpeedAVG)<br>
🔴 Maximale windsnelheid (WindSpeedMax)
</div>
""", unsafe_allow_html=True)

# 📥 Download windsnelheid JPEG
fig3, ax3 = plt.subplots()
ax3.bar(dagelijks["Day"], dagelijks["WindSpeedAVG"], color="skyblue", label="Gemiddelde")
ax3.plot(dagelijks["Day"], dagelijks["WindSpeedMax"], color="red", label="Maximum")
ax3.set_title("Windsnelheid")
ax3.set_xlabel("Dag van de maand")
ax3.set_ylabel("Windsnelheid (knopen of m/s)")
ax3.legend()
fig3.tight_layout()

jpeg_buffer3 = io.BytesIO()
fig3.savefig(jpeg_buffer3, format="jpeg")
st.download_button(
    label="📥 Download windsnelheid grafiek (JPEG)",
    data=jpeg_buffer3.getvalue(),
    file_name=f"{station}_{gekozen_jaar}-{str(gekozen_maand).zfill(2)}_windsnelheid.jpeg",
    mime="image/jpeg"
)
# =========================
# 🧭 Windrichtingsectie (Windroos)
# =========================
st.header("🧭 Windrichting – Windroos")

# Mapping van windrichting naar graden
richting_map = {
    "N": 0, "NE": 45, "E": 90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315
}

wind_df = dagelijks_full.copy()
wind_df = wind_df.dropna(subset=["WindDirectionAVG", "WindSpeedAVG"])
wind_df["Degrees"] = wind_df["WindDirectionAVG"].map(richting_map)

# 🎨 Windroos plot (hoogte = gemiddelde windsnelheid)
fig4, ax4 = plt.subplots(subplot_kw={"projection": "polar"})
angles = wind_df["Degrees"] * (3.14159/180)  # graden naar radian
bars = ax4.bar(angles, wind_df["WindSpeedAVG"], width=0.7,
               color="dodgerblue", edgecolor="black")

ax4.set_theta_zero_location("N")  # Noord bovenaan
ax4.set_theta_direction(-1)       # klokwijzer richting
ax4.set_title("Windroos – Gemiddelde windsnelheid per richting")

# 📥 Download windroos JPEG
jpeg_buffer4 = io.BytesIO()
fig4.savefig(jpeg_buffer4, format="jpeg")
st.download_button(
    label="📥 Download windroos (JPEG)",
    data=jpeg_buffer4.getvalue(),
    file_name=f"{station}_{gekozen_jaar}-{str(gekozen_maand).zfill(2)}_windroos.jpeg",
    mime="image/jpeg"
)



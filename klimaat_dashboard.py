import streamlit as st
import pandas as pd
import altair as alt
import io
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# 📥 Stap 1: Laad het Excel-bestand
df = pd.read_excel("data/Klimaatdata.xlsx")

# 🧼 Stap 2: Forceer numeriek datatype
for kolom in [
    "DryBulb T.", "RH", "Total Cloud Coverage",
    "Wind direction", "Wind Velocity", "Pressure"
]:
    df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

# 🧼 Stap 3: Zet '00z', '01z', … om naar 'HH:MM'
df["TijdUTC"] = df["Time"].astype(str).str.replace("z", "", regex=False).str.zfill(2) + ":00"

# 🧼 Stap 4: Bouw veilige datetime-kolom
df["Datum"] = pd.to_datetime(
    df["Year"].astype(str) + "-" +
    df["Month"].astype(str).str.zfill(2) + "-" +
    df["Day"].astype(str).str.zfill(2) + " " +
    df["TijdUTC"],
    errors="coerce"
)

# 🧼 Stap 5: Verwijder ongeldige datums
df = df.dropna(subset=["Datum"])

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", df["StationID"].unique())
datum_range = st.sidebar.date_input("Selecteer een datumbereik", [df["Datum"].min().date(), df["Datum"].max().date()])

# 🧮 Filter de data op station en datum
if isinstance(datum_range, list) and len(datum_range) == 2:
    start_date, end_date = datum_range
    filtered = df[
        (df["StationID"] == station) &
        (df["Datum"].dt.date >= start_date) &
        (df["Datum"].dt.date <= end_date)
    ]
else:
    st.warning("⚠️ Selecteer een geldig datumbereik met twee datums.")
    filtered = pd.DataFrame()

# 📅 Laatste datum in dataset
st.markdown(f"📅 Laatste datum in dataset: **{df['Datum'].max().strftime('%d %B %Y %H:%M')} UTC**")

# 🧾 Titel en metadata
st.title("🌦️ Klimaat per station – testversie")
if not filtered.empty:
    st.markdown(f"**Station:** {station}  \n**Periode:** {start_date} tot {end_date}")

# 📊 Temperatuurgrafiek
if not filtered["DryBulb T."].dropna().empty:
    temp_chart = alt.Chart(filtered.dropna(subset=["DryBulb T."])).mark_line().encode(
        x="Datum:T",
        y="DryBulb T.:Q",
        color=alt.value("orange"),
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("DryBulb T.:Q", title="Temperatuur (°C)")
        ]
    ).properties(title="Gemiddelde temperatuur per dag (°C)")
    st.altair_chart(temp_chart, use_container_width=True)
else:
    st.info("📭 Geen temperatuurdata beschikbaar voor deze selectie.")

# 💧 Relatieve vochtigheid
if not filtered["RH"].dropna().empty:
    rh_chart = alt.Chart(filtered.dropna(subset=["RH"])).mark_line(color="blue").encode(
        x="Datum:T",
        y="RH:Q",
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("RH:Q", title="Relatieve vochtigheid (%)")
        ]
    ).properties(title="Relatieve vochtigheid per dag (%)")
    st.altair_chart(rh_chart, use_container_width=True)
else:
    st.info("📭 Geen vochtigheidsdata beschikbaar.")

# ☁️ Bewolking
if not filtered["Total Cloud Coverage"].dropna().empty:
    cloud_chart = alt.Chart(filtered.dropna(subset=["Total Cloud Coverage"])).mark_bar(color="lightblue").encode(
        x="Datum:T",
        y="Total Cloud Coverage:Q",
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("Total Cloud Coverage:Q", title="Bewolking (oktas)")
        ]
    ).properties(title="Totale bewolking per dag (oktas)")
    st.altair_chart(cloud_chart, use_container_width=True)
else:
    st.info("📭 Geen bewolkingsdata beschikbaar.")

# 💨 Windsnelheid
if not filtered["Wind Velocity"].dropna().empty:
    wind_chart = alt.Chart(filtered.dropna(subset=["Wind Velocity"])).mark_line(color="gray").encode(
        x="Datum:T",
        y="Wind Velocity:Q",
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("Wind Velocity:Q", title="Windsnelheid (knopen)")
        ]
    ).properties(title="Windsnelheid per dag (knopen)")
    st.altair_chart(wind_chart, use_container_width=True)
else:
    st.info("📭 Geen windsnelheidsdata beschikbaar.")

# 🧭 Windrichting
if not filtered["Wind direction"].dropna().empty:
    dir_chart = alt.Chart(filtered.dropna(subset=["Wind direction"])).mark_line(color="purple").encode(
        x="Datum:T",
        y="Wind direction:Q",
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("Wind direction:Q", title="Windrichting (°)")
        ]
    ).properties(title="Windrichting per dag (°)")
    st.altair_chart(dir_chart, use_container_width=True)
else:
    st.info("📭 Geen windrichtingsdata beschikbaar.")

# 🧭 Windroos
if not filtered["Wind direction"].dropna().empty and not filtered["Wind Velocity"].dropna().empty:
    filtered["WindDirBin"] = pd.cut(
        filtered["Wind direction"],
        bins=np.arange(0, 361, 30),
        labels=[f"{i}°–{i+30}°" for i in range(0, 360, 30)],
        include_lowest=True
    )
    windroos_data = filtered.groupby("WindDirBin")["Wind Velocity"].mean().reset_index()
    windroos_data.dropna(inplace=True)

    def bin_to_angle(label):
        start = int(label.split("°")[0])
        return np.deg2rad(start + 15)

    angles = windroos_data["WindDirBin"].apply(bin_to_angle).values
    speeds = windroos_data["Wind Velocity"].values

    fig_roos, ax_roos = plt.subplots(subplot_kw={'projection': 'polar'})
    ax_roos.bar(angles, speeds, width=np.deg2rad(30), bottom=0, color='skyblue', edgecolor='gray')
    ax_roos.set_theta_zero_location("N")
    ax_roos.set_theta_direction(-1)
    ax_roos.set_title("🌬️ Windroos – Windsnelheid per richting", va='bottom')
    st.pyplot(fig_roos)
else:
    st.info("📭 Geen windroos mogelijk – ontbrekende richting of snelheid.")

# 📌 Samenvattende indicatoren
st.subheader("📌 Samenvatting")
col1, col2, col3 = st.columns(3)
col1.metric("Gem. temperatuur (°C)", f"{filtered['DryBulb T.'].mean():.1f}" if not filtered["DryBulb T."].dropna().empty else "—")
col2.metric("Gem. relatieve vocht (%)", f"{filtered['RH'].mean():.1f}" if not filtered["RH"].dropna().empty else "—")
col3.metric("Gem. windsnelheid (knopen)", f"{filtered['Wind Velocity'].mean():.1f}" if not filtered["Wind Velocity"].dropna().empty else "—")

# 📥 Download als CSV
if not filtered.empty:
    st.download_button(
        label="📥 Download als CSV",
        data=filtered.to_csv(index=False).encode('utf-8'),
        file_name=f"{station}_klimaatdata.csv",
        mime="text/csv"
    )
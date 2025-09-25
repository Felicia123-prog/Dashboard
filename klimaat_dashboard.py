import streamlit as st
import pandas as pd
import altair as alt
import io
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# 📥 Laad het Excel-bestand
df = pd.read_excel("data/Klimaatdata.xlsx")

# 🧼 Forceer numeriek datatype
for kolom in [
    "Temperature", "RH", "Total Cloud Coverage",
    "Wind direction", "Wind Velocity", "Pressure"
]:
    df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

# 🧼 Zet '00z', '01z', … om naar 'HH:MM'
df["TijdUTC"] = df["Time"].astype(str).str.replace("z", "", regex=False).str.zfill(2) + ":00"

# 🧼 Bouw veilige datetime-kolom
df["Datum"] = pd.to_datetime(
    df["Year"].astype(str) + "-" +
    df["Month"].astype(str).str.zfill(2) + "-" +
    df["Day"].astype(str).str.zfill(2) + " " +
    df["TijdUTC"],
    errors="coerce"
)

df = df.dropna(subset=["Datum"])

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", df["StationID"].unique())
datum_range = st.sidebar.date_input("Selecteer een datumbereik", [df["Datum"].min().date(), df["Datum"].max().date()])

# 🧮 Filter de data
if isinstance(datum_range, list) and len(datum_range) == 2:
    start_date, end_date = datum_range
    filtered = df[
        (df["StationID"] == station) &
        (df["Datum"].dt.date >= start_date) &
        (df["Datum"].dt.date <= end_date)
    ]
else:
    st.warning("⚠️ Selecteer een geldig datumbereik.")
    filtered = pd.DataFrame()

# 📅 Laatste datum
st.markdown(f"📅 Laatste datum in dataset: **{df['Datum'].max().strftime('%d %B %Y %H:%M')} UTC**")

# 🧾 Titel
st.title("🌦️ Klimaat per station – testversie")
if not filtered.empty:
    st.markdown(f"**Station:** {station}  \n**Periode:** {start_date} tot {end_date}")

# 📊 Temperature
if not filtered.empty and "Temperature" in filtered.columns and not filtered["Temperature"].dropna().empty:
    temp_chart = alt.Chart(filtered.dropna(subset=["Temperature"])).mark_line().encode(
        x="Datum:T",
        y="Temperature:Q",
        color=alt.value("orange"),
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("Temperature:Q", title="Temperatuur (°C)")
        ]
    ).properties(title="Gemiddelde temperatuur per dag (°C)")
    st.altair_chart(temp_chart, use_container_width=True)
else:
    st.info("📭 Geen temperatuurdata beschikbaar.")

# 💧 RH
if "RH" in filtered.columns and not filtered["RH"].dropna().empty:
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
if "Total Cloud Coverage" in filtered.columns and not filtered["Total Cloud Coverage"].dropna().empty:
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
if "Wind Velocity" in filtered.columns and not filtered["Wind Velocity"].dropna().empty:
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
if "Wind direction" in filtered.columns and not filtered["Wind direction"].dropna().empty:
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
if "Wind direction" in filtered.columns and "Wind Velocity" in filtered.columns:
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

    if len(angles) == len(speeds) and len(angles) > 0:
        fig_roos, ax_roos = plt.subplots(subplot_kw={'projection': 'polar'})
        ax_roos.bar(angles, speeds, width=np.deg2rad(30), bottom=0, color='skyblue', edgecolor='gray')
        ax_roos.set_theta_zero_location("N")
        ax_roos.set_theta_direction(-1)
        ax_roos.set_title("🌬️ Windroos – Windsnelheid per richting", va='bottom')
        st.pyplot(fig_roos)
    else:
        st.info("📭 Windroosdata is onvolledig.")
else:
    st.info("📭 Geen windroos mogelijk – ontbrekende richting of snelheid.")

# 📌 Samenvattende indicatoren
st.subheader("📌 Samenvatting")
col1, col2, col3 = st.columns(3)
col1.metric("Gem. temperatuur (°C)", f"{filtered['Temperature'].mean():.1f}" if "Temperature" in filtered.columns and not filtered["Temperature"].dropna().empty else "—")
col2.metric("Gem. relatieve vocht (%)", f"{filtered['RH'].mean():.1f}" if "RH" in filtered.columns and not filtered["RH"].dropna().empty else "—")
col3.metric("Gem. windsnelheid (knopen)", f"{filtered['Wind Velocity'].mean():.1f}" if "Wind Velocity" in filtered.columns and not filtered["Wind Velocity"].dropna().empty else "—")

# 📥 Download als CSV
if not filtered.empty:
    st.download_button(
        label="📥 Download als CSV",
        data=filtered.to_csv(index=False).encode('utf-8'),
        file_name=f"{station}_klimaatdata.csv",
        mime="text/csv"
    )
        # 📤 Genereer grafiekafbeeldingen
    fig_paths = {}

    def save_plot(fig, name):
        path = f"{station}_{name}.png"
        fig.savefig(path)
        plt.close(fig)
        fig_paths[name] = path

    if "Temperature" in filtered.columns and not filtered["Temperature"].dropna().empty:
        fig, ax = plt.subplots()
        ax.plot(filtered["Datum"], filtered["Temperature"], color="orange")
        ax.set_title("Temperatuur per dag")
        save_plot(fig, "temp")

    if "RH" in filtered.columns and not filtered["RH"].dropna().empty:
        fig, ax = plt.subplots()
        ax.plot(filtered["Datum"], filtered["RH"], color="blue")
        ax.set_title("Relatieve vochtigheid per dag")
        save_plot(fig, "rh")

    if "Pressure" in filtered.columns and not filtered["Pressure"].dropna().empty:
        fig, ax = plt.subplots()
        ax.plot(filtered["Datum"], filtered["Pressure"], color="green")
        ax.set_title("Luchtdruk per dag")
        save_plot(fig, "pressure")

    if "Wind Velocity" in filtered.columns and not filtered["Wind Velocity"].dropna().empty:
        fig, ax = plt.subplots()
        ax.plot(filtered["Datum"], filtered["Wind Velocity"], color="gray")
        ax.set_title("Windsnelheid per dag")
        save_plot(fig, "wind")

    if "Wind direction" in filtered.columns and not filtered["Wind direction"].dropna().empty:
        fig, ax = plt.subplots()
        ax.plot(filtered["Datum"], filtered["Wind direction"], color="purple")
        ax.set_title("Windrichting per dag")
        save_plot(fig, "dir")

    if "Total Cloud Coverage" in filtered.columns and not filtered["Total Cloud Coverage"].dropna().empty:
        fig, ax = plt.subplots()
        ax.bar(filtered["Datum"], filtered["Total Cloud Coverage"], color="lightblue")
        ax.set_title("Bewolking per dag")
        save_plot(fig, "cloud")

    if "WindDirBin" in filtered.columns and "Wind Velocity" in filtered.columns:
        windroos_data = filtered.groupby("WindDirBin")["Wind Velocity"].mean().reset_index()
        windroos_data.dropna(inplace=True)
        if not windroos_data.empty:
            def bin_to_angle(label):
                start = int(label.split("°")[0])
                return np.deg2rad(start + 15)
            angles = windroos_data["WindDirBin"].apply(bin_to_angle).values
            speeds = windroos_data["Wind Velocity"].values
            if len(angles) == len(speeds):
                fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
                ax.bar(angles, speeds, width=np.deg2rad(30), bottom=0, color='skyblue', edgecolor='gray')
                ax.set_theta_zero_location("N")
                ax.set_theta_direction(-1)
                ax.set_title("Windroos – Windsnelheid per richting")
                save_plot(fig, "roos")

    # 📄 Genereer PDF-rapport
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(2*cm, 28*cm, f"📄 Klimaatrapport – {station}")
    c.drawString(2*cm, 27.3*cm, f"Periode: {start_date} tot {end_date}")

   y = 26.6*cm
for label, value in [
    ("Gem. temperatuur (°C)", filtered["Temperature"].mean()),
    ("Gem. relatieve vochtigheid (%)", filtered["RH"].mean()),
    ("Gem. windsnelheid (knopen)", filtered["Wind Velocity"].mean()),
    ("Gem. luchtdruk (hPa)", filtered["Pressure"].mean()),
    ("Gem. bewolking (oktas)", filtered["Total Cloud Coverage"].mean())
]:
    if pd.notna(value):
        c.drawString(2*cm, y, f"{label}: {value:.1f}")
        y -= 0.6*cm

    draw_metric("Gem. temperatuur (°C)", filtered["Temperature"].mean())
    draw_metric("Gem. relatieve vochtigheid (%)", filtered["RH"].mean())
    draw_metric("Gem. windsnelheid (knopen)", filtered["Wind Velocity"].mean())
    draw_metric("Gem. luchtdruk (hPa)", filtered["Pressure"].mean())
    draw_metric("Gem. bewolking (oktas)", filtered["Total Cloud Coverage"].mean())

    # 📊 Voeg grafieken toe aan PDF
    grafiek_volgorde = ["temp", "rh", "pressure", "wind", "dir", "cloud", "roos"]
    pagina_grafieken = 0
    for i, key in enumerate(grafiek_volgorde):
        if key in fig_paths:
            y_pos = 17*cm - (8.5*cm * (i % 3))
            c.drawImage(fig_paths[key], 2*cm, y_pos, width=16*cm, height=8*cm)
            if (i + 1) % 3 == 0:
                c.showPage()
                c.setFont("Helvetica", 12)

    c.showPage()
    c.save()

    # 📥 Downloadknop voor PDF
    st.download_button(
        label="📄 Download visueel rapport (PDF)",
        data=pdf_buffer.getvalue(),
        file_name=f"{station}_klimaatrapport.pdf",
        mime="application/pdf"
    )
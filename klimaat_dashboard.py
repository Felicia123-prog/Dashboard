import streamlit as st
import pandas as pd
import altair as alt
import io
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# 📥 Data inladen
df = pd.read_excel("data/Klimaatdata.xlsx")

# 🧼 Kolommen converteren
verwachte_kolommen = ["Temperature", "RH", "Total Cloud Coverage", "Wind direction", "Wind Velocity", "Pressure"]
for kolom in verwachte_kolommen:
    if kolom in df.columns:
        df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

# 🕒 Tijdcorrectie van UTC naar Surinaamse tijd (UTC−3)
df["DatumUTC"] = pd.to_datetime(
    df["Year"].astype(str) + "-" +
    df["Month"].astype(str).str.zfill(2) + "-" +
    df["Day"].astype(str).str.zfill(2) + " " +
    df["Time"].astype(str).str.zfill(2) + ":00",
    errors="coerce"
)
df["Datum"] = df["DatumUTC"] - pd.Timedelta(hours=3)
df = df.dropna(subset=["Datum"])
df["StationID"] = df["StationID"].astype(str)

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", df["StationID"].unique())
beschikbare_datums = df[df["StationID"] == station]["Datum"].dt.date.unique()
datum_keuze = st.sidebar.selectbox("Kies een dag", beschikbare_datums)

# 📅 Filtering
filtered = df[
    (df["StationID"] == station) &
    (df["Datum"].dt.date == datum_keuze)
]

st.title("🌦️ Wat gebeurde er vandaag? – dagverloop van verschillende meteorologische elementen")
st.markdown(f"**Station:** {station}  \n**Datum:** {datum_keuze}")

if filtered.empty:
    st.warning("📭 Geen gegevens voor deze selectie. Controleer station en datum.")
    st.stop()

# 📊 Visualisatie
def plot_element(kolom, kleur, titel, eenheid):
    if kolom in filtered.columns and not filtered[kolom].dropna().empty:
        chart = alt.Chart(filtered.dropna(subset=[kolom])).mark_line(color=kleur).encode(
            x="Datum:T",
            y=f"{kolom}:Q",
            tooltip=[alt.Tooltip("Datum:T"), alt.Tooltip(f"{kolom}:Q", title=f"{titel} ({eenheid})")]
        ).properties(title=f"{titel} binnen dag ({eenheid})")
        st.altair_chart(chart, use_container_width=True)

plot_element("Temperature", "orange", "Temperatuur", "°C")
plot_element("RH", "blue", "Relatieve vochtigheid", "%")
plot_element("Total Cloud Coverage", "lightblue", "Bewolking", "oktas")
plot_element("Pressure", "green", "Luchtdruk", "hPa")
plot_element("Wind Velocity", "gray", "Windsnelheid", "knopen")
plot_element("Wind direction", "purple", "Windrichting", "°")

# 📊 Windroos op pagina (Synop – snelheid + frequentie)
if "Wind direction" in filtered.columns and "Wind Velocity" in filtered.columns:
    filtered["WindDirBin"] = pd.cut(
        filtered["Wind direction"],
        bins=np.arange(0, 361, 30),
        labels=[f"{i}°–{i+30}°" for i in range(0, 360, 30)],
        include_lowest=True
    )

    # Gemiddelde snelheid per richtingbin
    windroos_speed = filtered.groupby("WindDirBin")["Wind Velocity"].mean().reset_index()
    windroos_speed.dropna(inplace=True)

    # Frequentie per richtingbin
    windroos_freq = filtered["WindDirBin"].value_counts().reset_index()
    windroos_freq.columns = ["WindDirBin", "Count"]

    def bin_to_angle(label):
        start = int(label.split("°")[0])
        return np.deg2rad(start + 15)

    angles_speed = windroos_speed["WindDirBin"].apply(bin_to_angle).values
    speeds = windroos_speed["Wind Velocity"].values

    angles_freq = windroos_freq["WindDirBin"].apply(bin_to_angle).values
    counts = windroos_freq["Count"].values

    if len(angles_speed) == len(speeds) and len(angles_freq) == len(counts):
        fig_roos, (ax1, ax2) = plt.subplots(1, 2, figsize=(5, 2.4),
                                            subplot_kw={'projection': 'polar'})

        # 🔹 Snelheid per richting
        ax1.bar(angles_speed, speeds, width=np.deg2rad(30), bottom=0,
                color='skyblue', edgecolor='gray')
        ax1.set_theta_zero_location("N")
        ax1.set_theta_direction(-1)
        ax1.set_title("Gemiddelde snelheid (knopen)", fontsize=7, va='bottom')

        # 🔹 Frequentie per richting
        ax2.bar(angles_freq, counts, width=np.deg2rad(30), bottom=0,
                color='lightgreen', edgecolor='gray')
        ax2.set_theta_zero_location("N")
        ax2.set_theta_direction(-1)
        ax2.set_title("Frequentie (aantal)", fontsize=7, va='bottom')

        # Richtinglabels + graden
        ticks_deg = [0, 45, 90, 135, 180, 225, 270, 315]
        labels = ["N (0°)", "NE (45°)", "E (90°)", "SE (135°)",
                  "S (180°)", "SW (225°)", "W (270°)", "NW (315°)"]
        for ax in [ax1, ax2]:
            ax.set_xticks([deg * (3.14159 / 180) for deg in ticks_deg])
            ax.set_xticklabels(labels, fontsize=6)

        plt.tight_layout(pad=0.3)

        # ✅ Windrozen tonen
        st.pyplot(fig_roos)

        # 📤 Opslaan voor PDF
        fig_paths = {}
        def save_plot(fig, name):
            path = f"{station}_{name}.png"
            fig.savefig(path)
            plt.close(fig)
            fig_paths[name] = path

        save_plot(fig_roos, "roos_duo")

# 📄 PDF-generatie
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Klimaatrapport – {station}")
c.drawString(2*cm, 27.3*cm, f"Datum: {datum_keuze}")

# 📊 Voeg grafieken toe aan PDF
grafiek_volgorde = ["temp", "rh", "pressure", "wind", "dir", "cloud", "roos_duo"]
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
pdf_name = f"{station}_{datum_keuze}_klimaatrapport.pdf"
st.download_button(
    label="📄 Download visueel rapport (PDF)",
    data=pdf_buffer.getvalue(),
    file_name=pdf_name,
    mime="application/pdf"
)

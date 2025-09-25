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

# 🧼 Kolommen converteren naar numeriek (indien aanwezig)
verwachte_kolommen = ["Temperature", "RH", "Total Cloud Coverage", "Wind direction", "Wind Velocity", "Pressure"]
for kolom in verwachte_kolommen:
    if kolom in df.columns:
        df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

# 🧼 Tijd en datum samenvoegen
df["TijdUTC"] = df["Time"].astype(str).str.replace("z", "", regex=False).str.zfill(2) + ":00"
df["Datum"] = pd.to_datetime(
    df["Year"].astype(str) + "-" +
    df["Month"].astype(str).str.zfill(2) + "-" +
    df["Day"].astype(str).str.zfill(2) + " " +
    df["TijdUTC"],
    errors="coerce"
)
df = df.dropna(subset=["Datum"])
df["StationID"] = df["StationID"].astype(str)

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", df["StationID"].unique())
datum_range = st.sidebar.date_input("Selecteer een datumbereik", [df["Datum"].min().date(), df["Datum"].max().date()])
station = str(station)

# 🧮 Filtering
if isinstance(datum_range, list) and len(datum_range) == 2:
    start_date, end_date = datum_range
    filtered = df[
        (df["StationID"] == station) &
        (df["Datum"].dt.date >= pd.to_datetime(start_date).date()) &
        (df["Datum"].dt.date <= pd.to_datetime(end_date).date())
    ]
else:
    st.warning("⚠️ Selecteer een geldig datumbereik.")
    filtered = pd.DataFrame()

# 📅 Metadata
st.title("🌦️ Klimaat per station – testversie")
if not filtered.empty:
    st.markdown(f"**Station:** {station}  \n**Periode:** {start_date} tot {end_date}")

# 📊 Grafieken
def plot_element(kolom, kleur, titel, eenheid, chart_type="line"):
    if kolom in filtered.columns and not filtered[kolom].dropna().empty:
        data = filtered.dropna(subset=[kolom])
        if chart_type == "line":
            chart = alt.Chart(data).mark_line(color=kleur).encode(
                x="Datum:T",
                y=f"{kolom}:Q",
                tooltip=[alt.Tooltip("Datum:T"), alt.Tooltip(f"{kolom}:Q", title=f"{titel} ({eenheid})")]
            ).properties(title=f"{titel} per dag ({eenheid})")
        else:
            chart = alt.Chart(data).mark_bar(color=kleur).encode(
                x="Datum:T",
                y=f"{kolom}:Q",
                tooltip=[alt.Tooltip("Datum:T"), alt.Tooltip(f"{kolom}:Q", title=f"{titel} ({eenheid})")]
            ).properties(title=f"{titel} per dag ({eenheid})")
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(f"📭 Geen data beschikbaar voor: {titel}")

plot_element("Temperature", "orange", "Temperatuur", "°C")
plot_element("RH", "blue", "Relatieve vochtigheid", "%")
plot_element("Total Cloud Coverage", "lightblue", "Bewolking", "oktas", chart_type="bar")
plot_element("Pressure", "green", "Luchtdruk", "hPa")
plot_element("Wind Velocity", "gray", "Windsnelheid", "knopen")
plot_element("Wind direction", "purple", "Windrichting", "°")

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

# 📌 Samenvatting
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

# 📄 PDF-export
fig_paths = {}

def save_plot(fig, name):
    path = f"{station}_{name}.png"
    fig.savefig(path)
    plt.close(fig)
    fig_paths[name] = path

grafieken = {
    "temp": ("Temperature", "orange", "Temperatuur per dag"),
    "rh": ("RH", "blue", "Relatieve vochtigheid per dag"),
    "pressure": ("Pressure", "green", "Luchtdruk per dag"),
    "wind": ("Wind Velocity", "gray", "Windsnelheid per dag"),
    "dir": ("Wind direction", "purple", "Windrichting per dag"),
    "cloud": ("Total Cloud Coverage", "lightblue", "Bewolking per dag")
}

for key, (kolom, kleur, titel) in grafieken.items():
    if kolom in filtered.columns and not filtered[kolom].dropna().empty:
        fig, ax = plt.subplots()
        if key == "cloud":
            ax.bar(filtered["Datum"], filtered[kolom], color=kleur)
        else:
            ax.plot(filtered["Datum"], filtered[kolom], color=kleur)
        ax.set_title(titel)
        save_plot(fig, key)

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

pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Klimaatrapport – {station}")
c.drawString(2*cm, 27.3*cm, f"Periode: {start_date} tot {end_date}")

# 📌 Samenvatting
y = 26.6 * cm
for label, kolom in [
    ("Gem. temperatuur (°C)", "Temperature"),
    ("Gem. relatieve vochtigheid (%)", "RH"),
    ("Gem. windsnelheid (knopen)", "Wind Velocity"),
    ("Gem. luchtdruk (hPa)", "Pressure"),
    ("Gem. bewolking (oktas)", "Total Cloud Coverage")
]:
    if kolom in filtered.columns:
        value = filtered[kolom].mean()
        if pd.notna(value):
            c.drawString(2 * cm, y, f"{label}: {value:.1f}")
            y -= 0.6 * cm

# 📊 Voeg grafieken toe aan PDF
grafiek_volgorde = ["temp", "rh", "pressure", "wind", "dir", "cloud", "roos"]
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
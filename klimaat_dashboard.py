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
weergave = st.sidebar.radio("Weergave", ["Binnen één dag", "Dagelijkse samenvatting"])

# 📅 Filtering
filtered = pd.DataFrame()
if weergave == "Binnen één dag":
    beschikbare_datums = df[df["StationID"] == station]["Datum"].dt.date.unique()
    datum_keuze = st.sidebar.selectbox("Kies een dag", beschikbare_datums)
    filtered = df[
        (df["StationID"] == station) &
        (df["Datum"].dt.date == datum_keuze)
    ]
    st.title("🌦️ Klimaat per station – verloop binnen één dag")
    st.markdown(f"**Station:** {station}  \n**Datum:** {datum_keuze}")
else:
    min_datum = df[df["StationID"] == station]["Datum"].dt.date.min()
    max_datum = df[df["StationID"] == station]["Datum"].dt.date.max()
    datum_range = st.sidebar.date_input("Kies een datumbereik", [min_datum, max_datum])
    if isinstance(datum_range, list) and len(datum_range) == 2:
        start_date, end_date = datum_range
        filtered = df[
            (df["StationID"] == station) &
            (df["Datum"].dt.date >= pd.to_datetime(start_date).date()) &
            (df["Datum"].dt.date <= pd.to_datetime(end_date).date())
        ]
        st.title("🌦️ Klimaat per station – dagelijkse samenvatting")
        st.markdown(f"**Station:** {station}  \n**Periode:** {start_date} tot {end_date}")

# 🧪 Fallback
if filtered.empty:
    st.warning("📭 Geen gegevens voor deze selectie. Controleer station en datum.")
    st.stop()

# 📊 Visualisatie
def plot_element(kolom, kleur, titel, eenheid, chart_type="line", samenvatting=False):
    if kolom in filtered.columns and not filtered[kolom].dropna().empty:
        data = filtered.dropna(subset=[kolom])
        if samenvatting:
            data = data.copy()
            data["Dag"] = data["Datum"].dt.date
            data = data.groupby("Dag")[kolom].mean().reset_index()
            x_col = "Dag:T"
        else:
            x_col = "Datum:T"
        chart = alt.Chart(data).mark_line(color=kleur).encode(
            x=x_col,
            y=f"{kolom}:Q",
            tooltip=[alt.Tooltip(x_col), alt.Tooltip(f"{kolom}:Q", title=f"{titel} ({eenheid})")]
        ).properties(title=f"{titel} ({eenheid})")
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(f"📭 Geen data beschikbaar voor: {titel}")

plot_element("Temperature", "orange", "Temperatuur", "°C", samenvatting=(weergave == "Dagelijkse samenvatting"))
plot_element("RH", "blue", "Relatieve vochtigheid", "%", samenvatting=(weergave == "Dagelijkse samenvatting"))
plot_element("Total Cloud Coverage", "lightblue", "Bewolking", "oktas", samenvatting=(weergave == "Dagelijkse samenvatting"))
plot_element("Pressure", "green", "Luchtdruk", "hPa", samenvatting=(weergave == "Dagelijkse samenvatting"))
plot_element("Wind Velocity", "gray", "Windsnelheid", "knopen", samenvatting=(weergave == "Dagelijkse samenvatting"))
plot_element("Wind direction", "purple", "Windrichting", "°", samenvatting=(weergave == "Dagelijkse samenvatting"))

# 📌 Samenvatting
st.subheader("📌 Samenvatting")
col1, col2, col3 = st.columns(3)
col1.metric("Gem. temperatuur (°C)", f"{filtered['Temperature'].mean():.1f}" if "Temperature" in filtered.columns else "—")
col2.metric("Gem. relatieve vocht (%)", f"{filtered['RH'].mean():.1f}" if "RH" in filtered.columns else "—")
col3.metric("Gem. windsnelheid (knopen)", f"{filtered['Wind Velocity'].mean():.1f}" if "Wind Velocity" in filtered.columns else "—")

# 📥 Download als CSV
csv_name = f"{station}_{datum_keuze if weergave=='Binnen één dag' else start_date}_klimaatdata.csv"
st.download_button(
    label="📥 Download als CSV",
    data=filtered.to_csv(index=False).encode('utf-8'),
    file_name=csv_name,
    mime="text/csv"
)
# 📤 Grafieken exporteren
fig_paths = {}
def save_plot(fig, name):
    path = f"{station}_{name}.png"
    fig.savefig(path)
    plt.close(fig)
    fig_paths[name] = path

grafieken = {
    "temp": ("Temperature", "orange", "Temperatuur"),
    "rh": ("RH", "blue", "Relatieve vochtigheid"),
    "pressure": ("Pressure", "green", "Luchtdruk"),
    "wind": ("Wind Velocity", "gray", "Windsnelheid"),
    "dir": ("Wind direction", "purple", "Windrichting"),
    "cloud": ("Total Cloud Coverage", "lightblue", "Bewolking")
}

for key, (kolom, kleur, titel) in grafieken.items():
    if kolom in filtered.columns and not filtered[kolom].dropna().empty:
        fig, ax = plt.subplots()
        if weergave == "Dagelijkse samenvatting":
            data = filtered.copy()
            data["Dag"] = data["Datum"].dt.date
            daggemiddeld = data.groupby("Dag")[kolom].mean()
            ax.plot(daggemiddeld.index, daggemiddeld.values, color=kleur)
        else:
            ax.plot(filtered["Datum"], filtered[kolom], color=kleur)
        ax.set_title(f"{titel} – {'samenvatting' if weergave == 'Dagelijkse samenvatting' else 'verloop binnen dag'}")
        save_plot(fig, key)

# 🧭 Windroos exporteren
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

# 📄 PDF-generatie
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Klimaatrapport – {station}")

if weergave == "Binnen één dag":
    c.drawString(2*cm, 27.3*cm, f"Datum: {datum_keuze}")
else:
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
pdf_name = f"{station}_{datum_keuze if weergave=='Binnen één dag' else start_date}_klimaatrapport.pdf"
st.download_button(
    label="📄 Download visueel rapport (PDF)",
    data=pdf_buffer.getvalue(),
    file_name=pdf_name,
    mime="application/pdf"
)
import streamlit as st
import pandas as pd
import altair as alt
import io
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# 📥 Stap 1: Laad het Excel-bestand
df = pd.read_excel("data/Klimaatdata.xlsx")

# 🧼 Stap 2: Zet '00z', '01z', … om naar 'HH:MM'
df["TijdUTC"] = df["Time"].astype(str).str.replace("z", "", regex=False).str.zfill(2) + ":00"

# 🧼 Stap 3: Bouw veilige datetime-kolom
df["Datum"] = pd.to_datetime(
    df["Year"].astype(str) + "-" +
    df["Month"].astype(str).str.zfill(2) + "-" +
    df["Day"].astype(str).str.zfill(2) + " " +
    df["TijdUTC"],
    errors="coerce"
)

# 🧼 Stap 4: Verwijder ongeldige datums
df = df.dropna(subset=["Datum"])

# 🎛️ Stap 5: Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", df["StationID"].unique())
datum_range = st.sidebar.date_input("Selecteer een datumbereik", [df["Datum"].min().date(), df["Datum"].max().date()])

# 🧮 Stap 6: Filter de data op datum
if isinstance(datum_range, tuple) and len(datum_range) == 2:
    filtered = df[
        (df["StationID"] == station) &
        (df["Datum"].dt.date >= datum_range[0]) &
        (df["Datum"].dt.date <= datum_range[1])
    ]
else:
    st.warning("⚠️ Selecteer een geldig datumbereik met twee datums.")
    filtered = pd.DataFrame()

# 🧼 Stap 7: Forceer numeriek datatype
for kolom in [
    "DryBulb T.", "RH", "Total Cloud Coverage",
    "Wind direction", "Wind Velocity", "Pressure"
]:
    filtered[kolom] = pd.to_numeric(filtered[kolom], errors="coerce")

# 📅 Laatste datum in dataset
st.markdown(f"📅 Laatste datum in dataset: **{df['Datum'].max().strftime('%d %B %Y %H:%M')} UTC**")

# 🧾 Titel en metadata
st.title("🌦️ Klimaat per station – testversie")
if not filtered.empty:
    st.markdown(f"**Station:** {station}  \n**Periode:** {datum_range[0]} tot {datum_range[1]}")

# 📊 Temperatuurgrafiek
if not filtered["DryBulb T."].dropna().empty:
    temp_chart = alt.Chart(filtered).mark_line().encode(
        x="Datum:T",
        y="DryBulb T.:Q",
        color=alt.value("orange"),
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("DryBulb T.:Q", title="Temperatuur (°C)"),
            alt.Tooltip("RH:Q", title="Rel. vocht (%)"),
            alt.Tooltip("Pressure:Q", title="Druk (hPa)")
        ]
    ).properties(title="Gemiddelde temperatuur per dag (°C)")
    st.altair_chart(temp_chart, use_container_width=True)
else:
    st.info("📭 Geen temperatuurdata beschikbaar voor deze selectie.")

# 💨 Windsnelheid
if not filtered["Wind Velocity"].dropna().empty:
    wind_chart = alt.Chart(filtered).mark_line(color="gray").encode(
        x="Datum:T",
        y="Wind Velocity:Q",
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("Wind Velocity:Q", title="Windsnelheid (knopen)"),
            alt.Tooltip("Wind direction:Q", title="Windrichting (°)")
        ]
    ).properties(title="Windsnelheid per dag (knopen)")
    st.altair_chart(wind_chart, use_container_width=True)
else:
    st.info("📭 Geen windsnelheidsdata beschikbaar voor deze selectie.")

# ☁️ Bewolking
if not filtered["Total Cloud Coverage"].dropna().empty:
    cloud_chart = alt.Chart(filtered).mark_bar(color="lightblue").encode(
        x="Datum:T",
        y="Total Cloud Coverage:Q",
        tooltip=[
            alt.Tooltip("Datum:T", title="Datum & Tijd"),
            alt.Tooltip("Total Cloud Coverage:Q", title="Bewolking (oktas)")
        ]
    ).properties(title="Totale bewolking per dag (oktas)")
    st.altair_chart(cloud_chart, use_container_width=True)
else:
    st.info("📭 Geen bewolkingsdata beschikbaar voor deze selectie.")

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

    # 📤 Genereer grafiekafbeeldingen
    fig_paths = {}

    if not filtered["DryBulb T."].dropna().empty:
        fig1, ax1 = plt.subplots()
        ax1.plot(filtered["Datum"], filtered["DryBulb T."], label="Gem. temperatuur (°C)", color="orange")
        ax1.set_title("Temperatuur per dag")
        ax1.legend()
        fig_paths["temp"] = f"{station}_temp.png"
        fig1.savefig(fig_paths["temp"])
        plt.close(fig1)

    if not filtered["Wind Velocity"].dropna().empty:
        fig2, ax2 = plt.subplots()
        ax2.plot(filtered["Datum"], filtered["Wind Velocity"], label="Windsnelheid (knopen)", color="gray")
        ax2.set_title("Windsnelheid per dag")
        ax2.legend()
        fig_paths["wind"] = f"{station}_wind.png"
        fig2.savefig(fig_paths["wind"])
        plt.close(fig2)

    if not filtered["Total Cloud Coverage"].dropna().empty:
        fig3, ax3 = plt.subplots()
        ax3.bar(filtered["Datum"], filtered["Total Cloud Coverage"], color="lightblue")
        ax3.set_title("Bewolking per dag")
        fig_paths["cloud"] = f"{station}_cloud.png"
        fig3.savefig(fig_paths["cloud"])
        plt.close(fig3)

        # 📄 Genereer PDF-rapport
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(2*cm, 28*cm, f"📄 Klimaatrapport – {station}")
    c.drawString(2*cm, 27.3*cm, f"Periode: {datum_range[0]} tot {datum_range[1]}")

    if not filtered["DryBulb T."].dropna().empty:
        c.drawString(2*cm, 26.6*cm, f"Gem. temperatuur: {filtered['DryBulb T.'].mean():.1f} °C")
    if not filtered["RH"].dropna().empty:
        c.drawString(2*cm, 26*cm, f"Gem. relatieve vochtigheid: {filtered['RH'].mean():.1f} %")
    if not filtered["Wind Velocity"].dropna().empty:
        c.drawString(2*cm, 25.3*cm, f"Gem. windsnelheid: {filtered['Wind Velocity'].mean():.1f} knopen")
    if not filtered["Pressure"].dropna().empty:
        c.drawString(2*cm, 24.6*cm, f"Gem. luchtdruk: {filtered['Pressure'].mean():.1f} hPa")
    if not filtered["Total Cloud Coverage"].dropna().empty:
        c.drawString(2*cm, 24*cm, f"Gem. bewolking: {filtered['Total Cloud Coverage'].mean():.1f} oktas")

    if "temp" in fig_paths:
        c.drawImage(fig_paths["temp"], 2*cm, 17*cm, width=16*cm, height=8*cm)
    if "wind" in fig_paths:
        c.drawImage(fig_paths["wind"], 2*cm, 8.5*cm, width=16*cm, height=8*cm)
    if "cloud" in fig_paths:
        c.drawImage(fig_paths["cloud"], 2*cm, 0.5*cm, width=16*cm, height=8*cm)

    c.showPage()
    c.save()

    # 📥 Downloadknop voor PDF
    st.download_button(
        label="📄 Download visueel rapport (PDF)",
        data=pdf_buffer.getvalue(),
        file_name=f"{station}_klimaatrapport.pdf",
        mime="application/pdf"
    )
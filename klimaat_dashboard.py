import streamlit as st
import pandas as pd
import altair as alt
import io
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# 📥 Stap 1: Laad het Excel-bestand
df = pd.read_excel("data/Klimaatdata_Jan_Sep_2025.xlsx")

# 🧼 Stap 2: Zet 'Date' om naar datetime
df["Date"] = pd.to_datetime(df["Date"])

# 🎛️ Stap 3: Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", df["Name"].unique())
datum_range = st.sidebar.date_input("Selecteer een datumbereik", [df["Date"].min(), df["Date"].max()])

# 🧮 Stap 4: Filter de data
if isinstance(datum_range, tuple) and len(datum_range) == 2:
    filtered = df[
        (df["Name"] == station) &
        (df["Date"] >= pd.to_datetime(datum_range[0])) &
        (df["Date"] <= pd.to_datetime(datum_range[1]))
    ]
else:
    st.warning("⚠️ Selecteer een geldig datumbereik met twee datums.")
    filtered = pd.DataFrame()

# 🧾 Stap 5: Titel en metadata
st.title("🌦️ Klimaat per station – testversie")
if not filtered.empty:
    st.markdown(f"**Station:** {station}  \n**Periode:** {datum_range[0]} tot {datum_range[1]}")

# 📊 Stap 6: Temperatuurgrafiek
if not filtered.empty:
    temp_chart = alt.Chart(filtered).mark_line().encode(
        x="Date:T",
        y="AVG_Temp:Q",
        color=alt.value("orange"),
        tooltip=["Date", "AVG_Temp", "Max_TemP", "Min_Temp"]
    ).properties(title="Gemiddelde temperatuur per dag")
    st.altair_chart(temp_chart, use_container_width=True)

    # 🌧️ Stap 7: Neerslaggrafiek
    rain_chart = alt.Chart(filtered).mark_bar(color="skyblue").encode(
        x="Date:T",
        y="Rainfall:Q",
        tooltip=["Date", "Rainfall"]
    ).properties(title="Neerslag per dag")
    st.altair_chart(rain_chart, use_container_width=True)

    # 💨 Stap 8: Windsnelheid
    wind_chart = alt.Chart(filtered).mark_line(color="gray").encode(
        x="Date:T",
        y="Wind_Snelheid:Q",
        tooltip=["Date", "Wind_Snelheid", "Wind_Richting"]
    ).properties(title="Windsnelheid per dag")
    st.altair_chart(wind_chart, use_container_width=True)

    # 📌 Stap 9: Samenvattende indicatoren
    st.subheader("📌 Samenvatting")
    col1, col2, col3 = st.columns(3)
    col1.metric("Gem. temperatuur", f"{filtered['AVG_Temp'].mean():.1f} °C")
    col2.metric("Totale neerslag", f"{filtered['Rainfall'].sum():.1f} mm")
    col3.metric("Gem. windsnelheid", f"{filtered['Wind_Snelheid'].mean():.1f} km/h")

else:
    st.warning("⚠️ Er zijn geen gegevens beschikbaar voor deze selectie.")

# 📥 Stap 11: Download als CSV
if not filtered.empty:
    st.download_button(
        label="📥 Download als CSV",
        data=filtered.to_csv(index=False).encode('utf-8'),
        file_name=f"{station}_klimaatdata.csv",
        mime="text/csv"
    )

    # 📥 Stap 12: Download als Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        filtered.to_excel(writer, index=False, sheet_name='Klimaat')

    st.download_button(
        label="📥 Download als Excel",
        data=buffer.getvalue(),
        file_name=f"{station}_klimaatdata.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # 📤 Stap 13: Genereer grafiekafbeeldingen
    fig1, ax1 = plt.subplots()
    ax1.plot(filtered["Date"], filtered["AVG_Temp"], label="Gem. temperatuur", color="orange")
    ax1.plot(filtered["Date"], filtered["Max_TemP"], label="Max temperatuur", color="red")
    ax1.plot(filtered["Date"], filtered["Min_Temp"], label="Min temperatuur", color="blue")
    ax1.set_title("Temperatuur per dag")
    ax1.legend()
    temp_path = f"{station}_temp.png"
    fig1.savefig(temp_path)
    plt.close(fig1)

    fig2, ax2 = plt.subplots()
    ax2.bar(filtered["Date"], filtered["Rainfall"], color="skyblue")
    ax2.set_title("Neerslag per dag")
    rain_path = f"{station}_rain.png"
    fig2.savefig(rain_path)
    plt.close(fig2)

    fig3, ax3 = plt.subplots()
    ax3.plot(filtered["Date"], filtered["Wind_Snelheid"], color="gray")
    ax3.set_title("Windsnelheid per dag")
    wind_path = f"{station}_wind.png"
    fig3.savefig(wind_path)
    plt.close(fig3)

    # 📄 Stap 14: Genereer PDF-rapport
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(2*cm, 28*cm, f"📄 Klimaatrapport – {station}")
    c.drawString(2*cm, 27.3*cm, f"Periode: {datum_range[0]} tot {datum_range[1]}")
    c.drawString(2*cm, 26.6*cm, f"Gem. temperatuur: {filtered['AVG_Temp'].mean():.1f} °C")
    c.drawString(2*cm, 26*cm, f"Totale neerslag: {filtered['Rainfall'].sum():.1f} mm")
    c.drawString(2*cm, 25.3*cm, f"Gem. windsnelheid: {filtered['Wind_Snelheid'].mean():.1f} km/h")

    c.drawImage(temp_path, 2*cm, 17*cm, width=16*cm, height=8*cm)
    c.drawImage(rain_path, 2*cm, 8.5*cm, width=16*cm, height=8*cm)
    c.drawImage(wind_path, 2*cm, 0.5*cm, width=16*cm, height=8*cm)

    c.showPage()
    c.save()

    # 📥 Stap 15: Downloadknop voor PDF
    st.download_button(
        label="📄 Download visueel rapport (PDF)",
        data=pdf_buffer.getvalue(),
        file_name=f"{station}_klimaatrapport.pdf",
        mime="application/pdf"
    )
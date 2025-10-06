import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

st.set_page_config(page_title="📈 AWS Temperatuur – Suriname", layout="wide")

# 📥 Data inladen
df = pd.read_excel("data/awsdata.xlsx")

# 🧼 Kolommen opschonen
df["StationID"] = df["StationID"].fillna("").astype(str).str.strip()
df["Temperature"] = pd.to_numeric(df["Temperature"], errors="coerce")
df["Dag"] = pd.to_numeric(df["Dag"], errors="coerce")
df["Tijd"] = pd.to_datetime(df["Tijd"], format="%H:%M:%S", errors="coerce").dt.time

# 🕒 Tijdopbouw
df["Datum"] = pd.to_datetime(
    "2025-10-" + df["Dag"].astype(int).astype(str).str.zfill(2) + " " + df["Tijd"].astype(str),
    errors="coerce"
)

df = df.dropna(subset=["Datum", "Temperature"])

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", sorted(df["StationID"].unique()))
beschikbare_datums = sorted(df[df["StationID"] == station]["Datum"].dt.date.unique())
datum_keuze = st.sidebar.selectbox("Kies een dag", beschikbare_datums)

# 📅 Filtering
filtered = df[
    (df["StationID"] == station) &
    (df["Datum"].dt.date == datum_keuze)
]

st.title("🌡️ Temperatuurverloop – AWS")
st.markdown(f"**Station:** {station}  \n**Datum:** {datum_keuze}")

if filtered.empty:
    st.warning("📭 Geen temperatuurgegevens voor deze selectie.")
    st.stop()

# 📊 Visualisatie
chart = alt.Chart(filtered).mark_line(color="orange").encode(
    x="Datum:T",
    y="Temperature:Q",
    tooltip=[alt.Tooltip("Datum:T"), alt.Tooltip("Temperature:Q", title="Temperatuur (°C)")]
).properties(title="Temperatuur binnen dag (°C)")

st.altair_chart(chart, use_container_width=True)

# 📤 Matplotlib-grafiek voor PDF
fig, ax = plt.subplots()
ax.plot(filtered["Datum"], filtered["Temperature"], color="orange")
ax.set_title("Temperatuurverloop – AWS")
ax.set_xlabel("Tijd")
ax.set_ylabel("Temperatuur (°C)")
fig.tight_layout()

# 📄 PDF-generatie
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Temperatuurrapport – {station}")
c.drawString(2*cm, 27.3*cm, f"Datum: {datum_keuze}")

# 📤 Voeg grafiek toe
img_buffer = io.BytesIO()
fig.savefig(img_buffer, format="png")
img_buffer.seek(0)
c.drawImage(img_buffer, 2*cm, 12*cm, width=16*cm, height=12*cm)

c.showPage()
c.save()

# 📥 Downloadknop
pdf_name = f"{station}_{datum_keuze}_temperatuur_AWS.pdf"
st.download_button(
    label="📄 Download temperatuurgrafiek (PDF)",
    data=pdf_buffer.getvalue(),
    file_name=pdf_name,
    mime="application/pdf"
)
import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import io
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="📈 AWS Temperatuur – Suriname", layout="wide")

# 📥 Data inladen
df = pd.read_excel("data/awsdata.xlsx")

# 🧼 Kolommen opschonen
df["StationID"] = df["StationID"].fillna("").astype(str).str.strip()

# 🕒 Datumconstructie
df["Datum"] = pd.to_datetime(df[["Year", "Month", "Day"]], errors="coerce")

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", sorted(df["StationID"].unique()))
beschikbare_datums = sorted(df[df["StationID"] == station]["Datum"].dt.date.unique())
datum_keuze = st.sidebar.selectbox("Kies een dag", beschikbare_datums)

temp_type = st.sidebar.radio("Temperatuurtype", ["AVG_Temperature", "Max_Temperature", "Min_Temperature"])

# 📅 Filtering
filtered = df[
    (df["StationID"] == station) &
    (df["Datum"].dt.date == datum_keuze)
]

st.title("🌡️ Temperatuurverloop – AWS")
st.markdown(f"**Station:** {station}  \n**Datum:** {datum_keuze}  \n**Type:** {temp_type}")

if filtered.empty:
    st.warning("📭 Geen temperatuurgegevens voor deze selectie.")
    st.stop()

# 📊 Visualisatie
chart = alt.Chart(filtered).mark_line(color="orange").encode(
    x="Datum:T",
    y=f"{temp_type}:Q",
    tooltip=[alt.Tooltip("Datum:T"), alt.Tooltip(f"{temp_type}:Q", title="Temperatuur (°C)")]
).properties(title=f"{temp_type} binnen dag (°C)")

st.altair_chart(chart, use_container_width=True)

# 📤 Matplotlib-grafiek voor PDF
fig, ax = plt.subplots()
ax.plot(filtered["Datum"], filtered[temp_type], color="orange")
ax.set_title(f"{temp_type} – AWS")
ax.set_xlabel("Tijd")
ax.set_ylabel("Temperatuur (°C)")
fig.tight_layout()

# 📄 PDF-generatie
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Temperatuurrapport – {station}")
c.drawString(2*cm, 27.3*cm, f"Datum: {datum_keuze}")
c.drawString(2*cm, 26.6*cm, f"Type: {temp_type}")

# ✅ Correcte image rendering via PIL
img_buffer = io.BytesIO()
fig.savefig(img_buffer, format="png")
img_buffer.seek(0)
image = Image.open(img_buffer)
image_reader = ImageReader(image)
c.drawImage(image_reader, 2*cm, 12*cm, width=16*cm, height=12*cm)

# 📊 Samenvatting toevoegen
avg_val = filtered[temp_type].mean()
max_val = filtered[temp_type].max()
min_val = filtered[temp_type].min()
c.drawString(2*cm, 10*cm, f"Gemiddelde: {avg_val:.2f} °C")
c.drawString(2*cm, 9.5*cm, f"Maximum: {max_val:.2f} °C")
c.drawString(2*cm, 9.0*cm, f"Minimum: {min_val:.2f} °C")

c.showPage()
c.save()

# 📥 Downloadknop
pdf_name = f"{station}_{datum_keuze}_{temp_type}_AWS.pdf"
st.download_button(
    label="📄 Download temperatuurrapport (PDF)",
    data=pdf_buffer.getvalue(),
    file_name=pdf_name,
    mime="application/pdf"
)

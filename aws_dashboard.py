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

st.set_page_config(page_title="📆 Maandgemiddelden – AWS Suriname", layout="wide")

# 📥 Data inladen
df = pd.read_excel("data/awsdata.xlsx")

# ✅ Kolomcheck – trainer-proof
required_columns = ["StationID", "Year", "Month", "Day", 
                    "AVG_Temperature", "Max_Temperature", "Min_Temperature"]
missing = [col for col in required_columns if col not in df.columns]
if missing:
    st.error(f"❌ Ontbrekende kolommen in dataset: {', '.join(missing)}")
    st.stop()

# 🧼 Opschonen
df["StationID"] = df["StationID"].fillna("").astype(str).str.strip()

# 📅 Datumkolom opbouwen
df["Datum"] = pd.to_datetime(df[["Year", "Month", "Day"]], errors="coerce")

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", sorted(df["StationID"].unique()))
temp_type = st.sidebar.radio("Temperatuurtype", ["AVG_Temperature", "Max_Temperature", "Min_Temperature"])

# 📊 Maandgemiddelden berekenen
monthly = (
    df[df["StationID"] == station]
    .groupby(["Year", "Month"])
    .agg({
        "AVG_Temperature": "mean",
        "Max_Temperature": "mean",
        "Min_Temperature": "mean"
    })
    .reset_index()
)

monthly["Datum"] = pd.to_datetime(monthly[["Year", "Month"]].assign(Day=1))

# 📈 Visualisatie
st.title("📆 Maandgemiddelden – AWS")
st.markdown(f"**Station:** {station}  \n**Type:** {temp_type}")

if monthly.empty:
    st.warning("📭 Geen gegevens beschikbaar voor deze selectie.")
    st.stop()

chart = alt.Chart(monthly).mark_line(color="green").encode(
    x="Datum:T",
    y=f"{temp_type}:Q",
    tooltip=[alt.Tooltip("Datum:T"), alt.Tooltip(f"{temp_type}:Q", title="Gemiddelde (°C)")]
).properties(title=f"Maandgemiddelde – {temp_type}")

st.altair_chart(chart, use_container_width=True)

# 📤 Matplotlib-grafiek voor PDF
fig, ax = plt.subplots()
ax.plot(monthly["Datum"], monthly[temp_type], color="green", marker="o")
ax.set_title(f"Maandgemiddelde – {temp_type}")
ax.set_xlabel("Maand")
ax.set_ylabel("Temperatuur (°C)")
fig.tight_layout()

# 📄 PDF-generatie
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Maandrapport – {station}")
c.drawString(2*cm, 27.3*cm, f"Type: {temp_type}")

# ✅ Grafiek renderen
img_buffer = io.BytesIO()
fig.savefig(img_buffer, format="png")
img_buffer.seek(0)
image = Image.open(img_buffer)
image_reader = ImageReader(image)
c.drawImage(image_reader, 2*cm, 12*cm, width=16*cm, height=12*cm)

# 📊 Samenvattingstabel
c.drawString(2*cm, 10*cm, "📊 Maandgemiddelden:")
for i, row in monthly.iterrows():
    y_pos = 9.5*cm - i*0.4*cm
    if y_pos < 2*cm:
        break  # voorkom overflow
    maand_str = row["Datum"].strftime("%Y-%m")
    waarde = f"{row[temp_type]:.2f} °C"
    c.drawString(2*cm, y_pos, f"{maand_str}: {waarde}")

c.showPage()
c.save()

# 📥 Downloadknop
pdf_name = f"{station}_maandgemiddelde_{temp_type}_AWS.pdf"
st.download_button(
    label="📄 Download maandrapport (PDF)",
    data=pdf_buffer.getvalue(),
    file_name=pdf_name,
    mime="application/pdf"
)

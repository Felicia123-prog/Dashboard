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

st.set_page_config(page_title="📆 Dagelijks Temperatuurverloop – AWS Suriname", layout="wide")

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
df["Day"] = pd.to_numeric(df["Day"], errors="coerce")
df = df.dropna(subset=["Day"])
df["Datum"] = pd.to_datetime(df[["Year", "Month", "Day"]], errors="coerce")

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", sorted(df["StationID"].unique()))
jaar_opties = sorted(df[df["StationID"] == station]["Year"].unique())
gekozen_jaar = st.sidebar.selectbox("Kies een jaar", jaar_opties)
maand_opties = sorted(df[(df["StationID"] == station) & (df["Year"] == gekozen_jaar)]["Month"].unique())
gekozen_maand = st.sidebar.selectbox("Kies een maand", maand_opties)
temp_type = st.sidebar.radio("Temperatuurtype", ["AVG_Temperature", "Max_Temperature", "Min_Temperature"])

# 📅 Filtering: alle dagen binnen gekozen maand
maand_df = df[
    (df["StationID"] == station) &
    (df["Year"] == gekozen_jaar) &
    (df["Month"] == gekozen_maand)
]

if maand_df.empty:
    st.warning("📭 Geen gegevens beschikbaar voor deze maand.")
    st.stop()

# 📊 Dagelijks gemiddelde berekenen
dagelijks = (
    maand_df.groupby(["Year", "Month", "Day"])
    .agg({
        "AVG_Temperature": "mean",
        "Max_Temperature": "mean",
        "Min_Temperature": "mean"
    })
    .reset_index()
)
dagelijks["Datum"] = pd.to_datetime(dagelijks[["Year", "Month", "Day"]], errors="coerce")

# 📅 Volledige daglijst (1–31)
daglijst = pd.DataFrame({"Day": range(1, 32)})
daglijst["Year"] = gekozen_jaar
daglijst["Month"] = gekozen_maand
daglijst["Datum"] = pd.to_datetime(daglijst[["Year", "Month", "Day"]], errors="coerce")

# 🔗 Merge met volledige daglijst
volledig = pd.merge(daglijst, dagelijks, on=["Year", "Month", "Day", "Datum"], how="left")

# 🧪 Check of temperatuurkolom bestaat en gevuld is
if temp_type not in volledig.columns:
    st.error(f"❌ Kolom '{temp_type}' bestaat niet in de data.")
    st.stop()

if volledig[temp_type].isna().all():
    st.warning("📭 Geen temperatuurwaarden beschikbaar voor deze maand.")
    st.stop()

# 📈 Visualisatie met dagnummers
st.title("📆 Dagelijks Temperatuurverloop – AWS")
st.markdown(f"**Station:** {station}  \n**Periode:** {gekozen_jaar}-{str(gekozen_maand).zfill(2)}  \n**Type:** {temp_type}")

chart = alt.Chart(volledig).mark_line(color="orange").encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y(f"{temp_type}:Q", title="Temperatuur (°C)"),
    tooltip=[alt.Tooltip("Day:O", title="Dag"), alt.Tooltip(f"{temp_type}:Q", title="Temperatuur (°C)")]
).properties(title=f"Dagelijks verloop – {temp_type}")

st.altair_chart(chart, use_container_width=True)

# 📤 Matplotlib-grafiek voor PDF
fig, ax = plt.subplots()
ax.plot(volledig["Day"], volledig[temp_type], color="orange", marker="o")
ax.set_title(f"Dagelijks verloop – {temp_type}")
ax.set_xlabel("Dag van de maand")
ax.set_ylabel("Temperatuur (°C)")
fig.tight_layout()

# 📄 PDF-generatie
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Temperatuurrapport – {station}")
c.drawString(2*cm, 27.3*cm, f"Periode: {gekozen_jaar}-{str(gekozen_maand).zfill(2)}")
c.drawString(2*cm, 26.6*cm, f"Type: {temp_type}")

# ✅ Grafiek renderen
img_buffer = io.BytesIO()
fig.savefig(img_buffer, format="png")
img_buffer.seek(0)
image = Image.open(img_buffer)
image_reader = ImageReader(image)
c.drawImage(image_reader, 2*cm, 12*cm, width=16*cm, height=12*cm)

# 📊 Samenvattingstabel
c.drawString(2*cm, 10*cm, "📊 Dagwaarden:")
for i, row in volledig.iterrows():
    y_pos = 9.5*cm - i*0.4*cm
    if y_pos < 2*cm:
        break
    dag_str = f"{gekozen_jaar}-{str(gekozen_maand).zfill(2)}-{int(row['Day']):02d}"
    waarde = f"{row[temp_type]:.2f} °C" if pd.notna(row[temp_type]) else "geen data"
    c.drawString(2*cm, y_pos, f"{dag_str}: {waarde}")

c.showPage()
c.save()

# 📥 Downloadknop
pdf_name = f"{station}_{gekozen_jaar}-{str(gekozen_maand).zfill(2)}_{temp_type}_dagverloop_AWS.pdf"
st.download_button(
    label="📄 Download temperatuurverloop (PDF)",
    data=pdf_buffer.getvalue(),
    file_name=pdf_name,
    mime="application/pdf"
)

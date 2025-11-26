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

st.set_page_config(page_title="📊 Dagelijkse Extremen – AWS Suriname", layout="wide")

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
df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
df["Month"] = pd.to_numeric(df["Month"], errors="coerce").astype("Int64")
df["Day"] = pd.to_numeric(df["Day"], errors="coerce").astype("Int64")
df = df.dropna(subset=["Year", "Month", "Day"])

# 🎛️ Sidebarfilters
st.sidebar.title("🔎 Filteropties")
station = st.sidebar.selectbox("Selecteer een station", sorted(df["StationID"].unique()))
jaar_opties = sorted(df[df["StationID"] == station]["Year"].dropna().unique())
gekozen_jaar = st.sidebar.selectbox("Kies een jaar", jaar_opties)
maand_opties = sorted(df[(df["StationID"] == station) & (df["Year"] == gekozen_jaar)]["Month"].dropna().unique())
gekozen_maand = st.sidebar.selectbox("Kies een maand", maand_opties)

# 📅 Filtering
maand_df = df[
    (df["StationID"] == station) &
    (df["Year"] == gekozen_jaar) &
    (df["Month"] == gekozen_maand)
].copy()

if maand_df.empty:
    st.warning("📭 Geen gegevens beschikbaar voor deze selectie.")
    st.stop()

# 📊 Dagelijkse aggregatie
dagelijks = (
    maand_df.groupby(["Year", "Month", "Day"], as_index=False)
    .agg({
        "AVG_Temperature": "mean",
        "Max_Temperature": "mean",
        "Min_Temperature": "mean"
    })
)

# 📅 Volledige daglijst (1–31)
max_days = 31
daglijst = pd.DataFrame({"Day": range(1, max_days + 1)})
daglijst["Year"] = gekozen_jaar
daglijst["Month"] = gekozen_maand

# 🔗 Merge
volledig = pd.merge(daglijst, dagelijks, on=["Year", "Month", "Day"], how="left")

# 📈 Visualisatie: staafdiagram met extremen
st.title("📊 Dagelijkse Extremen – AWS")
st.markdown(f"**Station:** {station}  \n**Periode:** {int(gekozen_jaar)}-{str(int(gekozen_maand)).zfill(2)}")

bars = alt.Chart(volledig).mark_bar(color="skyblue").encode(
    x=alt.X("Day:O", title="Dag van de maand"),
    y=alt.Y("Min_Temperature:Q", title="Temperatuur (°C)"),
    y2="Max_Temperature:Q",
    tooltip=[
        alt.Tooltip("Day:O", title="Dag"),
        alt.Tooltip("Min_Temperature:Q", title="Minimum (°C)"),
        alt.Tooltip("Max_Temperature:Q", title="Maximum (°C)")
    ]
)

avg_points = alt.Chart(volledig).mark_point(color="red").encode(
    x="Day:O",
    y="AVG_Temperature:Q",
    tooltip=[alt.Tooltip("AVG_Temperature:Q", title="Gemiddelde (°C)")]
)

st.altair_chart(bars + avg_points, use_container_width=True)

# 📤 Matplotlib-grafiek voor PDF
fig, ax = plt.subplots()
for _, row in volledig.iterrows():
    if pd.notna(row["Min_Temperature"]) and pd.notna(row["Max_Temperature"]):
        ax.bar(row["Day"], row["Max_Temperature"] - row["Min_Temperature"],
               bottom=row["Min_Temperature"], color="skyblue")
    if pd.notna(row["AVG_Temperature"]):
        ax.plot(row["Day"], row["AVG_Temperature"], "ro")

ax.set_title("Dagelijkse extremen – Min/Max Temperatuur")
ax.set_xlabel("Dag van de maand")
ax.set_ylabel("Temperatuur (°C)")
ax.set_xticks(range(1, max_days + 1))
fig.tight_layout()

# 📄 PDF-generatie
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=A4)
c.setFont("Helvetica", 12)
c.drawString(2*cm, 28*cm, f"📄 Temperatuurrapport – {station}")
c.drawString(2*cm, 27.3*cm, f"Periode: {int(gekozen_jaar)}-{str(int(gekozen_maand)).zfill(2)}")
c.drawString(2*cm, 26.6*cm, "Type: Dagelijkse extremen (Min/Max + Gemiddelde)")

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
    dag_str = f"{int(gekozen_jaar)}-{str(int(gekozen_maand)).zfill(2)}-{int(row['Day']):02d}"
    min_val = f"{row['Min_Temperature']:.2f} °C" if pd.notna(row['Min_Temperature']) else "geen data"
    max_val = f"{row['Max_Temperature']:.2f} °C" if pd.notna(row['Max_Temperature']) else "geen data"
    avg_val = f"{row['AVG_Temperature']:.2f} °C" if pd.notna(row['AVG_Temperature']) else "geen data"
    c.drawString(2*cm, y_pos, f"{dag_str}: min={min_val}, max={max_val}, avg={avg_val}")

c.showPage()
c.save()

# 📥 Downloadknop
pdf_name = f"{station}_{int(gekozen_jaar)}-{str(int(gekozen_maand)).zfill(2)}_extremen_AWS.pdf"
st.download_button(
    label="📄 Download temperatuur-extremen (PDF)",
    data=pdf_buffer.getvalue(),
    file_name=pdf_name,
    mime="application/pdf"
)

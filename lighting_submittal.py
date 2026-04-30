import streamlit as st
import pdfplumber
import pandas as pd
import requests
import os
import shutil
from ddgs import DDGS
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfMerger
from PIL import Image
import io
from datetime import datetime

st.set_page_config(page_title="Lighting Submittal Builder", layout="wide")
st.title("💡 Advanced Lighting Submittal Package Builder")
st.markdown("**Auto PDF Search + Branded Cover + TOC + Private Cache**")

# ====================== DIRECTORIES ======================
CACHE_DIR = "spec_sheets"
os.makedirs(CACHE_DIR, exist_ok=True)

# ====================== SIDEBAR - BRANDING ======================
st.sidebar.header("🏢 Company & Project Info")

logo_file = st.sidebar.file_uploader("Upload Company Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

company_name = st.sidebar.text_input("Company Name", "Your Lighting Company LLC")
project_name = st.sidebar.text_input("Project Name", "Project XYZ - Lighting Package")
prepared_by = st.sidebar.text_input("Prepared By", "Rebecca Linderman")
project_date = st.sidebar.date_input("Date", datetime.today())

# ====================== INPUT PARTS ======================
st.header("1. Add Your Lighting Fixtures")

option = st.radio("Choose input method:", ["Upload Schedule File", "Paste Part Numbers Manually"])

parts = []

if option == "Upload Schedule File":
    uploaded_file = st.file_uploader("Upload Excel, CSV, or PDF schedule", 
                                   type=["xlsx", "xls", "csv", "pdf"])
    
    if uploaded_file:
        if uploaded_file.name.endswith(".pdf"):
            with pdfplumber.open(uploaded_file) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            st.text_area("Preview of extracted text:", text[:600] + "..." if len(text) > 600 else text, height=200)
            
            # Basic lighting part number extraction
            lines = text.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped) > 6 and any(c.isalnum() for c in stripped):
                    parts.append(stripped[:120])
        else:
            # Excel or CSV
            if uploaded_file.name.endswith((".xlsx", ".xls")):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            
            st.write("**Detected Columns:**", list(df.columns))
            part_col = st.selectbox("Select the column containing Part Numbers / Catalog #", df.columns.tolist())
            
            raw_parts = df[part_col].dropna().astype(str).str.strip()
            parts = [p for p in raw_parts if len(p) > 4]

else:  # Paste manually
    manual_input = st.text_area(
        "Paste part numbers (one per line)",
        placeholder="2BLT4 40L ADP EZ1 LP835\nCXB3590-0000-000N0HCB50E\nLED-12345-ABC",
        height=250
    )
    if manual_input:
        parts = [line.strip() for line in manual_input.strip().split("\n") if line.strip()]

# ====================== HELPER FUNCTIONS ======================
def is_part_in_pdf(pdf_path, part_no):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = " ".join([page.extract_text() or "" for page in pdf.pages]).lower()
        return part_no.lower() in text
    except:
        return False

# ====================== MAIN ACTION ======================
if st.button("🚀 Auto-Find Spec Sheets + Generate Branded Package", type="primary") and parts:
    st.success(f"Processing {len(parts)} lighting items...")
    
    downloaded = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    ddgs = DDGS()
    
    for i, part_no in enumerate(parts):
        status_text.text(f"🔍 Working on: {part_no}")
        
        safe_name = part_no.replace("/", "_").replace(" ", "_").replace("\\", "_")[:80]
        cached_file = os.path.join(CACHE_DIR, f"{safe_name}.pdf")
        
        # 1. Check cache
        if os.path.exists(cached_file) and is_part_in_pdf(cached_file, part_no):
            st.success(f"✅ Using cached: {part_no}")
            downloaded.append(cached_file)
            progress_bar.progress((i + 1) / len(parts))
            continue
        
        # 2. Auto search
        query = f'"{part_no}" (lighting OR fixture) (spec sheet OR cut sheet OR datasheet OR "product data" OR photometric) filetype:pdf'
        
        try:
            results = list(ddgs.text(query, max_results=10))
            found_good = False
            
            for result in results:
                url = result.get("href")
                if url and url.lower().endswith(".pdf"):
                    try:
                        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                        if resp.status_code == 200:
                            with open(cached_file, "wb") as f:
                                f.write(resp.content)
                            
                            if is_part_in_pdf(cached_file, part_no):
                                st.success(f"✅ Downloaded & verified: {part_no}")
                                downloaded.append(cached_file)
                                found_good = True
                                break
                            else:
                                os.remove(cached_file)  # false positive
                    except:
                        continue
            if not found_good:
                st.warning(f"⚠️ No verified PDF found for {part_no}")
        except Exception as e:
            st.error(f"Search failed for {part_no}: {e}")
        
        progress_bar.progress((i + 1) / len(parts))

    # ====================== BUILD FINAL PACKAGE ======================
    if downloaded:
        st.success(f"✅ {len(downloaded)} spec sheets ready. Creating branded PDF...")
        
        # Cover Page
        cover_path = "cover_page.pdf"
        c = canvas.Canvas(cover_path, pagesize=letter)
        w, h = letter
        
        # Logo
        if logo_file:
            try:
                img = Image.open(logo_file)
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                c.drawImage(ImageReader(img_bytes), 50, h - 180, width=220, height=120, preserveAspectRatio=True)
            except:
                pass
        
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(w/2, h - 260, company_name.upper())
        
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(w/2, h - 310, project_name)
        
        c.setFont("Helvetica", 16)
        c.drawCentredString(w/2, h - 360, "Lighting Fixture Submittal Package")
        
        c.setFont("Helvetica", 12)
        c.drawCentredString(w/2, h - 400, f"Prepared by: {prepared_by}")
        c.drawCentredString(w/2, h - 425, f"Date: {project_date.strftime('%B %d, %Y')}")
        
        c.save()
        
        # Table of Contents
        toc_path = "toc.pdf"
        c = canvas.Canvas(toc_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, h - 80, "Table of Contents")
        c.line(50, h - 90, w - 50, h - 90)
        
        c.setFont("Helvetica", 12)
        y = h - 130
        for idx, pdf_file in enumerate(downloaded):
            part_name = os.path.basename(pdf_file).replace(".pdf", "").replace("_", " ")
            c.drawString(60, y, f"{idx + 1}. {part_name}")
            c.drawRightString(w - 60, y, str(idx + 3))  # Cover + TOC = page 1+2
            y -= 22
            if y < 80:
                c.showPage()
                y = h - 80
        c.save()
        
        # Merge everything
        final_path = f"{project_name.replace(' ', '_')}_FINAL_Submittal.pdf"
        merger = PdfMerger()
        merger.append(cover_path)
        merger.append(toc_path)
        
        for pdf_path in downloaded:
            merger.append(pdf_path)
        
        merger.write(final_path)
        merger.close()
        
        # Offer download
        with open(final_path, "rb") as f:
            st.download_button(
                label="📥 DOWNLOAD FINAL BRANDED SUBMITTAL PDF",
                data=f,
                file_name=final_path,
                mime="application/pdf",
                type="primary"
            )
        
        st.balloons()
        st.success("🎉 Your professional submittal package is ready!")
        
        st.info(f"All spec sheets are saved privately in the **{CACHE_DIR}** folder for future use.")

else:
    st.info("Upload your schedule or paste part numbers, then click the big button above.")

st.caption("Built for lighting companies • Everything stays private on your machine / private Streamlit app")

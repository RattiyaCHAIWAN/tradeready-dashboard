import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pydantic import BaseModel
from google import genai
from google.genai import types

# ==========================================
# 0. PAGE CONFIGURATION (ต้องวางไว้ตรงนี้เลยครับ เป็นคำสั่งแรกของ Streamlit)
# ==========================================
st.set_page_config(
    page_title="TradeReady AI", 
    layout="wide", # 👈 ตัวนี้แหละครับที่จะทำให้จอขยายกว้างเต็มพื้นที่
    initial_sidebar_state="expanded"
)

# ==========================================
# 0.1 CUSTOM BACKGROUND IMAGE (ส่วนที่เพิ่มใหม่)
# ==========================================
# 🔗 เปลี่ยน URL ตรงนี้เป็นลิงก์รูปภาพที่คุณต้องการ
background_image_url = "https://images.unsplash.com/photo-1578575437130-527eed3abbec?q=80&w=2070&auto=format&fit=crop"

st.markdown(
    f"""
    <style>
    /* ตั้งค่ารูปพื้นหลังให้เต็มจอ .stApp */
    .stApp {{
        background-image: url("{background_image_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* เพิ่มพื้นหลังสีกรมท่าโปร่งใสทับส่วนเนื้อหา เพื่อให้ตัวอักษรยังคงอ่านง่าย */
    .block-container {{
        background-color: rgba(18, 58, 98, 0.65); /* #123A62 ที่มีความโปร่งใส 85% */
        padding-top: 3rem;
        padding-bottom: 3rem;
        padding-left: 3rem;
        padding-right: 3rem;
        border-radius: 15px;
        margin-top: 2rem;
    }}
    
    /* ปรับขนาดฟอนต์ในตาราง (ตามที่คุยกันก่อนหน้า) */
    .stDataFrame {{
        font-size: 16px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 1. SETUP & CONSTANTS
# ==========================================
HISTORY_FILE = "data/history_logs.csv"
DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# ตัวแปรความเข้มงวดและรูปแบบการขนส่ง
STRICTNESS_MULTIPLIER = {"Lenient": 0.5, "Standard": 1.0, "Strict": 1.5}
MODE_MULTIPLIER = {"AIR ✈️": 0.5, "TRUCK 🚛": 1.0, "SEA 🚢": 1.5}

# ==========================================
# 2. DATA GENERATOR (Requirement: 30 Samples)
# ==========================================
def generate_sample_data():
    """สร้างไฟล์ CSV จำลอง 30 รายการ หากยังไม่มีไฟล์ในระบบ"""
    if os.path.exists(HISTORY_FILE):
        return
    
    samples = []
    # จำลองข้อมูลกลุ่ม OEM Electronics และการเกษตร
    scenarios = ["Normal", "Disruption", "Erroneous Data"]
    
    for i in range(1, 31):
        scenario = scenarios[i % 3]
        score = 95 if scenario == "Normal" else (65 if scenario == "Disruption" else 40)
        risk = "LOW 🟢" if score >= 85 else ("MED 🟡" if score >= 50 else "HIGH 🔴")
        delay = 0 if risk == "LOW 🟢" else (12 if risk == "MED 🟡" else 36)
        ai_rec = "Ready to Export" if risk == "LOW 🟢" else ("Requires Review" if risk == "MED 🟡" else "Hold Shipment")
        
        samples.append({
            "running_no": f"TR-202608{i:02d}-0001",
            "timestamp": f"2026-08-{i:02d} 10:30:00",
            "exporter": "Chiang Mai OEM Electronics" if i % 2 == 0 else "Northern Agri Export",
            "destination": "Japan" if i % 2 == 0 else "China",
            "shipment_mode": "AIR ✈️" if i % 3 == 0 else ("SEA 🚢" if i % 3 == 1 else "TRUCK 🚛"),
            "scenario_type": scenario,
            "readiness_score": score,
            "risk_level": risk,
            "est_delay": delay,
            "ai_recommendation": ai_rec,
            "human_status": "🟢 Accepted" if i % 4 != 0 else "🟠 Overridden"
        })
    pd.DataFrame(samples).to_csv(HISTORY_FILE, index=False)

generate_sample_data()

# ==========================================
# 3. PYDANTIC MODEL (AI Output Schema)
# ==========================================
class ExtractedShipment(BaseModel):
    doc_type: str
    shipment_mode: str
    invoice_no: str
    po_no: str
    exporter_name: str
    destination: str
    invoice_qty: int
    packing_qty: int
    total_amount: float
    hs_code: str
    has_coo: bool

# ==========================================
# 4. RULES ENGINE (Scoring Logic)
# ==========================================
def calculate_readiness(data, strictness_label):
    score = 100
    delay = 0
    m_strict = STRICTNESS_MULTIPLIER.get(strictness_label, 1.0)
    m_mode = MODE_MULTIPLIER.get(data['shipment_mode'], 1.0)
    
    issues = []
    # 1. Quantity Mismatch
    if data['invoice_qty'] != data['packing_qty']:
        score -= (25 * m_strict)
        delay += (24 * m_mode)
        issues.append("Quantity Mismatch (Invoice vs Packing)")
        
    # 2. Missing COO
    if not data['has_coo']:
        score -= (20 * m_strict)
        delay += (12 * m_mode)
        issues.append("Missing Certificate of Origin (COO)")

    score = max(0, int(score))
    
    # Evaluate Risk
    if score >= 85 and not issues:
        risk = "LOW 🟢"
        ai_rec = "Ready to Export"
    elif score >= 50:
        risk = "MED 🟡"
        ai_rec = "Requires Review & Correction"
    else:
        risk = "HIGH 🔴"
        ai_rec = "Hold Shipment / High Risk"
        
    return score, risk, int(delay), ai_rec, issues

# ==========================================
# 5. REVIEW MODAL (Human-in-the-Loop)
# ==========================================
@st.dialog("🔍 Review & Verify Extracted Data", width="large")
def review_modal():
    st.info("⚠️ โปรดตรวจสอบและแก้ไขข้อมูลที่ AI สกัดได้ก่อนบันทึกเข้าระบบ Dashboard")
    data = st.session_state.temp_extracted_data
    
    with st.form("verify_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📌 Header & Routing**")
            mode = st.selectbox("Shipment Mode", ["AIR ✈️", "SEA 🚢", "TRUCK 🚛"], 
                                index=["AIR ✈️", "SEA 🚢", "TRUCK 🚛"].index(data['shipment_mode']))
            inv = st.text_input("Invoice No.", data['invoice_no'])
            po = st.text_input("PO No.", data['po_no'])
            exporter = st.text_input("Exporter", data['exporter_name'])
            dest = st.selectbox("Destination", ["Japan", "China", "Vietnam", "USA", "EU"], index=0)
            
        with c2:
            st.markdown("**📊 Quantities & Compliance**")
            inv_qty = st.number_input("Invoice Qty", value=int(data['invoice_qty']))
            pl_qty = st.number_input("Packing List Qty", value=int(data['packing_qty']))
            if inv_qty != pl_qty:
                st.error("⚠️ Quantity Mismatch Detected!")
                
            amount = st.number_input("Total Amount ($)", value=float(data['total_amount']))
            hs = st.text_input("HS Code", data['hs_code'])
            coo = st.checkbox("Has Certificate of Origin (COO)", value=data['has_coo'])

        if st.form_submit_button("🚀 Confirm & Process"):
            # คำนวณคะแนนและบันทึก
            verified_data = {
                "shipment_mode": mode, "invoice_no": inv, "po_no": po, "exporter_name": exporter,
                "destination": dest, "invoice_qty": inv_qty, "packing_qty": pl_qty,
                "total_amount": amount, "hs_code": hs, "has_coo": coo
            }
            
            score, risk, delay, ai_rec, issues = calculate_readiness(verified_data, st.session_state.strictness)
            
            # ออก Running No
            today = datetime.today().strftime('%Y%m%d')
            run_no = f"TR-{today}-{str(len(pd.read_csv(HISTORY_FILE)) + 1).zfill(4)}"
            
            # เซฟลง CSV
            new_record = pd.DataFrame([{
                "running_no": run_no, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "exporter": exporter, "destination": dest, "shipment_mode": mode,
                "scenario_type": "Live Audit", "readiness_score": score, "risk_level": risk,
                "est_delay": delay, "ai_recommendation": ai_rec, "human_status": "⚪ Pending"
            }])
            new_record.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
            
            # เก็บค่าไว้โชว์ Dashboard
            st.session_state.active_audit = new_record.iloc[0].to_dict()
            st.session_state.active_audit['issues'] = issues
            st.session_state.show_modal = False
            st.rerun()

# ==========================================
# 6. MAIN UI & SIDEBAR
# ==========================================

st.markdown(
    """
    <style>
    /* 1. 🧊 ปรับ Sidebar ให้โปร่งแสง และทำเอฟเฟกต์กระจกฝ้า (Frosted Glass) */
    [data-testid="stSidebar"] {
        background-color: rgba(18, 58, 98, 0.65) !important; /* ปรับความโปร่งแสงที่เลข 0.65 (65%) */
        backdrop-filter: blur(8px) !important;              /* เพิ่มความเบลอฉากหลังให้ดูพรีเมียม */
        -webkit-backdrop-filter: blur(8px);
    }
    
    [data-testid="stSidebarContent"] {
        background-color: transparent !important;
    }

    /* 2. ขยายฟอนต์ข้อความทั่วไป */
    html, body, [class*="st-"], .stMarkdown p {
        font-size: 16px !important;
    }
    
    /* ขยายฟอนต์ใน Sidebar */
    [data-testid="stSidebar"] * {
        font-size: 15px !important;
    }
    
    /* ขยายหัวข้อใน Sidebar */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-size: 20px !important;
    }
    
    /* ขยาย Label */
    .stRadio label, .stSelectbox label, .stTextInput label, .stFileUploader label {
        font-size: 16px !important;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🚢 TradeReady AI")
st.caption("Export Documentation & Customs Readiness Assistant")

# --- SIDEBAR ---
with st.sidebar:
  st.header("⚙️ Control Panel")

  # 🔑 2. เพิ่มช่องใส่ Gemini API Key ตรงนี้
  api_key = st.text_input(
      "🔑 Gemini API Key",
      type="password",
      placeholder="AIzaSy...",
      help="กรอก Gemini API Key เพื่อเปิดใช้งาน AI",
  )
  if api_key:
    st.session_state.api_key = api_key

  st.divider()

  app_mode = st.radio(
      "Navigation", ["📄 Audit New Document", "📜 History Logs"]
  )
  st.divider()
  st.markdown("**📂 Document Upload (Multi-File)**")
  uploaded_files = st.file_uploader(
      "Upload Invoice, PL, COO", type=["pdf"], accept_multiple_files=True
  )
  st.divider()

  st.session_state.strictness = st.selectbox(
      "Customs Strictness Level", ["Lenient", "Standard", "Strict"], index=1
  )
  if uploaded_files and st.button("🚀 Release to AI", use_container_width=True):
    # เช็คว่าผู้ใช้กรอก API Key หรือยัง
    if not st.session_state.get("api_key"):
      st.error("⚠️ กรุณากรอก Gemini API Key ด้านบนก่อนเริ่มประมวลผล!")
    else:
      with st.spinner("AI is analyzing documents..."):
        # หมายเหตุ: นำ st.session_state.api_key ไปใช้งานต่อกับ Google GenAI Client ได้ที่นี่
        st.session_state.temp_extracted_data = {
            "doc_type": "Multiple",
            "shipment_mode": "AIR ✈️",
            "invoice_no": "INV-2026-991",
            "po_no": "PO-991",
            "exporter_name": "Chiang Mai OEM Electronics",
            "destination": "Japan",
            "invoice_qty": 500,
            "packing_qty": 450,
            "total_amount": 12500.0,
            "hs_code": "8542.31",
            "has_coo": False,
        }
        st.session_state.show_modal = True

if getattr(st.session_state, "show_modal", False):
  review_modal()
# ==========================================
# 7. MAIN DASHBOARD CONTENT
# ==========================================
if app_mode == "📄 Audit New Document":
    if 'active_audit' in st.session_state:
        audit = st.session_state.active_audit
        st.success(f"✅ ประมวลผลสำเร็จ | Running No: **{audit['running_no']}** | Mode: {audit['shipment_mode']}")
        
        # KPI Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Readiness Score", f"{audit['readiness_score']}/100")
        c2.metric("Completion Rate", "83.3%")
        c3.metric("Risk Level", audit['risk_level'])
        c4.metric("Est. Border Delay", f"{audit['est_delay']} Hours")
        
        st.divider()
        col_left, col_right = st.columns([1.5, 1])
        
        with col_left:
            st.markdown("### 🤖 AI Recommendation")
            st.info(f"**Decision:** {audit['ai_recommendation']}")
            if audit['issues']:
                st.error("**Detected Issues:**\n" + "\n".join([f"- {i}" for i in audit['issues']]))
            else:
                st.success("**Status:** Documents are compliant and ready.")
                
        with col_right:
            st.markdown("### 👤 Human Override")
            st.selectbox("Final Decision", ["Ready to Export", "Requires Review", "Hold Shipment"])
            st.text_area("Remarks / Notes")
            if st.button("💾 Save Final Decision", type="primary"):
                st.success("Decision updated in history log.")
                
    else:
        st.info("👈 กรุณาอัปโหลดไฟล์ PDF ด้านซ้ายมือ หรือปรับโหมดเพื่อดูประวัติย้อนหลัง")

elif app_mode == "📜 History Logs":
    st.subheader("📜 Transaction History Logs")
    
    df = pd.read_csv(HISTORY_FILE)
    
    col1, col2 = st.columns(2)
    search_q = col1.text_input("🔍 Search Exporter or Running No.")
    risk_filter = col2.selectbox("Filter Risk", ["All", "LOW 🟢", "MED 🟡", "HIGH 🔴"])
    
    if search_q:
        df = df[df['exporter'].str.contains(search_q, case=False) | df['running_no'].str.contains(search_q, case=False)]
    if risk_filter != "All":
        df = df[df['risk_level'] == risk_filter]
        
    st.dataframe(
        df[["running_no", "timestamp", "shipment_mode", "exporter", "destination", "readiness_score", "risk_level", "human_status"]],
        use_container_width=True,
        hide_index=True
    )

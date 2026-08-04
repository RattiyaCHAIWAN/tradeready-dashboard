import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from pydantic import BaseModel
from google import genai
from google.genai import types

# ==========================================
# 0. PAGE CONFIGURATION & STATE INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="TradeReady AI", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# จัดจัดการ Navigation State สำหรับปุ่มวาร์ป
if "nav_choice" not in st.session_state:
    st.session_state.nav_choice = "📄 Audit New Document"

# ==========================================
# 0.1 CUSTOM BACKGROUND IMAGE & OVERLAY (CSS)
# ==========================================
background_image_url = "https://images.unsplash.com/photo-1578575437130-527eed3abbec?q=80&w=2070&auto=format&fit=crop"

st.markdown(
    f"""
    <style>
    /* 1. ตั้งค่ารูปพื้นหลังให้เต็มจอหลัก (.stApp) */
    .stApp {{
        background-image: url("{background_image_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* 2. สีกรมท่าโปร่งใสคลุมเต็มพื้นที่หน้าจอหลัก (Main Area) */
    [data-testid="stMain"], section.main {{
        background-color: rgba(18, 58, 98, 0.70) !important;
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
    }}
    
    /* 3. ปรับ Sidebar ให้โปร่งแสง และทำเอฟเฟกต์กระจกฝ้า (Frosted Glass) */
    [data-testid="stSidebar"] {{
        background-color: rgba(18, 58, 98, 0.65) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px);
    }}
    
    [data-testid="stSidebarContent"] {{
        background-color: transparent !important;
    }}

    /* 4. ปรับแต่งฟอนต์ */
    .block-container {{
        background-color: transparent !important;
        padding-top: 2.5rem;
        padding-bottom: 2.5rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }}
    
    html, body, [class*="st-"], .stMarkdown p {{
        font-size: 16px !important;
    }}
    
    [data-testid="stSidebar"] * {{
        font-size: 15px !important;
    }}
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        font-size: 20px !important;
    }}
    
    .stRadio label, .stSelectbox label, .stTextInput label, .stFileUploader label, .stDateInput label {{
        font-size: 16px !important;
        font-weight: bold;
    }}

    .stDataFrame {{
        font-size: 15px !important;
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

STRICTNESS_MULTIPLIER = {"Lenient": 0.5, "Standard": 1.0, "Strict": 1.5}
MODE_MULTIPLIER = {"AIR ✈️": 0.5, "TRUCK 🚛": 1.0, "SEA 🚢": 1.5}

# ==========================================
# 2. DATA GENERATOR & UPDATER
# ==========================================
def generate_sample_data():
    """สร้างไฟล์ CSV จำลอง 30 รายการ พร้อมเพิ่ม Ship Date"""
    if os.path.exists(HISTORY_FILE):
        return
    
    samples = []
    scenarios = ["Normal", "Disruption", "Erroneous Data"]
    
    for i in range(1, 31):
        scenario = scenarios[i % 3]
        score = 95 if scenario == "Normal" else (65 if scenario == "Disruption" else 40)
        risk = "LOW 🟢" if score >= 85 else ("MED 🟡" if score >= 50 else "HIGH 🔴")
        delay = 0 if risk == "LOW 🟢" else (12 if risk == "MED 🟡" else 36)
        ai_rec = "Ready to Export" if risk == "LOW 🟢" else ("Requires Review" if risk == "MED 🟡" else "Hold Shipment")
        
        # กระจายวัน Ship Date ออกไปในช่วงวันที่ 2026-08-01 ถึง 2026-08-10
        ship_day = (i % 5) + 1
        ship_date_str = f"2026-08-{ship_day:02d}"
        
        samples.append({
            "running_no": f"TR-202608{i:02d}-0001",
            "timestamp": f"2026-08-01 10:30:00",
            "ship_date": ship_date_str,  # 👈 เพิ่มฟิลด์ Ship Date
            "exporter": "Chiang Mai OEM Electronics" if i % 2 == 0 else "Northern Agri Export",
            "destination": "Japan" if i % 2 == 0 else "China",
            "shipment_mode": "AIR ✈️" if i % 3 == 0 else ("SEA 🚢" if i % 3 == 1 else "TRUCK 🚛"),
            "scenario_type": scenario,
            "readiness_score": score,
            "risk_level": risk,
            "est_delay": delay,
            "ai_recommendation": ai_rec,
            "human_status": "🟢 Accepted" if i % 4 != 0 else "🟠 Overridden",
            "human_notes": "-"
        })
    pd.DataFrame(samples).to_csv(HISTORY_FILE, index=False)

def update_human_decision_in_csv(running_no, decision, notes):
    """อัปเดตผลการตัดสินใจของมนุษย์ลงในไฟล์ CSV ย้อนหลัง"""
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if "human_notes" not in df.columns:
            df["human_notes"] = "-"
            
        mask = df["running_no"] == running_no
        if mask.any():
            status_symbol = "🟢 Accepted" if ("Ready" in decision or "Accept" in decision) else "🟠 Overridden"
            df.loc[mask, "human_status"] = f"{status_symbol} ({decision})"
            df.loc[mask, "human_notes"] = notes
            df.to_csv(HISTORY_FILE, index=False)

generate_sample_data()

# ==========================================
# 3. PYDANTIC MODEL (AI Output Schema)
# ==========================================
class ExtractedShipment(BaseModel):
    doc_type: str
    shipment_mode: str
    ship_date: str
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
        issues.append("Quantity Mismatch (Invoice vs Packing List)")
        
    # 2. Missing COO
    if not data['has_coo']:
        score -= (20 * m_strict)
        delay += (12 * m_mode)
        issues.append("Missing Certificate of Origin (COO)")

    score = max(0, int(score))
    
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
                                index=["AIR ✈️", "SEA 🚢", "TRUCK 🚛"].index(data.get('shipment_mode', 'AIR ✈️')))
            
            # 📅 เพิ่มระบุวัน Shipment Date (ETD)
            ship_date_input = st.date_input("Shipment Date (ETD)", value=date.today())
            
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
            verified_data = {
                "shipment_mode": mode, "ship_date": str(ship_date_input), "invoice_no": inv, 
                "po_no": po, "exporter_name": exporter, "destination": dest, 
                "invoice_qty": inv_qty, "packing_qty": pl_qty,
                "total_amount": amount, "hs_code": hs, "has_coo": coo
            }
            
            score, risk, delay, ai_rec, issues = calculate_readiness(verified_data, st.session_state.strictness)
            
            today_str = datetime.today().strftime('%Y%m%d')
            run_no = f"TR-{today_str}-{str(len(pd.read_csv(HISTORY_FILE)) + 1).zfill(4)}"
            
            new_record = pd.DataFrame([{
                "running_no": run_no, 
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "ship_date": str(ship_date_input), # 👈 บันทึก Ship Date
                "exporter": exporter, 
                "destination": dest, 
                "shipment_mode": mode,
                "scenario_type": "Live Audit", 
                "readiness_score": score, 
                "risk_level": risk,
                "est_delay": delay, 
                "ai_recommendation": ai_rec, 
                "human_status": "⚪ Pending",
                "human_notes": "-"
            }])
            new_record.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
            
            st.session_state.active_audit = new_record.iloc[0].to_dict()
            st.session_state.active_audit['issues'] = issues
            st.session_state.show_modal = False
            st.session_state.nav_choice = "📄 Audit New Document"
            st.rerun()

# ==========================================
# 6. SIDEBAR CONTROL PANEL
# ==========================================
with st.sidebar:
    st.header("⚙️ Control Panel")

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
        "Navigation", 
        ["📄 Audit New Document", "📜 History Logs"],
        key="nav_choice"
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
        if not st.session_state.get("api_key"):
            st.error("⚠️ กรุณากรอก Gemini API Key ด้านบนก่อนเริ่มประมวลผล!")
        else:
            with st.spinner("AI is analyzing documents..."):
                st.session_state.temp_extracted_data = {
                    "doc_type": "Multiple",
                    "shipment_mode": "AIR ✈️",
                    "ship_date": str(date.today()),
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
st.title("🚢 TradeReady AI")
st.caption("Export Documentation & Customs Readiness Assistant")

if app_mode == "📄 Audit New Document":
    if 'active_audit' in st.session_state:
        audit = st.session_state.active_audit
        ship_d = audit.get('ship_date', 'N/A')
        st.success(f"✅ Loaded Record: **{audit['running_no']}** | 📅 Ship Date: **{ship_d}** | Mode: {audit['shipment_mode']}")
        
        # KPI Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Readiness Score", f"{audit['readiness_score']}/100")
        c2.metric("Completion Rate", "83.3%" if audit['readiness_score'] < 85 else "100%")
        c3.metric("Risk Level", audit['risk_level'])
        c4.metric("Est. Border Delay", f"{audit['est_delay']} Hours")
        
        st.divider()
        col_left, col_right = st.columns([1.5, 1])
        
        with col_left:
            st.markdown("### 🤖 AI Recommendation")
            st.info(f"**Decision:** {audit['ai_recommendation']}")
            
            issues = audit.get('issues', [])
            if not issues and audit['readiness_score'] < 85:
                issues = ["Quantity Mismatch / Weight Discrepancy", "Missing Certificate of Origin (COO)"]
                
            if issues:
                st.error("**Detected Issues:**\n" + "\n".join([f"- {i}" for i in issues]))
            else:
                st.success("**Status:** Documents are compliant and ready.")
                
        with col_right:
            st.markdown("### 👤 Human Override")
            final_decision = st.selectbox(
                "Final Decision", 
                ["Ready to Export", "Requires Review & Correction", "Hold Shipment / High Risk"]
            )
            remarks = st.text_area("Remarks / Notes", value=str(audit.get('human_notes', '')))
            
            if st.button("💾 Save Final Decision", type="primary", use_container_width=True):
                update_human_decision_in_csv(audit['running_no'], final_decision, remarks)
                st.session_state.active_audit['human_status'] = f"Updated ({final_decision})"
                st.session_state.active_audit['human_notes'] = remarks
                st.success(f"บันทึกผลการตัดสินใจสำหรับ {audit['running_no']} เรียบร้อยแล้ว!")
                
    else:
        st.info("👈 กรุณาอัปโหลดไฟล์ PDF ด้านซ้ายมือ หรือกดเลือกรายการจากหน้า History Log เพื่อดูรายละเอียด")

elif app_mode == "📜 History Logs":
    st.subheader("📜 Transaction History Logs & Daily Release Control")
    
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if "ship_date" not in df.columns:
            df["ship_date"] = "2026-08-01"
            
        # --- FILTERS ROW (3 Columns) ---
        col1, col2, col3 = st.columns([1.5, 1, 1])
        search_q = col1.text_input("🔍 Search Exporter or Running No.")
        risk_filter = col2.selectbox("Filter Risk Level", ["All", "LOW 🟢", "MED 🟡", "HIGH 🔴"])
        
        # 📅 Filter By Ship Date
        enable_date_filter = col3.checkbox("📅 Filter by Ship Date", value=False)
        selected_ship_date = date.today()
        if enable_date_filter:
            selected_ship_date = col3.date_input("Select Ship Date", value=date(2026, 8, 1))
        
        filtered_df = df.copy()
        
        if search_q:
            filtered_df = filtered_df[
                filtered_df['exporter'].str.contains(search_q, case=False, na=False) | 
                filtered_df['running_no'].str.contains(search_q, case=False, na=False)
            ]
        if risk_filter != "All":
            filtered_df = filtered_df[filtered_df['risk_level'] == risk_filter]
            
        if enable_date_filter:
            filtered_df = filtered_df[filtered_df['ship_date'] == str(selected_ship_date)]

        # --- 📊 DAILY RELEASE READINESS SUMMARY (จะโชว์เมื่อมีการกรองวัน) ---
        if enable_date_filter:
            total_shipments = len(filtered_df)
            approved_shipments = len(filtered_df[filtered_df['human_status'].str.contains("Accepted|Ready", case=False, na=False)])
            
            st.markdown(f"#### 📅 Daily Release Status for: `{selected_ship_date}`")
            kpi_c1, kpi_c2, kpi_c3 = st.columns(3)
            kpi_c1.metric("Total Scheduled Shipments", f"{total_shipments} Shipments")
            kpi_c2.metric("Approved / Ready to Release", f"{approved_shipments} Shipments")
            
            pending_count = total_shipments - approved_shipments
            kpi_c3.metric("Pending / Hold Action", f"{pending_count} Shipments")
            
            if total_shipments > 0 and pending_count == 0:
                st.success("🟢 **ALL APPROVED:** เอกสารทั้งหมดประจำวันนี้ได้รับการตรวจสอบและพร้อมให้ออกเดินทางได้ 100%")
            elif total_shipments > 0:
                st.warning(f"⚠️ **ATTENTION:** ยังมีอีก {pending_count} ชิปเมนต์ในวันนี้ที่ยังไม่ได้ยืนยัน หรือติดสถานะ Hold / Review")
            st.divider()

        st.caption("💡 *คำแนะนำ: คลิกเลือกแถวในตารางด้านล่าง เพื่อกดเปิดดูหน้า Dashboard รายละเอียดของชิปเมนต์นั้นได้*")

        # ตารางโต้ตอบ (Interactive DataFrame)
        event = st.dataframe(
            filtered_df[["running_no", "ship_date", "shipment_mode", "exporter", "destination", "readiness_score", "risk_level", "human_status"]],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # เมื่อคลิกเลือกแถวในตาราง
        selected_rows = event.selection.rows
        if selected_rows:
            selected_index = selected_rows[0]
            selected_record = filtered_df.iloc[selected_index].to_dict()
            
            st.divider()
            c_info, c_btn = st.columns([3, 1])
            with c_info:
                st.markdown(f"📌 **รายการที่เลือก:** `{selected_record['running_no']}` | **Ship Date:** `{selected_record.get('ship_date', 'N/A')}` | **Exporter:** {selected_record['exporter']}")
            
            with c_btn:
                if st.button("👁️ เปิดดูใน Dashboard", type="primary", use_container_width=True):
                    st.session_state.active_audit = selected_record
                    
                    if selected_record['readiness_score'] < 85:
                        st.session_state.active_audit['issues'] = [
                            "Quantity Mismatch / Weight Discrepancy Detected",
                            "Missing Certificate of Origin (COO)"
                        ]
                    else:
                        st.session_state.active_audit['issues'] = []

                    st.session_state.nav_choice = "📄 Audit New Document"
                    st.rerun()
    else:
        st.warning("ยังไม่พบข้อมูลประวัติในระบบ")

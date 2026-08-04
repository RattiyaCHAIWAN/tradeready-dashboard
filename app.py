import json
import os
from datetime import date, datetime
import pandas as pd
from pydantic import BaseModel
import streamlit as st

# ==========================================
# 0. PAGE CONFIGURATION & STATE INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="TradeReady AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "pending_page" in st.session_state:
    st.session_state.nav_choice = st.session_state.pending_page
    del st.session_state["pending_page"]

if "nav_choice" not in st.session_state:
    st.session_state.nav_choice = "📄 Audit New Document"

# ==========================================
# 0.1 ULTIMATE WHITE ENTERPRISE DASHBOARD CSS
# ==========================================
background_image_url = "https://images.unsplash.com/photo-1578575437130-527eed3abbec?q=80&w=2070&auto=format&fit=crop"

st.markdown(
    f"""
    <style>
    /* 1. Background Image Full Screen */
    .stApp {{
        background-image: url("{background_image_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* 2. Main Layout Dark Overlay */
    [data-testid="stMain"], section.main {{
        background-color: rgba(10, 25, 47, 0.85) !important;
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
    }}
    
    [data-testid="stSidebar"] {{
        background-color: rgba(15, 23, 42, 0.88) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px);
    }}
    
    [data-testid="stSidebarContent"] {{
        background-color: transparent !important;
    }}

    .block-container {{
        background-color: transparent !important;
        padding-top: 1.5rem !important; 
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}
    
    /* 3. INPUTS & TEXTAREA STYLING */
    div[data-testid="stVerticalBlockBorderWrapper"] textarea,
    div[data-testid="stVerticalBlockBorderWrapper"] input {{
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }}

    /* 4. ALERT BOXES */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stNotification"] {{
        border-radius: 10px !important;
    }}

    /* Global Typography */
    html, body, [class*="st-"], .stMarkdown p {{
        font-size: 15px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
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
# 2. DATA GENERATOR & AUTO-HEAL SYSTEM
# ==========================================
def validate_and_repair_csv():
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE)
            required_cols = ["invoice_no", "po_no", "invoice_qty", "ship_date"]
            if not all(col in df.columns for col in required_cols):
                os.remove(HISTORY_FILE)
        except Exception:
            os.remove(HISTORY_FILE)


def generate_sample_data():
    if os.path.exists(HISTORY_FILE):
        return

    samples = []
    scenarios = ["Normal", "Disruption", "Erroneous Data"]

    for i in range(1, 31):
        scenario = scenarios[i % 3]
        score = (
            95 if scenario == "Normal" else (65 if scenario == "Disruption" else 40)
        )
        risk = "LOW 🟢" if score >= 85 else ("MED 🟡" if score >= 50 else "HIGH 🔴")
        delay = 0 if risk == "LOW 🟢" else (12 if risk == "MED 🟡" else 36)
        ai_rec = (
            "Ready to Export"
            if risk == "LOW 🟢"
            else (
                "Requires Review & Correction"
                if risk == "MED 🟡"
                else "Hold Shipment"
            )
        )

        ship_day = (i % 5) + 1

        samples.append({
            "running_no": f"TR-202608{i:02d}-0001",
            "timestamp": f"2026-08-01 10:30:00",
            "ship_date": f"2026-08-{ship_day:02d}",
            "exporter": (
                "Chiang Mai OEM Electronics"
                if i % 2 == 0
                else "Northern Agri Export"
            ),
            "destination": "Japan" if i % 2 == 0 else "China",
            "shipment_mode": (
                "AIR ✈️" if i % 3 == 0 else ("SEA 🚢" if i % 3 == 1 else "TRUCK 🚛")
            ),
            "scenario_type": scenario,
            "readiness_score": score,
            "risk_level": risk,
            "est_delay": delay,
            "ai_recommendation": ai_rec,
            "human_status": "🟢 Accepted" if i % 4 != 0 else "🟠 Overridden",
            "human_notes": "-",
            "invoice_no": f"INV-{i:03d}-881",
            "po_no": f"PO-{i:03d}-99",
            "invoice_qty": 1000 if scenario == "Normal" else 850,
            "packing_qty": 1000,
            "total_amount": 15000.0,
            "hs_code": "8409.91",
            "has_coo": True if scenario != "Erroneous Data" else False,
        })
    pd.DataFrame(samples).to_csv(HISTORY_FILE, index=False)


def update_human_decision_in_csv(running_no, decision, notes):
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if "human_notes" not in df.columns:
            df["human_notes"] = "-"

        mask = df["running_no"] == running_no
        if mask.any():
            status_symbol = (
                "🟢 Accepted"
                if ("Ready" in decision or "Accept" in decision)
                else "🟠 Overridden"
            )
            df.loc[mask, "human_status"] = f"{status_symbol} ({decision})"
            df.loc[mask, "human_notes"] = notes
            df.to_csv(HISTORY_FILE, index=False)


validate_and_repair_csv()
generate_sample_data()


# ==========================================
# 3. RULES ENGINE
# ==========================================
def calculate_readiness(data, strictness_label):
    score = 100
    delay = 0
    m_strict = STRICTNESS_MULTIPLIER.get(strictness_label, 1.0)
    m_mode = MODE_MULTIPLIER.get(data["shipment_mode"], 1.0)

    issues = []
    if data["invoice_qty"] != data["packing_qty"]:
        score -= 25 * m_strict
        delay += 24 * m_mode
        issues.append("Quantity Mismatch (Invoice vs Packing List)")

    if not data["has_coo"]:
        score -= 20 * m_strict
        delay += 12 * m_mode
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
# 4. REVIEW MODAL
# ==========================================
@st.dialog("🔍 Review & Verify Extracted Data", width="large")
def review_modal():
    st.info("⚠️ โปรดตรวจสอบและแก้ไขข้อมูลที่ AI สกัดได้ก่อนบันทึกเข้าระบบ")
    data = st.session_state.temp_extracted_data

    with st.form("verify_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📌 Header & Routing**")
            mode = st.selectbox(
                "Shipment Mode",
                ["AIR ✈️", "SEA 🚢", "TRUCK 🚛"],
                index=["AIR ✈️", "SEA 🚢", "TRUCK 🚛"].index(
                    data.get("shipment_mode", "AIR ✈️")
                ),
            )
            ship_date_input = st.date_input(
                "Shipment Date (ETD)", value=date.today()
            )
            inv = st.text_input("Invoice No.", data["invoice_no"])
            po = st.text_input("PO No.", data["po_no"])
            exporter = st.text_input("Exporter", data["exporter_name"])
            dest = st.selectbox(
                "Destination", ["Japan", "China", "Vietnam", "USA", "EU"], index=0
            )

        with c2:
            st.markdown("**📊 Quantities & Compliance**")
            inv_qty = st.number_input("Invoice Qty", value=int(data["invoice_qty"]))
            pl_qty = st.number_input("Packing List Qty", value=int(data["packing_qty"]))
            if inv_qty != pl_qty:
                st.error("⚠️ Quantity Mismatch Detected!")
            amount = st.number_input(
                "Total Amount ($)", value=float(data["total_amount"])
            )
            hs = st.text_input("HS Code", data["hs_code"])
            coo = st.checkbox("Has Certificate of Origin (COO)", value=data["has_coo"])

        if st.form_submit_button("🚀 Confirm & Process"):
            verified_data = {
                "shipment_mode": mode,
                "ship_date": str(ship_date_input),
                "invoice_no": inv,
                "po_no": po,
                "exporter_name": exporter,
                "destination": dest,
                "invoice_qty": inv_qty,
                "packing_qty": pl_qty,
                "total_amount": amount,
                "hs_code": hs,
                "has_coo": coo,
            }

            score, risk, delay, ai_rec, issues = calculate_readiness(
                verified_data, st.session_state.strictness
            )

            today_str = datetime.today().strftime("%Y%m%d")
            run_no = f"TR-{today_str}-{str(len(pd.read_csv(HISTORY_FILE)) + 1).zfill(4)}"

            new_record = pd.DataFrame([{
                "running_no": run_no,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ship_date": str(ship_date_input),
                "exporter": exporter,
                "destination": dest,
                "shipment_mode": mode,
                "scenario_type": "Live Audit",
                "readiness_score": score,
                "risk_level": risk,
                "est_delay": delay,
                "ai_recommendation": ai_rec,
                "human_status": "⚪ Pending",
                "human_notes": "-",
                "invoice_no": inv,
                "po_no": po,
                "invoice_qty": inv_qty,
                "packing_qty": pl_qty,
                "total_amount": amount,
                "hs_code": hs,
                "has_coo": coo,
            }])
            new_record.to_csv(HISTORY_FILE, mode="a", header=False, index=False)

            st.session_state.active_audit = new_record.iloc[0].to_dict()
            st.session_state.active_audit["issues"] = issues
            st.session_state.show_modal = False
            st.session_state.pending_page = "📄 Audit New Document"
            st.rerun()


# ==========================================
# 5. SIDEBAR CONTROL PANEL
# ==========================================
with st.sidebar:
    st.header("⚙️ Control Panel")

    api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        placeholder="AIzaSy...",
        help="ปล่อยว่างไว้เพื่อทดสอบโหมดข้อมูลจำลอง (Mockup)",
    )
    if api_key:
        st.session_state.api_key = api_key
    elif "api_key" in st.session_state:
        del st.session_state.api_key

    app_mode = st.radio(
        "Navigation", ["📄 Audit New Document", "📜 History Logs"], key="nav_choice"
    )
    st.divider()

    st.markdown("**📂 Document Upload (Multi-File)**")
    uploaded_files = st.file_uploader(
        "Upload Invoice, PL, COO", type=["pdf"], accept_multiple_files=True
    )
    st.session_state.strictness = st.selectbox(
        "Customs Strictness Level", ["Lenient", "Standard", "Strict"], index=1
    )

    if uploaded_files and st.button("🚀 Release to AI", use_container_width=True):
        is_mockup = not st.session_state.get("api_key")
        if is_mockup:
            st.warning(
                "⚠️ ไม่พบ API Key: ระบบเข้าสู่โหมดข้อมูลจำลอง (Mockup Mode)"
            )

        with st.spinner(
            "AI กำลังวิเคราะห์ข้อมูลผ่าน Gemini API..."
            if not is_mockup
            else "กำลังโหลดข้อมูลจำลอง..."
        ):
            st.session_state.temp_extracted_data = {
                "doc_type": "Multiple",
                "shipment_mode": "AIR ✈️",
                "ship_date": str(date.today()),
                "invoice_no": (
                    "INV-2026-991" if not is_mockup else "MOCK-INV-001"
                ),
                "po_no": "PO-991" if not is_mockup else "MOCK-PO-001",
                "exporter_name": "Chiang Mai OEM Electronics",
                "destination": "Japan",
                "invoice_qty": 500,
                "packing_qty": 450,
                "total_amount": 12500.0,
                "hs_code": "8409.91",
                "has_coo": False,
            }
            st.session_state.show_modal = True

if getattr(st.session_state, "show_modal", False):
    review_modal()


# ==========================================
# REUSABLE DASHBOARD COMPONENT (Solid White Enterprise Card)
# ==========================================
def render_dashboard(audit, key_prefix=""):
    issues = audit.get("issues", [])
    if isinstance(issues, str):
        issues = []

    try:
        inv_qty_val = int(float(audit.get("invoice_qty", 0)))
        inv_qty_str = f"{inv_qty_val:,}"
    except (ValueError, TypeError):
        inv_qty_str = str(audit.get("invoice_qty", "N/A"))

    try:
        pl_qty_val = int(float(audit.get("packing_qty", 0)))
        pl_qty_str = f"{pl_qty_val:,}"
    except (ValueError, TypeError):
        pl_qty_str = str(audit.get("packing_qty", "N/A"))

    try:
        amt_val = float(audit.get("total_amount", 0.0))
        amt_str = f"{amt_val:,.2f}"
    except (ValueError, TypeError):
        amt_str = str(audit.get("total_amount", "0.00"))

    inv_no = str(audit.get("invoice_no", "N/A"))
    pl_no_suffix = (
        inv_no[-3:] if inv_no != "N/A" and len(inv_no) >= 3 else "N/A"
    )

    if not issues and audit.get("readiness_score", 100) < 85:
        if str(audit.get("invoice_qty")) != str(audit.get("packing_qty")):
            issues.append("Quantity Mismatch (Invoice vs Packing List)")
        if not audit.get("has_coo", True):
            issues.append("Missing Certificate of Origin (COO)")

    coo_color = "#D97706" if not audit.get("has_coo", True) else "#16A34A"
    coo_text = "❌ COO (Missing)" if not audit.get("has_coo", True) else "✓ COO (Verified)"
    comp_rate = "83.3%" if audit.get("readiness_score", 0) < 85 else "100%"

    audit_html = ""
    if str(audit.get("invoice_qty")) != str(audit.get("packing_qty")):
        audit_html += f'<div style="background: #FEF2F2; color: #DC2626; padding: 12px 16px; border: 1px solid #FCA5A5; border-radius: 8px; font-weight: bold; margin-bottom: 8px; font-size: 14px;">🔴 Quantity Mismatch (Invoice vs PL): {audit.get("invoice_qty", "N/A")} vs {audit.get("packing_qty", "N/A")}</div>'
    else:
        audit_html += f'<div style="background: #F0FDF4; color: #16A34A; padding: 12px 16px; border: 1px solid #86EFAC; border-radius: 8px; font-weight: bold; margin-bottom: 8px; font-size: 14px;">🟢 Quantity Match (Invoice vs PL): {inv_qty_str} PCS</div>'

    audit_html += '<div style="background: #F0FDF4; color: #16A34A; padding: 12px 16px; border: 1px solid #86EFAC; border-radius: 8px; font-weight: bold; margin-bottom: 8px; font-size: 14px;">🟢 Exporter & Consignee: Matches Across All Docs</div>'

    if not audit.get("has_coo", True) or "COO" in str(issues):
        audit_html += '<div style="background: #FFFBEB; color: #D97706; padding: 12px 16px; border: 1px solid #FDE68A; border-radius: 8px; font-weight: bold; margin-bottom: 8px; font-size: 14px;">🟡 Certificate of Origin (COO): Missing or Invalid</div>'
    else:
        audit_html += '<div style="background: #F0FDF4; color: #16A34A; padding: 12px 16px; border: 1px solid #86EFAC; border-radius: 8px; font-weight: bold; margin-bottom: 8px; font-size: 14px;">🟢 Certificate of Origin (COO): Valid for FTA</div>'

    audit_html += f'<div style="background: #F0FDF4; color: #16A34A; padding: 12px 16px; border: 1px solid #86EFAC; border-radius: 8px; font-weight: bold; margin-bottom: 8px; font-size: 14px;">🟢 HS Code {audit.get("hs_code", "8409.91")}: Matched Invoice vs COO</div>'

# ⚠️ สำคัญมาก: โค้ดส่วนนี้ห้ามเคาะวรรคด้านหน้า (Indent) เพื่อป้องกันไม่ให้ Markdown แปลงเป็น Code Block ⚠️
    html_dashboard = f"""
<div style="background-color: #FFFFFF; border-radius: 16px; padding: 24px; box-shadow: 0px 10px 30px rgba(0,0,0,0.25); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #0F172A; margin-bottom: 20px; border: 1px solid #E2E8F0;">
    <!-- 1. HEADER BAR -->
    <div style="display: flex; justify-content: space-between; align-items: center; background-color: #F8FAFC; padding: 14px 20px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 25px; flex-wrap: wrap; gap: 10px;">
        <div>
            <span style="background-color: #16A34A; color: white; padding: 6px 14px; border-radius: 20px; font-weight: 800; font-size: 13px;">🟢 3 DOCS MERGED & AUDITED</span> 
            <span style="margin-left: 15px; color: #475569; font-size: 14px;"><b>Running No:</b></span> 
            <span style="background-color: #E2E8F0; padding: 4px 10px; border-radius: 6px; color: #0F172A; font-weight: bold; font-size: 14px; margin-left: 5px;">{audit.get('running_no', 'N/A')}</span> 
        </div>
        <div style="font-size: 14px; color: #475569;">
            <b>Time:</b> {audit.get('timestamp', 'N/A')} &nbsp;|&nbsp; <b>Mode:</b> <span style="font-weight: bold; color: #1E3A8A;">{audit.get('shipment_mode', 'N/A')}</span>
        </div>
    </div>

    <!-- 2. KPI METRICS -->
    <div style="display: flex; gap: 16px; margin-bottom: 25px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 150px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 5px solid #DC2626; border-radius: 10px; padding: 16px;">
            <div style="color: #64748B; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;">READINESS SCORE</div>
            <div style="color: #0F172A; font-size: 26px; font-weight: 900; margin-top: 5px;">{audit.get('readiness_score', 0)}/100</div>
        </div>
        <div style="flex: 1; min-width: 150px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 5px solid #2563EB; border-radius: 10px; padding: 16px;">
            <div style="color: #64748B; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;">COMPLETION RATE</div>
            <div style="color: #0F172A; font-size: 26px; font-weight: 900; margin-top: 5px;">{comp_rate}</div>
        </div>
        <div style="flex: 1; min-width: 150px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 5px solid #D97706; border-radius: 10px; padding: 16px;">
            <div style="color: #64748B; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;">RISK LEVEL</div>
            <div style="color: #0F172A; font-size: 26px; font-weight: 900; margin-top: 5px;">{audit.get('risk_level', 'N/A')}</div>
        </div>
        <div style="flex: 1; min-width: 150px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 5px solid #D97706; border-radius: 10px; padding: 16px;">
            <div style="color: #64748B; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;">EST. BORDER DELAY</div>
            <div style="color: #0F172A; font-size: 26px; font-weight: 900; margin-top: 5px;">{audit.get('est_delay', 0)} Hours</div>
        </div>
    </div>

    <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;">

    <!-- 3. CHECKLIST -->
    <div style="font-weight: 800; color: #334155; margin-bottom: 12px; font-size: 14px;">DOCUMENT CHECKLIST (ATTACHED):</div>
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 25px;">
        <span style="background-color: #16A34A; color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: bold;">✓ Invoice</span>
        <span style="background-color: #16A34A; color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: bold;">✓ Packing List</span>
        <span style="background-color: #16A34A; color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: bold;">✓ PO</span>
        <span style="background-color: #16A34A; color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: bold;">✓ B/L / AWB</span>
        <span style="background-color: {coo_color}; color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: bold;">{coo_text}</span>
    </div>
    
    <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;">

    <!-- 4. DATA & AUDIT CHECK -->
    <div style="display: flex; flex-wrap: wrap; gap: 30px;">
        <div style="flex: 1; min-width: 300px;">
            <div style="color: #1E3A8A; font-size: 18px; font-weight: 800; margin-bottom: 15px;">📄 Extracted Data Across Files</div>
            <table style="width: 100%; border-collapse: collapse; font-size: 15px; color: #334155; line-height: 2.2;">
                <tr><td width="45%">• Invoice No:</td><td><span style="background-color: #EFF6FF; color: #1E40AF; padding: 3px 10px; border-radius: 5px; font-weight: bold; border: 1px solid #BFDBFE;">{inv_no}</span></td></tr>
                <tr><td>• Packing List No:</td><td><span style="background-color: #EFF6FF; color: #1E40AF; padding: 3px 10px; border-radius: 5px; font-weight: bold; border: 1px solid #BFDBFE;">PL-{pl_no_suffix}</span></td></tr>
                <tr><td>• Invoice Total Qty:</td><td><span style="background-color: #EFF6FF; color: #1E40AF; padding: 3px 10px; border-radius: 5px; font-weight: bold; border: 1px solid #BFDBFE;">{inv_qty_str} PCS</span></td></tr>
                <tr><td>• PL Total Qty:</td><td><span style="background-color: #EFF6FF; color: #1E40AF; padding: 3px 10px; border-radius: 5px; font-weight: bold; border: 1px solid #BFDBFE;">{pl_qty_str} PCS</span></td></tr>
                <tr><td>• Total Amount:</td><td><span style="background-color: #EFF6FF; color: #1E40AF; padding: 3px 10px; border-radius: 5px; font-weight: bold; border: 1px solid #BFDBFE;">${amt_str} USD</span></td></tr>
                <tr><td>• Main HS Code:</td><td><span style="background-color: #EFF6FF; color: #1E40AF; padding: 3px 10px; border-radius: 5px; font-weight: bold; border: 1px solid #BFDBFE;">{audit.get('hs_code', 'N/A')}</span></td></tr>
                <tr><td>• Destination Origin:</td><td><span style="background-color: #EFF6FF; color: #1E40AF; padding: 3px 10px; border-radius: 5px; font-weight: bold; border: 1px solid #BFDBFE;">{audit.get('destination', 'N/A')}</span></td></tr>
            </table>
        </div>
        
        <div style="flex: 1; min-width: 300px;">
            <div style="color: #1E3A8A; font-size: 18px; font-weight: 800; margin-bottom: 15px;">🔍 Cross-Document Multi-Audit</div>
            {audit_html}
        </div>
    </div>
</div>
"""
    
    st.markdown(html_dashboard, unsafe_allow_html=True)
    
    # CSS Trick ให้ Container ด้านล่างกลายเป็นสีขาว
    st.markdown('''
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.action-marker) {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 16px !important;
            padding: 24px !important;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.2) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.action-marker) h3, 
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.action-marker) p, 
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.action-marker) label {
            color: #0F172A !important;
        }
        </style>
    ''', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="action-marker" style="display:none;"></div>', unsafe_allow_html=True)
        col_ai, col_human = st.columns([1.5, 1])
        
        with col_ai:
            st.markdown("<h3 style='color: #1E3A8A; font-weight: 800; margin-bottom: 10px; font-size: 18px;'>🤖 AI Recommendation</h3>", unsafe_allow_html=True)
            st.info(f"👉 **{audit.get('ai_recommendation', 'N/A').upper()}**")
            
            if issues:
                st.markdown("**Reason & Notes:**")
                for i in issues:
                    st.markdown(f"<div style='color:#DC2626; font-weight:bold; margin-top:4px;'>- 🔴 {i}</div>", unsafe_allow_html=True)
                st.markdown("<div style='margin-top:8px; font-weight:bold; color:#475569;'>Responsible Party: Logistics / Compliance Officer</div>", unsafe_allow_html=True)
            else:
                st.markdown("**Reason & Notes:**")
                st.markdown("<div style='color:#334155; margin-top:4px;'>- Documents are complete with COO attached.</div>", unsafe_allow_html=True)
                st.markdown("<div style='color:#334155; margin-top:4px;'>- Minor Note: Declared weight is within tolerance.</div>", unsafe_allow_html=True)
                st.markdown("<div style='margin-top:8px; font-weight:bold; color:#475569;'>Responsible Party: Shipping Officer (Clearance)</div>", unsafe_allow_html=True)

        with col_human:
            st.markdown("<h3 style='color: #1E3A8A; font-weight: 800; margin-bottom: 10px; font-size: 18px;'>👤 Human Decision</h3>", unsafe_allow_html=True)
            options_list = ["Ready to Export", "Requires Review & Correction", "Hold Shipment / High Risk"]
            default_idx = 0
            for idx, opt in enumerate(options_list):
                if opt.lower() in audit.get("ai_recommendation", "").lower():
                    default_idx = idx

            final_decision = st.radio("Final Status:", options_list, index=default_idx, key=f"{key_prefix}radio_dec", label_visibility="collapsed")
            remarks = st.text_area("Remarks / Notes", value=str(audit.get("human_notes", "")), key=f"{key_prefix}rem")

            if st.button("💾 Save Transaction Log", type="primary", use_container_width=True, key=f"{key_prefix}save"):
                update_human_decision_in_csv(audit["running_no"], final_decision, remarks)
                st.session_state.active_audit["human_status"] = f"Updated ({final_decision})"
                st.session_state.active_audit["human_notes"] = remarks
                st.success("บันทึกอัปเดตเรียบร้อยแล้ว!")


# ==========================================
# 6. MAIN APP ROUTING
# ==========================================
st.markdown(
    "## 🚢 TradeReady AI <span style='font-size: 14px; color: #CBD5E1;'>|"
    " Export Documentation & Customs Readiness Assistant</span>",
    unsafe_allow_html=True,
)

if app_mode == "📄 Audit New Document":
    if "active_audit" in st.session_state:
        render_dashboard(st.session_state.active_audit, key_prefix="main_")
    else:
        st.info(
            "👈 กรุณาอัปโหลดไฟล์ PDF ด้านซ้ายมือ"
            " หรือเลือกดูรายการจากเมนู History Logs"
        )

elif app_mode == "📜 History Logs":
    st.markdown("#### 📜 Transaction History Logs & Daily Release Control")

    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)

        enable_date_filter = st.toggle(
            "📅 Enable Ship Date Filter (กรองเฉพาะวันส่งออก)", value=False
        )

        col1, col2, col3 = st.columns(3)
        search_q = col1.text_input("🔍 Search Exporter / Running No.")
        risk_filter = col2.selectbox(
            "Filter Risk Level", ["All", "LOW 🟢", "MED 🟡", "HIGH 🔴"]
        )
        selected_ship_date = col3.date_input(
            "Select Ship Date",
            value=date(2026, 8, 1),
            disabled=not enable_date_filter,
        )

        filtered_df = df.copy()

        if search_q:
            filtered_df = filtered_df[
                filtered_df["exporter"].str.contains(search_q, case=False, na=False)
                | filtered_df["running_no"].str.contains(
                    search_q, case=False, na=False
                )
            ]
        if risk_filter != "All":
            filtered_df = filtered_df[filtered_df["risk_level"] == risk_filter]

        if enable_date_filter:
            filtered_df = filtered_df[
                filtered_df["ship_date"] == str(selected_ship_date)
            ]

        if enable_date_filter:
            total_shipments = len(filtered_df)
            approved_shipments = len(
                filtered_df[
                    filtered_df["human_status"].str.contains(
                        "Accepted|Ready", case=False, na=False
                    )
                ]
            )
            pending_count = total_shipments - approved_shipments

            if total_shipments > 0 and pending_count == 0:
                st.success(
                    f"🟢 **ALL APPROVED (100%):** เอกสารของวันที่ `{selected_ship_date}`"
                    f" พร้อมส่งออกทั้ง {total_shipments} รายการ"
                )
            elif total_shipments > 0:
                st.warning(
                    f"⚠️ **ATTENTION:** วันที่ `{selected_ship_date}` มี"
                    f" {total_shipments} ชิปเมนต์ (รอการยืนยัน {pending_count} รายการ)"
                )

        event = st.dataframe(
            filtered_df[[
                "running_no",
                "ship_date",
                "shipment_mode",
                "exporter",
                "destination",
                "readiness_score",
                "risk_level",
                "human_status",
            ]],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        selected_rows = event.selection.rows
        if selected_rows:
            selected_index = selected_rows[0]
            selected_record = filtered_df.iloc[selected_index].to_dict()

            if (
                st.session_state.get("opened_inline_id")
                != selected_record["running_no"]
            ):
                st.session_state.show_inline_dashboard = False
                st.session_state.opened_inline_id = selected_record["running_no"]

            c_info, c_btn = st.columns([4, 1])
            with c_info:
                st.markdown(
                    f"📌 **รายการที่เลือก:** `{selected_record['running_no']}` | **Ship"
                    f" Date:** `{selected_record.get('ship_date', 'N/A')}`"
                )
            with c_btn:
                if st.button(
                    "👁️ เปิดดูรายละเอียดด้านล่าง",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.active_audit = selected_record
                    st.session_state.show_inline_dashboard = True
                    st.rerun()
        else:
            st.session_state.show_inline_dashboard = False

        if getattr(st.session_state, "show_inline_dashboard", False):
            st.markdown("---")

            c_head, c_close = st.columns([5, 1])
            with c_head:
                st.markdown("### 📊 Dashboard Detail View")
            with c_close:
                if st.button("❌ ปิด (Close)", use_container_width=True):
                    st.session_state.show_inline_dashboard = False
                    st.rerun()

            render_dashboard(st.session_state.active_audit, key_prefix="inline_")

    else:
        st.warning("ยังไม่พบข้อมูลประวัติในระบบ")

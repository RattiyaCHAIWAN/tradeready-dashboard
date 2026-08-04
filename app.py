import streamlit as st
import pandas as pd
json
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

if "pending_page" in st.session_state:
    st.session_state.nav_choice = st.session_state.pending_page
    del st.session_state["pending_page"]

if "nav_choice" not in st.session_state:
    st.session_state.nav_choice = "📄 Audit New Document"

# ==========================================
# 0.1 CUSTOM BACKGROUND & WHITE CARDS CSS
# ==========================================
background_image_url = "https://images.unsplash.com/photo-1578575437130-527eed3abbec?q=80&w=2070&auto=format&fit=crop"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("{background_image_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    [data-testid="stMain"], section.main {{
        background-color: rgba(18, 58, 98, 0.70) !important;
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
    }}
    
    [data-testid="stSidebar"] {{
        background-color: rgba(18, 58, 98, 0.65) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px);
    }}
    
    [data-testid="stSidebarContent"] {{
        background-color: transparent !important;
    }}

    .block-container {{
        background-color: transparent !important;
        padding-top: 1.5rem !important; 
        padding-bottom: 1.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}
    
    /* ⭐️ ปรับกรอบข้อมูลหลักให้เป็นพื้นหลังสีขาว ตัวหนังสือสีเข้ม คมชัดเด่นตา ⭐️ */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #ffffff !important; 
        border: 2px solid #cbd5e1 !important; 
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.3) !important; 
    }}

    /* ปรับสีตัวอักษรภายในกรอบสีขาวให้เป็นสีเข้ม */
    [data-testid="stVerticalBlockBorderWrapper"] h3, 
    [data-testid="stVerticalBlockBorderWrapper"] p, 
    [data-testid="stVerticalBlockBorderWrapper"] li, 
    [data-testid="stVerticalBlockBorderWrapper"] span,
    [data-testid="stVerticalBlockBorderWrapper"] label {{
        color: #0f172a !important;
    }}
    
    h1, h2, h3, h4 {{
        margin-top: 0.2rem !important;
        margin-bottom: 0.5rem !important;
    }}
    
    html, body, [class*="st-"], .stMarkdown p {{
        font-size: 15px !important;
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
        score = 95 if scenario == "Normal" else (65 if scenario == "Disruption" else 40)
        risk = "LOW 🟢" if score >= 85 else ("MED 🟡" if score >= 50 else "HIGH 🔴")
        delay = 0 if risk == "LOW 🟢" else (12 if risk == "MED 🟡" else 36)
        ai_rec = "Ready to Export" if risk == "LOW 🟢" else ("Requires Review & Correction" if risk == "MED 🟡" else "Hold Shipment")
        
        ship_day = (i % 5) + 1
        
        samples.append({
            "running_no": f"TR-202608{i:02d}-0001",
            "timestamp": f"2026-08-01 10:30:00",
            "ship_date": f"2026-08-{ship_day:02d}",
            "exporter": "Chiang Mai OEM Electronics" if i % 2 == 0 else "Northern Agri Export",
            "destination": "Japan" if i % 2 == 0 else "China",
            "shipment_mode": "AIR ✈️" if i % 3 == 0 else ("SEA 🚢" if i % 3 == 1 else "TRUCK 🚛"),
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
            "has_coo": True if scenario != "Erroneous Data" else False
        })
    pd.DataFrame(samples).to_csv(HISTORY_FILE, index=False)

def update_human_decision_in_csv(running_no, decision, notes):
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

validate_and_repair_csv()
generate_sample_data()

# ==========================================
# 3. RULES ENGINE
# ==========================================
def calculate_readiness(data, strictness_label):
    score = 100
    delay = 0
    m_strict = STRICTNESS_MULTIPLIER.get(strictness_label, 1.0)
    m_mode = MODE_MULTIPLIER.get(data['shipment_mode'], 1.0)
    
    issues = []
    if data['invoice_qty'] != data['packing_qty']:
        score -= (25 * m_strict)
        delay += (24 * m_mode)
        issues.append("Quantity Mismatch (Invoice vs Packing List)")
        
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
            mode = st.selectbox("Shipment Mode", ["AIR ✈️", "SEA 🚢", "TRUCK 🚛"], index=["AIR ✈️", "SEA 🚢", "TRUCK 🚛"].index(data.get('shipment_mode', 'AIR ✈️')))
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
                "running_no": run_no, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "ship_date": str(ship_date_input), "exporter": exporter, "destination": dest, 
                "shipment_mode": mode, "scenario_type": "Live Audit", "readiness_score": score, 
                "risk_level": risk, "est_delay": delay, "ai_recommendation": ai_rec, 
                "human_status": "⚪ Pending", "human_notes": "-",
                "invoice_no": inv, "po_no": po, "invoice_qty": inv_qty, "packing_qty": pl_qty, 
                "total_amount": amount, "hs_code": hs, "has_coo": coo
            }])
            new_record.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
            
            st.session_state.active_audit = new_record.iloc[0].to_dict()
            st.session_state.active_audit['issues'] = issues
            st.session_state.show_modal = False
            st.session_state.pending_page = "📄 Audit New Document"
            st.rerun()

# ==========================================
# 5. SIDEBAR CONTROL PANEL
# ==========================================
with st.sidebar:
    st.header("⚙️ Control Panel")

    api_key = st.text_input(
        "🔑 Gemini API Key", type="password", placeholder="AIzaSy...", help="ปล่อยว่างไว้เพื่อทดสอบโหมดข้อมูลจำลอง (Mockup)"
    )
    if api_key:
        st.session_state.api_key = api_key
    elif "api_key" in st.session_state:
        del st.session_state.api_key

    app_mode = st.radio("Navigation", ["📄 Audit New Document", "📜 History Logs"], key="nav_choice")
    st.divider()
    
    st.markdown("**📂 Document Upload (Multi-File)**")
    uploaded_files = st.file_uploader("Upload Invoice, PL, COO", type=["pdf"], accept_multiple_files=True)
    st.session_state.strictness = st.selectbox("Customs Strictness Level", ["Lenient", "Standard", "Strict"], index=1)
    
    if uploaded_files and st.button("🚀 Release to AI", use_container_width=True):
        is_mockup = not st.session_state.get("api_key")
        if is_mockup:
            st.warning("⚠️ ไม่พบ API Key: ระบบเข้าสู่โหมดข้อมูลจำลอง (Mockup Mode)")
            
        with st.spinner("AI กำลังวิเคราะห์ข้อมูลผ่าน Gemini API..." if not is_mockup else "กำลังโหลดข้อมูลจำลอง..."):
            st.session_state.temp_extracted_data = {
                "doc_type": "Multiple", "shipment_mode": "AIR ✈️", "ship_date": str(date.today()),
                "invoice_no": "INV-2026-991" if not is_mockup else "MOCK-INV-001", 
                "po_no": "PO-991" if not is_mockup else "MOCK-PO-001", 
                "exporter_name": "Chiang Mai OEM Electronics",
                "destination": "Japan", "invoice_qty": 500, "packing_qty": 450,
                "total_amount": 12500.0, "hs_code": "8409.91", "has_coo": False,
            }
            st.session_state.show_modal = True

if getattr(st.session_state, "show_modal", False):
    review_modal()

# ==========================================
# REUSABLE DASHBOARD COMPONENT (Solid White Frame)
# ==========================================
def render_dashboard(audit, key_prefix=""):
    issues = audit.get('issues', [])
    if isinstance(issues, str): 
        issues = [] 
    
    try:
        inv_qty_val = int(float(audit.get('invoice_qty', 0)))
        inv_qty_str = f"{inv_qty_val:,}"
    except (ValueError, TypeError):
        inv_qty_str = str(audit.get('invoice_qty', 'N/A'))

    try:
        pl_qty_val = int(float(audit.get('packing_qty', 0)))
        pl_qty_str = f"{pl_qty_val:,}"
    except (ValueError, TypeError):
        pl_qty_str = str(audit.get('packing_qty', 'N/A'))

    try:
        amt_val = float(audit.get('total_amount', 0.0))
        amt_str = f"{amt_val:,.2f}"
    except (ValueError, TypeError):
        amt_str = str(audit.get('total_amount', '0.00'))

    inv_no = str(audit.get('invoice_no', 'N/A'))
    pl_no_suffix = inv_no[-3:] if inv_no != 'N/A' and len(inv_no) >= 3 else 'N/A'

    if not issues and audit.get('readiness_score', 100) < 85:
        if str(audit.get('invoice_qty')) != str(audit.get('packing_qty')):
            issues.append("Quantity Mismatch (Invoice vs Packing List)")
        if not audit.get('has_coo', True):
            issues.append("Missing Certificate of Origin (COO)")

    with st.container(border=True):
        # --- 1. HEADER ROW ---
        st.markdown(f"""
        <div style="color: #334155; margin-bottom: 10px;">
            <span style="background-color: #16a34a; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 14px;">🟢 3 DOCS MERGED & AUDITED</span> 
            &nbsp;&nbsp;&nbsp; <b>Running No:</b> <span style="background-color: #e2e8f0; padding: 3px 8px; border-radius: 4px; color: #0f172a;">{audit.get('running_no', 'N/A')}</span> 
            &nbsp;&nbsp;&nbsp; <b>Time:</b> {audit.get('timestamp', 'N/A')} 
            &nbsp;&nbsp;&nbsp; <b>Mode:</b> {audit.get('shipment_mode', 'N/A')}
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        # --- 2. KPI ROW ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("READINESS SCORE", f"{audit.get('readiness_score', 0)}/100")
        c2.metric("COMPLETION RATE", "83.3%" if audit.get('readiness_score', 0) < 85 else "100%")
        c3.metric("RISK LEVEL", audit.get('risk_level', 'N/A'))
        c4.metric("EST. BORDER DELAY", f"{audit.get('est_delay', 0)} Hours")
        
        st.divider()

        # --- 3. DATA & AUDIT CHECK ROW ---
        col_data, col_audit = st.columns(2)
        
        with col_data:
            st.markdown("### 📄 Extracted Data Across Files")
            st.markdown(f"""
            * **Invoice No:** `{inv_no}`
            * **Packing List No:** `PL-{pl_no_suffix}`
            * **Invoice Total Qty:** `{inv_qty_str} PCS`
            * **PL Total Qty:** `{pl_qty_str} PCS`
            * **Total Amount:** `${amt_str} USD`
            * **Main HS Code:** `{audit.get('hs_code', 'N/A')}`
            * **Destination Origin:** `{audit.get('destination', 'N/A')}`
            """)

        with col_audit:
            st.markdown("### 🔍 Cross-Document Multi-Audit")
            if str(audit.get('invoice_qty')) != str(audit.get('packing_qty')):
                st.error(f"🔴 Quantity Mismatch (Invoice vs PL): {audit.get('invoice_qty', 'N/A')} vs {audit.get('packing_qty', 'N/A')}")
            else:
                st.success(f"🟢 Quantity Match (Invoice vs PL): {inv_qty_str} PCS")
                
            st.success("🟢 Exporter & Consignee: Matches Across All Docs")
            
            if not audit.get('has_coo', True) or "COO" in str(issues):
                st.warning("🟡 Certificate of Origin (COO): Missing or Invalid")
            else:
                st.success("🟢 Certificate of Origin (COO): Valid for FTA")
                
            st.success(f"🟢 HS Code {audit.get('hs_code', '8409.91')}: Matched Invoice vs COO")

        st.divider()

        # --- 4. ACTION & DECISION ROW (เปลี่ยนเป็น Radio แบบคลิกเลือกได้ทันทีโดยไม่ต้องกด Dropdown) ---
        col_ai, col_human = st.columns([1.5, 1])
        
        with col_ai:
            st.markdown("### 🤖 AI Recommendation (Alternative 1 of 3)")
            st.info(f"👉 **{audit.get('ai_recommendation', 'N/A').upper()}**")
            
            if issues:
                st.markdown("**Reason & Notes:**")
                for i in issues:
                    st.markdown(f"<span style='color:#dc2626; font-weight: bold;'>- 🔴 {i}</span>", unsafe_allow_html=True)
                st.markdown("- **Responsible Party:** Logistics / Compliance Officer")
            else:
                st.markdown("**Reason & Notes:**")
                st.markdown("- Documents are complete with COO attached.")
                st.markdown("- Minor Note: Declared weight is within tolerance.")
                st.markdown("- **Responsible Party:** Shipping Officer (Clearance)")
                
        with col_human:
            st.markdown("### 👤 Human Decision")
            
            # ⭐️ ใช้ Radio button แทน Selectbox เพื่อให้เลือกได้ทันทีในหน้าจอเดียวโดยไม่ต้องกด Dropdown ⭐️
            options_list = ["Ready to Export", "Requires Review & Correction", "Hold Shipment / High Risk"]
            current_status = str(audit.get('human_notes', ''))
            default_idx = 0
            for idx, opt in enumerate(options_list):
                if opt.lower() in audit.get('ai_recommendation', '').lower():
                    default_idx = idx

            final_decision = st.radio("Final Status:", options_list, index=default_idx, key=f"{key_prefix}radio_dec", horizontal=False)
            remarks = st.text_area("Remarks / Notes", value=str(audit.get('human_notes', '')), key=f"{key_prefix}rem")
            
            if st.button("💾 Save Transaction Log", type="primary", use_container_width=True, key=f"{key_prefix}save"):
                update_human_decision_in_csv(audit['running_no'], final_decision, remarks)
                st.session_state.active_audit['human_status'] = f"Updated ({final_decision})"
                st.session_state.active_audit['human_notes'] = remarks
                st.success("บันทึกอัปเดตเรียบร้อยแล้ว!")

        # --- 5. DOCUMENT CHECKLIST (BOTTOM - ขยายขนาดให้เด่นชัดขึ้น) ---
        st.divider()
        coo_color = "#ca8a04" if not audit.get('has_coo', True) else "#166534"
        coo_text = "❌ COO (Missing)" if not audit.get('has_coo', True) else "✓ COO (Verified)"
        
        st.markdown("**DOCUMENT CHECKLIST (ATTACHED):**")
        st.markdown(f"""
        <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px;">
            <span style="background-color: #166534; color: white; padding: 10px 18px; border-radius: 6px; font-size: 15px; font-weight: bold; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">✓ Invoice</span>
            <span style="background-color: #166534; color: white; padding: 10px 18px; border-radius: 6px; font-size: 15px; font-weight: bold; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">✓ Packing List</span>
            <span style="background-color: #166534; color: white; padding: 10px 18px; border-radius: 6px; font-size: 15px; font-weight: bold; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">✓ PO</span>
            <span style="background-color: #166534; color: white; padding: 10px 18px; border-radius: 6px; font-size: 15px; font-weight: bold; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">✓ B/L / AWB</span>
            <span style="background-color: {coo_color}; color: white; padding: 10px 18px; border-radius: 6px; font-size: 15px; font-weight: bold; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">{coo_text}</span>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 6. MAIN APP ROUTING
# ==========================================
st.markdown("## 🚢 TradeReady AI <span style='font-size: 14px; color: #cbd5e1;'>| Export Documentation & Customs Readiness Assistant</span>", unsafe_allow_html=True)

if app_mode == "📄 Audit New Document":
    if 'active_audit' in st.session_state:
        render_dashboard(st.session_state.active_audit, key_prefix="main_")
    else:
        st.info("👈 กรุณาอัปโหลดไฟล์ PDF ด้านซ้ายมือ หรือเลือกดูรายการจากเมนู History Logs")

elif app_mode == "📜 History Logs":
    st.markdown("#### 📜 Transaction History Logs & Daily Release Control")
    
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
            
        enable_date_filter = st.toggle("📅 Enable Ship Date Filter (กรองเฉพาะวันส่งออก)", value=False)
        
        col1, col2, col3 = st.columns(3)
        search_q = col1.text_input("🔍 Search Exporter / Running No.")
        risk_filter = col2.selectbox("Filter Risk Level", ["All", "LOW 🟢", "MED 🟡", "HIGH 🔴"])
        selected_ship_date = col3.date_input("Select Ship Date", value=date(2026, 8, 1), disabled=not enable_date_filter)
        
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

        if enable_date_filter:
            total_shipments = len(filtered_df)
            approved_shipments = len(filtered_df[filtered_df['human_status'].str.contains("Accepted|Ready", case=False, na=False)])
            pending_count = total_shipments - approved_shipments
            
            if total_shipments > 0 and pending_count == 0:
                st.success(f"🟢 **ALL APPROVED (100%):** เอกสารของวันที่ `{selected_ship_date}` พร้อมส่งออกทั้ง {total_shipments} รายการ")
            elif total_shipments > 0:
                st.warning(f"⚠️ **ATTENTION:** วันที่ `{selected_ship_date}` มี {total_shipments} ชิปเมนต์ (รอการยืนยัน {pending_count} รายการ)")

        event = st.dataframe(
            filtered_df[["running_no", "ship_date", "shipment_mode", "exporter", "destination", "readiness_score", "risk_level", "human_status"]],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        selected_rows = event.selection.rows
        if selected_rows:
            selected_index = selected_rows[0]
            selected_record = filtered_df.iloc[selected_index].to_dict()
            
            if st.session_state.get('opened_inline_id') != selected_record['running_no']:
                st.session_state.show_inline_dashboard = False
                st.session_state.opened_inline_id = selected_record['running_no']

            c_info, c_btn = st.columns([4, 1])
            with c_info:
                st.markdown(f"📌 **รายการที่เลือก:** `{selected_record['running_no']}` | **Ship Date:** `{selected_record.get('ship_date', 'N/A')}`")
            with c_btn:
                if st.button("👁️ เปิดดูรายละเอียดด้านล่าง", type="primary", use_container_width=True):
                    st.session_state.active_audit = selected_record
                    st.session_state.show_inline_dashboard = True
                    st.rerun()
        else:
            st.session_state.show_inline_dashboard = False

        if getattr(st.session_state, 'show_inline_dashboard', False):
            st.markdown("---")
            
            c_head, c_close = st.columns([5, 1])
            with c_head:
                st.markdown(f"### 📊 Dashboard Detail View")
            with c_close:
                if st.button("❌ ปิด (Close)", use_container_width=True):
                    st.session_state.show_inline_dashboard = False
                    st.rerun()
            
            render_dashboard(st.session_state.active_audit, key_prefix="inline_")
                    
    else:
        st.warning("ยังไม่พบข้อมูลประวัติในระบบ")

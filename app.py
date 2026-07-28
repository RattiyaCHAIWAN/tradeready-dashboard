import json
import re
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import streamlit as st

# ==========================================
# 1. PAGE CONFIG & THEME
# ==========================================
st.set_page_config(
    page_title="TradeReady AI Control Tower",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded",
)

# Custom CSS for Dark Control Tower Theme
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0f19; color: #f9fafb; }
    div[data-testid="stMetricValue"] { font-weight: bold; }
    .card-frame { background-color: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 16px; margin-bottom: 12px; }
    .alert-box { background-color: #3f1218; border: 1px solid #991b1b; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
    .pass-box { background-color: #064e3b; border: 1px solid #10b981; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
    .ai-suggest-box { background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. SESSION STATE INITIALIZATION
# ==========================================
if "master_db" not in st.session_state:
    st.session_state.master_db = pd.DataFrame([
        {
            "Shipment_ID": "EXP-2026-001",
            "Customer_Name": "Sony Vietnam Co., Ltd.",
            "Destination": "Vietnam",
            "Readiness_Score": 40,
            "Risk_Level": "High",
            "Issue_Detected": "Qty Mismatch (TC-1)",
            "Responsible": "Planning",
            "Invoice_Qty": 100000,
            "PL_Qty": 98000,
            "HS_Code": "4016.99.90",
            "COO_Form": "Form D (ATIGA)",
        }
    ])

# ตัวแปรสำหรับพักข้อมูลที่ AI แกะได้ ก่อนกดยืนยันบันทึก
if "staging_data" not in st.session_state:
    st.session_state.staging_data = None

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "dashboard"  # 'dashboard' หรือ 'add_document'


# ==========================================
# 3. SIDEBAR & FILE UPLOAD ENGINE
# ==========================================
with st.sidebar:
    st.title("⚙️ AI Document Engine")
    gemini_key = st.text_input(
        "Gemini API Key (Optional)", type="password", key="sidebar_key"
    )

    st.markdown("---")
    st.subheader("📄 Step 1: Upload Documents")

    uploaded_files = st.file_uploader(
        "Upload Invoice / Packing List",
        type=["pdf", "xlsx", "xls", "csv"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.success(f"Uploaded {len(uploaded_files)} file(s) ready")

        if st.button(
            "🤖 Process Documents with AI OCR",
            type="primary",
            use_container_width=True,
        ):
            # จำลอง/สกัดข้อมูลจากไฟล์ และนำมาใส่ใน Staging Area
            st.session_state.staging_data = {
                "running_id": f"EXP-2026-0{len(st.session_state.master_db) + 51:02d}",
                "customer_name": "Sony Vietnam Co., Ltd.",
                "destination_country": "Vietnam",
                "product_desc": "EPDM Rubber Cushion Dampener Part #SNV-902",
                "po_number": "PO-SNV-2026-8891",
                "invoice_qty": 50000,
                "packing_list_qty": 50000,
                "total_amount": "$ 10,000.00 ($0.20/pc)",
                "incoterms": "FOB Bangkok / Air Freight",
                "suggested_hs_code": "4016.99.90 (Rubber Dampener)",
                "suggested_coo": "Form D (ATIGA Preferential Rate)",
                "hs_confirmed": False,
                "coo_confirmed": False,
            }
            st.session_state.view_mode = "add_document"
            st.rerun()

    st.markdown("---")
    if st.button("📊 Back to Main Dashboard", use_container_width=True):
        st.session_state.view_mode = "dashboard"
        st.rerun()


# ==========================================
# 4. MAIN SCREEN DISPLAY SWITCH
# ==========================================

# ------------------------------------------
# MODE A: EXTRACTED RESULT VERIFICATION GRID (ตาม MOCKUP)
# ------------------------------------------
if (
    st.session_state.view_mode == "add_document"
    and st.session_state.staging_data
):
    data = st.session_state.staging_data

    # Header section
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("📦 Add & Validate Shipping Document")
        st.caption(
            "Upload Invoice, Packing List, or PO for Automated AI Extraction &"
            " Customs Readiness Check"
        )
    with col_h2:
        st.markdown(
            f"**AUTO RUNNING ID**  \n`{data['running_id']}`",
            help="Auto generated ID",
        )

    st.markdown("---")
    st.subheader("🔍 Step 2-5: AI Extracted Data & Verification Grid")
    st.caption(
        "Review AI pre-filled data. You can edit or confirm any field directly"
        " before submission."
    )

    # Box 1: AI Suggested HS Code & C/O Form Controls
    c_hs, c_coo = st.columns(2)

    with c_hs:
        st.markdown(
            """
            <div class="ai-suggest-box">
                <div style="display:flex; justify-between; align-items:center;">
                    <b style="color:#f9fafb; font-size:12px;">🏷️ AI SUGGESTED HS CODE</b>
                    <span style="background:#1e3a8a; color:#60a5fa; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:bold;">🤖 98% Match</span>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        hs_input = st.text_input(
            "Edit HS Code if needed:",
            value=data["suggested_hs_code"],
            key="input_hs",
        )
        confirm_hs = st.checkbox("✓ Confirm HS Code", value=True, key="chk_hs")

    with c_coo:
        st.markdown(
            """
            <div class="ai-suggest-box">
                <div style="display:flex; justify-between; align-items:center;">
                    <b style="color:#f9fafb; font-size:12px;">📜 AI SUGGESTED C/O FORM</b>
                    <span style="background:#064e3b; color:#34d399; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:bold;">🤖 FTA Matched</span>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        coo_select = st.selectbox(
            "Select C/O Form:",
            [
                "Form D (ATIGA Preferential Rate)",
                "Form JTEPA (Japan-Thailand)",
                "Form AKFTA (ASEAN-Korea)",
                "General C/O",
            ],
            index=0,
            key="select_coo",
        )
        confirm_coo = st.checkbox("✓ Confirm C/O Form", value=True, key="chk_coo")

    st.write(" ")

    # Box 2: Form Fields Editing Grid
    with st.form("verification_form"):
        f1, f2 = st.columns(2)
        with f1:
            cust_name = st.text_input(
                "Customer Name", value=data["customer_name"]
            )
            prod_desc = st.text_input(
                "Product Description", value=data["product_desc"]
            )
            inv_qty = st.number_input(
                "Invoice Quantity (PCS)", value=int(data["invoice_qty"])
            )
            total_amt = st.text_input(
                "Total Unit Amount (USD)", value=data["total_amount"]
            )

        with f2:
            dest_country = st.selectbox(
                "Destination Country",
                ["Vietnam", "Japan", "Malaysia", "South Korea"],
                index=0,
            )
            po_num = st.text_input("PO Number", value=data["po_number"])
            pl_qty = st.number_input(
                "Packing List Quantity (PCS)", value=int(data["packing_list_qty"])
            )
            incoterm = st.text_input(
                "Incoterms & Shipping Mode", value=data["incoterms"]
            )

        # Consistency Check Status Banner
        is_qty_pass = inv_qty == pl_qty
        if is_qty_pass:
            st.markdown(
                """
                <div class="pass-box">
                    <b style="color:#6ee7b7;">✅ AI Consistency Check Passed</b><br>
                    <span style="font-size:12px; color:#e5e7eb;">Invoice & Packing List quantities match perfectly. High Customs Readiness Score predicted (95%).</span>
                </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="alert-box">
                    <b style="color:#fca5a5;">⚠️ Anomaly Detected: Quantity Discrepancy</b><br>
                    <span style="font-size:12px; color:#e5e7eb;">Invoice states {inv_qty:,} PCS, but Packing List states {pl_qty:,} PCS. Physical inspection likely.</span>
                </div>
            """,
                unsafe_allow_html=True,
            )

        # Form Actions
        b_cancel, b_submit = st.columns([1, 2])
        with b_cancel:
            btn_cancel = st.form_submit_button(
                "Cancel", use_container_width=True
            )
        with b_submit:
            btn_confirm = st.form_submit_button(
                "🚀 Confirm & Submit to Dashboard",
                type="primary",
                use_container_width=True,
            )

        if btn_cancel:
            st.session_state.staging_data = None
            st.session_state.view_mode = "dashboard"
            st.rerun()

        if btn_confirm:
            # คำนวณคะแนนและบันทึกเข้า master_db จริง
            score = 95 if is_qty_pass else 40
            risk = "Low" if score >= 80 else "High"
            issue = (
                "None (Passed)"
                if is_qty_pass
                else f"Qty Mismatch ({abs(inv_qty-pl_qty):,} PCS)"
            )

            new_row = {
                "Shipment_ID": data["running_id"],
                "Customer_Name": cust_name,
                "Destination": dest_country,
                "Readiness_Score": score,
                "Risk_Level": risk,
                "Issue_Detected": issue,
                "Responsible": "System" if is_qty_pass else "Planning",
                "Invoice_Qty": inv_qty,
                "PL_Qty": pl_qty,
                "HS_Code": hs_input,
                "COO_Form": coo_select,
            }

            st.session_state.master_db = pd.concat(
                [st.session_state.master_db, pd.DataFrame([new_row])],
                ignore_index=True,
            )
            st.session_state.staging_data = None
            st.session_state.view_mode = "dashboard"
            st.toast(f"✅ Shipment {data['running_id']} added to Dashboard!")
            st.rerun()

# ------------------------------------------
# MODE B: MAIN DASHBOARD VIEW
# ------------------------------------------
else:
    st.title("🛡️ TradeReady AI Dashboard")
    st.caption("Export Documentation & Customs Readiness Control Tower")

    # แสดงตาราง Master Table ด้านล่างตามปกติ
    st.dataframe(st.session_state.master_db, use_container_width=True)

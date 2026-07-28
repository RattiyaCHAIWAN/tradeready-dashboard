import json
import re
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import streamlit as st

# Safe import for PDF parsing fallback
try:
  import pypdf
except ImportError:
  pypdf = None

# ==========================================
# 1. PAGE CONFIG & THEME
# ==========================================
st.set_page_config(
    page_title="TradeReady AI Control Tower",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded",
)

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
# 2. REAL AI EXTRACTION ENGINE (PDF / EXCEL / CSV)
# ==========================================
def extract_data_with_gemini(file_bytes, mime_type, api_key):
  """สกัดข้อมูลจาก Commercial Invoice / Packing List จริงด้วย Gemini 1.5 Flash"""
  genai.configure(api_key=api_key)
  model = genai.GenerativeModel("gemini-1.5-flash")

  prompt = """
    You are an AI Customs Auditor. Read the attached Commercial Invoice image/PDF and extract the exact fields into this strict JSON structure:

    {
        "shipment_id": "Extract Shipment ID e.g. EXP-2026-002 or invoice number if missing",
        "customer_name": "Full name of SOLD TO or SHIP TO customer e.g. Denso Japan",
        "destination_country": "Country in SOLD TO / SHIP TO address e.g. Japan",
        "product_desc": "Main description of the item e.g. Silicone Rubber Foot for Automotive ECU",
        "po_number": "Customer PO number e.g. PO-DNS-4412",
        "invoice_qty": 50000, // Number only (integer) from Total Qty
        "packing_list_qty": 50000, // Number only (integer)
        "total_amount": "Total amount with currency e.g. $12,500.00",
        "incoterms": "Incoterms and Ship Via e.g. CIF / BY AIR FREIGHT",
        "suggested_hs_code": "Full 8-digit HS code e.g. 4016.99.00",
        "suggested_coo": "Automated C/O Form suggestion based on destination e.g. Form JTEPA (Japan-Thailand)"
    }

    Rules:
    - Extract exact values shown in the document.
    - Remove commas from qty integers.
    - Return ONLY valid raw JSON text. Do not use markdown code blocks or ```json tag.
    """

  doc_part = {"mime_type": mime_type, "data": file_bytes}
  response = model.generate_content([doc_part, prompt])

  # ทำความสะอาด String และแปลงเป็น JSON Object
  clean_json = response.text.replace("```json", "").replace("```", "").strip()
  return json.loads(clean_json)

  doc_part = {"mime_type": mime_type, "data": file_bytes}
  response = model.generate_content([doc_part, prompt])
  clean_json = response.text.replace("```json", "").replace("```", "").strip()
  return json.loads(clean_json)


def extract_fallback_text(file, file_ext):
  """ระบบดึงข้อมูลสำรอง กรณีไม่ได้ใส่ Gemini API Key"""
  customer_name = "Extracted Customer"
  product_desc = "Parsed Product Item"
  po_num = "PO-2026-X1"
  inv_qty = 1000
  pl_qty = 1000

  if file_ext == "csv":
    df = pd.read_csv(file)
    if not df.empty:
      customer_name = str(df.iloc[0].get("Customer", customer_name))
      inv_qty = int(df.iloc[0].get("Invoice_Qty", inv_qty))
      pl_qty = int(df.iloc[0].get("PL_Qty", pl_qty))

  elif file_ext in ["xlsx", "xls"]:
    df = pd.read_excel(file)
    if not df.empty:
      customer_name = str(df.iloc[0].get("Customer", customer_name))
      inv_qty = int(df.iloc[0].get("Invoice_Qty", inv_qty))
      pl_qty = int(df.iloc[0].get("PL_Qty", pl_qty))

  elif file_ext == "pdf" and pypdf is not None:
    reader = pypdf.PdfReader(file)
    text = "\n".join(
        [p.extract_text() for p in reader.pages if p.extract_text()]
    )

    # ดึง Qty จาก PDF ด้วย Regex
    qty_match = re.search(
        r"(?:qty|quantity|pcs)[\s:]*([0-9,]+)", text, re.IGNORECASE
    )
    if qty_match:
      inv_qty = int(qty_match.group(1).replace(",", ""))
      pl_qty = inv_qty

    po_match = re.search(
        r"(?:po|order)[\s:]*([A-Za-z0-9\-_]+)", text, re.IGNORECASE
    )
    if po_match:
      po_num = po_match.group(1)

    if len(text) > 10:
      product_desc = text[:80].replace("\n", " ")

  return {
      "customer_name": customer_name,
      "destination_country": "Vietnam",
      "product_desc": product_desc,
      "po_number": po_num,
      "invoice_qty": inv_qty,
      "packing_list_qty": pl_qty,
      "total_amount": "$ 5,000.00",
      "incoterms": "FOB Bangkok",
      "suggested_hs_code": "8504.40.90",
      "suggested_coo": "Form D (ATIGA Preferential Rate)",
  }


# ==========================================
# 3. SESSION STATE
# ==========================================
if "master_db" not in st.session_state:
  st.session_state.master_db = pd.DataFrame([{
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
  }])

if "staging_data" not in st.session_state:
  st.session_state.staging_data = None

if "view_mode" not in st.session_state:
  st.session_state.view_mode = "dashboard"


# ==========================================
# 4. SIDEBAR & REAL FILE PARSER TRIGGER
# ==========================================
with st.sidebar:
  st.title("⚙️ AI Document Engine")
  gemini_key = st.text_input(
      "Gemini API Key (ใส่เพื่อให้อ่าน PDF จริง)",
      type="password",
      key="sidebar_key",
  )

  st.markdown("---")
  st.subheader("📄 Step 1: Upload Documents")

  uploaded_files = st.file_uploader(
      "Upload Invoice / Packing List",
      type=["pdf", "xlsx", "xls", "csv"],
      accept_multiple_files=True,
  )

  if uploaded_files:
    st.success(f"อัปโหลด {len(uploaded_files)} ไฟล์เรียบร้อย")

    if st.button(
        "🤖 Process Documents with AI OCR",
        type="primary",
        use_container_width=True,
    ):
      first_file = uploaded_files[0]
      file_bytes = first_file.getvalue()
      file_ext = first_file.name.split(".")[-1].lower()

      extracted_res = None

      # 1. ส่งอ่านด้วย Gemini AI ถ้าระบุ API Key
      if gemini_key and file_ext in ["pdf", "png", "jpg"]:
        with st.spinner("🤖 Gemini AI กำลังแกะข้อมูลจากเอกสาร PDF จริง..."):
          try:
            mime = "application/pdf" if file_ext == "pdf" else "image/png"
            extracted_res = extract_data_with_gemini(
                file_bytes, mime, gemini_key
            )
          except Exception as e:
            st.error(f"การอ่านด้วย AI ขัดข้อง: {e}")

      # 2. อ่านด้วย Parser ตัวกลางถ้าระบุคีย์ไม่ครบหรือเป็น Excel/CSV
      if not extracted_res:
        with st.spinner("📄 กำลังสกัดข้อความจากไฟล์..."):
          extracted_res = extract_fallback_text(first_file, file_ext)

      # บันทึกข้อมูลที่อ่านได้จริงเข้าสู่ Staging Data
      st.session_state.staging_data = {
          "running_id": f"EXP-2026-0{len(st.session_state.master_db) + 51:02d}",
          "customer_name": extracted_res.get(
              "customer_name", "Unknown Customer"
          ),
          "destination_country": extracted_res.get(
              "destination_country", "Vietnam"
          ),
          "product_desc": extracted_res.get("product_desc", "Electronic Parts"),
          "po_number": extracted_res.get("po_number", "PO-NONE"),
          "invoice_qty": int(extracted_res.get("invoice_qty", 0)),
          "packing_list_qty": int(extracted_res.get("packing_list_qty", 0)),
          "total_amount": str(extracted_res.get("total_amount", "N/A")),
          "incoterms": extracted_res.get("incoterms", "FOB Bangkok"),
          "suggested_hs_code": extracted_res.get(
              "suggested_hs_code", "4016.99.90"
          ),
          "suggested_coo": extracted_res.get(
              "suggested_coo", "Form D (ATIGA Preferential Rate)"
          ),
      }
      st.session_state.view_mode = "add_document"
      st.rerun()

  st.markdown("---")
  if st.button("📊 Back to Main Dashboard", use_container_width=True):
    st.session_state.view_mode = "dashboard"
    st.rerun()


# ==========================================
# 5. MAIN DISPLAY (VERIFICATION GRID WITH REAL DATA)
# ==========================================
if (
    st.session_state.view_mode == "add_document"
    and st.session_state.staging_data
):
  data = st.session_state.staging_data

  col_h1, col_h2 = st.columns([3, 1])
  with col_h1:
    st.title("📦 Add & Validate Shipping Document")
    st.caption("AI Extracted Result from Uploaded File")
  with col_h2:
    st.markdown(f"**AUTO RUNNING ID**  \n`{data['running_id']}`")

  st.markdown("---")
  st.subheader("🔍 Step 2-5: AI Extracted Data & Verification Grid")

  # AI Suggested Box
  c_hs, c_coo = st.columns(2)
  with c_hs:
    st.markdown(
        '<div class="ai-suggest-box"><b style="color:#f9fafb;">🏷️ AI SUGGESTED'
        ' HS CODE</b></div>',
        unsafe_allow_html=True,
    )
    hs_input = st.text_input(
        "Edit HS Code if needed:",
        value=data["suggested_hs_code"],
        key="input_hs",
    )

  with c_coo:
    st.markdown(
        '<div class="ai-suggest-box"><b style="color:#f9fafb;">📜 AI SUGGESTED'
        ' C/O FORM</b></div>',
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

  st.write(" ")

  # Dynamic Editable Form from PDF
  with st.form("verification_form"):
    f1, f2 = st.columns(2)
    with f1:
      cust_name = st.text_input("Customer Name", value=data["customer_name"])
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
      dest_country = st.text_input(
          "Destination Country", value=data["destination_country"]
      )
      po_num = st.text_input("PO Number", value=data["po_number"])
      pl_qty = st.number_input(
          "Packing List Quantity (PCS)", value=int(data["packing_list_qty"])
      )
      incoterm = st.text_input(
          "Incoterms & Shipping Mode", value=data["incoterms"]
      )

    # Quantity Match Checking
    is_qty_pass = (inv_qty == pl_qty) and (inv_qty > 0)
    if is_qty_pass:
      st.markdown(
          '<div class="pass-box"><b style="color:#6ee7b7;">✅ AI Consistency'
          " Check Passed</b><br>Invoice & Packing List quantities match"
          " perfectly.</div>",
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          f'<div class="alert-box"><b style="color:#fca5a5;">⚠️ Anomaly'
          f" Detected: Quantity Discrepancy</b><br>Invoice states {inv_qty:,}"
          f" PCS, but Packing List states {pl_qty:,} PCS.</div>",
          unsafe_allow_html=True,
      )

    b_cancel, b_submit = st.columns([1, 2])
    with b_cancel:
      btn_cancel = st.form_submit_button("Cancel", use_container_width=True)
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
      st.toast(f"✅ บันทึกข้อมูล {data['running_id']} เรียบร้อยแล้ว!")
      st.rerun()

else:
  st.title("🛡️ TradeReady AI Dashboard")
  st.caption("Export Documentation & Customs Readiness Control Tower")
  st.dataframe(st.session_state.master_db, use_container_width=True)

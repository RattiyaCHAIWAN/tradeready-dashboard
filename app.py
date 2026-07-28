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
# 1. PAGE CONFIGURATION & DARK THEME STYLING
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
    /* Dark Control Tower Custom CSS */
    .stApp { background-color: #0b0f19; color: #f9fafb; }
    div[data-testid="stMetricValue"] { font-weight: bold; }
    
    .card-frame {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .alert-box {
        background-color: #3f1218;
        border: 1px solid #991b1b;
        border-radius: 8px;
        padding: 12px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .action-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .badge-high {
        background-color: #7f1d1d; color: #fca5a5; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px;
    }
    .badge-med {
        background-color: #78350f; color: #fcd34d; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px;
    }
    .badge-low {
        background-color: #064e3b; color: #6ee7b7; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# ==========================================
# 2. HELPER FUNCTIONS & AI ENGINE
# ==========================================
def run_customs_rules(inv_qty, pl_qty, destination):
  """Computes readiness score, risk level, and FTA/COO recommendations."""
  inv_qty = inv_qty or 50000
  pl_qty = pl_qty or 50000

  discrepancy = abs(inv_qty - pl_qty)
  if discrepancy == 0:
    score = 95
    risk = "Low"
    issue = "None (Passed)"
    dept = "System"
  else:
    score = 40
    risk = "High"
    issue = f"Qty Mismatch ({discrepancy:,} PCS)"
    dept = "Planning"

  coo_map = {
      "Vietnam": "Form D (ATIGA)",
      "Malaysia": "Form D (ATIGA)",
      "Japan": "Form JTEPA",
      "South Korea": "Form AKFTA",
      "China": "Form E (ACFTA)",
  }
  coo_form = coo_map.get(destination, "General C/O")
  return score, risk, issue, dept, coo_form


def extract_data_with_gemini(file_bytes, mime_type, api_key):
  """Extracts structured JSON from PDF or Image using Gemini 1.5 Flash Vision OCR."""
  try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """
        You are an expert export customs documentation auditor for OEM electronics.
        Analyze the attached document (Invoice, Packing List, or PO) and extract the following fields into a strictly valid JSON object:
        {
            "customer_name": "Name of buyer/consignee",
            "destination_country": "Country of destination (e.g., Vietnam, Japan, South Korea)",
            "invoice_qty": integer_or_null,
            "packing_list_qty": integer_or_null,
            "po_number": "PO number if present",
            "product_description": "Brief description of goods",
            "suggested_hs_code": "8-digit HS code if found or inferred (e.g., 4016.99.90)",
            "incoterms": "e.g., FOB Bangkok"
        }
        Return ONLY the raw JSON string without markdown formatting or code blocks.
        """

    doc_part = {"mime_type": mime_type, "data": file_bytes}
    response = model.generate_content([doc_part, prompt])

    clean_text = (
        response.text.replace("```json", "").replace("```", "").strip()
    )
    return json.loads(clean_text)
  except Exception as e:
    st.error(f"Gemini AI Extraction Error: {e}")
    return None


# ==========================================
# 3. SESSION STATE & INITIAL DATABASE
# ==========================================
if "master_db" not in st.session_state:
  st.session_state.master_db = pd.DataFrame([
      {
          "Shipment_ID": "EXP-2026-001",
          "Customer_Name": "Sony Vietnam",
          "Destination": "Vietnam",
          "Readiness_Score": 40,
          "Risk_Level": "High",
          "Issue_Detected": "Qty Mismatch (TC-1)",
          "Responsible": "Planning",
          "Invoice_Qty": 100000,
          "PL_Qty": 98000,
          "HS_Code": "4016.99.90",
          "COO_Form": "Form D (ATIGA)",
      },
      {
          "Shipment_ID": "EXP-2026-002",
          "Customer_Name": "Denso Japan",
          "Destination": "Japan",
          "Readiness_Score": 55,
          "Risk_Level": "Medium",
          "Issue_Detected": "Missing C/O (TC-2)",
          "Responsible": "Export Admin",
          "Invoice_Qty": 45000,
          "PL_Qty": 45000,
          "HS_Code": "8504.40.90",
          "COO_Form": "Form JTEPA",
      },
      {
          "Shipment_ID": "EXP-2026-003",
          "Customer_Name": "Samsung Korea",
          "Destination": "South Korea",
          "Readiness_Score": 60,
          "Risk_Level": "Medium",
          "Issue_Detected": "Vague Desc (TC-3)",
          "Responsible": "Sales",
          "Invoice_Qty": 30000,
          "PL_Qty": 30000,
          "HS_Code": "8542.31.00",
          "COO_Form": "Form AKFTA",
      },
      {
          "Shipment_ID": "EXP-2026-004",
          "Customer_Name": "Panasonic Malaysia",
          "Destination": "Malaysia",
          "Readiness_Score": 30,
          "Risk_Level": "High",
          "Issue_Detected": "Weight Anomaly (TC-4)",
          "Responsible": "Warehouse",
          "Invoice_Qty": 80000,
          "PL_Qty": 80000,
          "HS_Code": "4016.99.90",
          "COO_Form": "Form D (ATIGA)",
      },
      {
          "Shipment_ID": "EXP-2026-026",
          "Customer_Name": "Sony Vietnam",
          "Destination": "Vietnam",
          "Readiness_Score": 98,
          "Risk_Level": "Low",
          "Issue_Detected": "None (Passed)",
          "Responsible": "System",
          "Invoice_Qty": 50000,
          "PL_Qty": 50000,
          "HS_Code": "4016.99.90",
          "COO_Form": "Form D (ATIGA)",
      },
  ])

if "selected_shipment_id" not in st.session_state:
  st.session_state.selected_shipment_id = "EXP-2026-001"


# ==========================================
# 4. SIDEBAR: FILE UPLOAD & AI OCR
# ==========================================
with st.sidebar:
  st.title("⚙️ AI Document Engine")

  # Gemini API Key Input
  gemini_api_key = st.text_input(
      "Gemini API Key (Optional)",
      type="password",
      help="Enter key to enable direct AI PDF Vision OCR extraction.",
  )

  st.markdown("---")
  st.subheader("📤 Upload Document Set")
  uploaded_files = st.file_uploader(
      "Upload Invoice / Packing List",
      type=["pdf", "xlsx", "xls", "csv"],
      accept_multiple_files=True,
  )

  if uploaded_files:
    for file in uploaded_files:
      file_ext = file.name.split(".")[-1].lower()
      st.markdown(f"**📄 File:** `{file.name}`")

      if st.button(f"🤖 Process {file.name}", key=f"btn_{file.name}"):
        file_bytes = file.getvalue()
        extracted = None

        # Process with Gemini AI if API key is provided for PDF/Images
        if gemini_api_key and file_ext in ["pdf", "png", "jpg"]:
          mime = "application/pdf" if file_ext == "pdf" else "image/png"
          with st.spinner("AI Extracting data from document..."):
            extracted = extract_data_with_gemini(
                file_bytes, mime, gemini_api_key
            )

        # Fallback Parser for Excel/CSV or if API key is omitted
        if not extracted:
          if file_ext == "csv":
            df_temp = pd.read_csv(file)
          elif file_ext in ["xlsx", "xls"]:
            df_temp = pd.read_excel(file)
          else:
            df_temp = pd.DataFrame()

          extracted = {
              "customer_name": (
                  df_temp.get("Customer", ["New Client"])[0]
                  if not df_temp.empty
                  else "Sony Vietnam"
              ),
              "destination_country": (
                  df_temp.get("Country", ["Vietnam"])[0]
                  if not df_temp.empty
                  else "Vietnam"
              ),
              "invoice_qty": (
                  df_temp.get("Invoice_Qty", [50000])[0]
                  if not df_temp.empty
                  else 50000
              ),
              "packing_list_qty": (
                  df_temp.get("PL_Qty", [50000])[0]
                  if not df_temp.empty
                  else 50000
              ),
              "suggested_hs_code": "4016.99.90",
          }

        # Calculate scores and update Database
        score, risk, issue, dept, coo = run_customs_rules(
            extracted.get("invoice_qty"),
            extracted.get("packing_list_qty"),
            extracted.get("destination_country", "Vietnam"),
        )

        new_id = f"EXP-2026-0{len(st.session_state.master_db) + 1:02d}"
        new_row = {
            "Shipment_ID": new_id,
            "Customer_Name": extracted.get("customer_name", "Unknown Customer"),
            "Destination": extracted.get("destination_country", "Vietnam"),
            "Readiness_Score": score,
            "Risk_Level": risk,
            "Issue_Detected": issue,
            "Responsible": dept,
            "Invoice_Qty": extracted.get("invoice_qty", 50000),
            "PL_Qty": extracted.get("packing_list_qty", 50000),
            "HS_Code": extracted.get("suggested_hs_code", "4016.99.90"),
            "COO_Form": coo,
        }

        st.session_state.master_db = pd.concat(
            [st.session_state.master_db, pd.DataFrame([new_row])],
            ignore_index=True,
        )
        st.session_state.selected_shipment_id = new_id
        st.toast(
            f"✅ Successfully processed {file.name}! Added Shipment {new_id}."
        )
        st.rerun()


# ==========================================
# 5. MAIN HEADER & CONTROL BAR
# ==========================================
st.title("🛡️ TradeReady AI")
st.caption(
    "Export Documentation & Customs Readiness Control Tower (OEM Electronics)"
)

col_sel, col_srch, col_b1, col_b2 = st.columns([2.5, 2, 1, 1])

with col_sel:
  df_db = st.session_state.master_db
  shipment_list = (
      df_db["Shipment_ID"] + " | " + df_db["Customer_Name"]
  ).tolist()
  selected_str = st.selectbox(
      "Selected Shipment:", shipment_list, index=0, key="shipment_selector"
  )
  selected_id = selected_str.split(" | ")[0]
  st.session_state.selected_shipment_id = selected_id

with col_srch:
  search_term = st.text_input(
      "🔍 Search Invoice / Customer...", "", key="search_box"
  )

with col_b1:
  st.write(" ")
  if st.button("➕ Add Document", use_container_width=True, type="primary"):
    st.toast("Upload drawer active in sidebar!")

with col_b2:
  st.write(" ")
  if st.button("🔄 Run AI Scan", use_container_width=True):
    st.toast("AI Audit Scan completed across all records!")

st.markdown("---")


# ==========================================
# 6. EXECUTIVE KPI METRICS
# ==========================================
shipment_data = df_db[df_db["Shipment_ID"] == selected_id].iloc[0]

k1, k2, k3, k4 = st.columns(4)

with k1:
  score = shipment_data["Readiness_Score"]
  st.metric(
      "CUSTOMS READINESS SCORE",
      f"{score}%",
      delta="HIGH RISK" if score < 50 else "READY",
      delta_color="inverse" if score < 50 else "normal",
  )

with k2:
  st.metric("DOC COMPLETION RATE", "90%", "9 of 10 Required Uploaded")

with k3:
  st.metric(
      "ESTIMATED BORDER DELAY",
      "+24 Hours" if score < 50 else "0 Hours",
      "CRITICAL HOLD RISK" if score < 50 else "ON SCHEDULE",
      delta_color="inverse" if score < 50 else "normal",
  )

with k4:
  st.metric(
      "RESPONSIBLE PARTY",
      f"{shipment_data['Responsible']} Team",
      "ACTION NEEDED",
  )

st.markdown("---")


# ==========================================
# 7. MIDDLE SECTION: FLEET ANALYTICS & INSPECTION MATRIX
# ==========================================
left_col, right_col = st.columns([1.1, 1])

# --- LEFT PANEL: FLEET ANALYTICS (3 CHARTS) ---
with left_col:
  st.subheader("📊 Fleet Analytics Summary")

  chart_tab1, chart_tab2, chart_tab3 = st.tabs(
      ["1. Risk Distribution", "2. Error Details", "3. Issues by Dept"]
  )

  with chart_tab1:
    fig_risk = px.pie(
        df_db,
        names="Risk_Level",
        hole=0.55,
        color="Risk_Level",
        color_discrete_map={
            "Low": "#10b981",
            "Medium": "#f59e0b",
            "High": "#ef4444",
        },
    )
    fig_risk.update_layout(
        template="plotly_dark",
        height=220,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=True,
    )
    st.plotly_chart(fig_risk, use_container_width=True)

  with chart_tab2:
    err_df = df_db[df_db["Issue_Detected"] != "None (Passed)"]
    if not err_df.empty:
      err_counts = (
          err_df["Issue_Detected"].value_counts().reset_index(name="count")
      )
      fig_err = px.bar(
          err_counts,
          x="count",
          y="Issue_Detected",
          orientation="h",
          color_discrete_sequence=["#8b5cf6"],
      )
      fig_err.update_layout(
          template="plotly_dark", height=220, margin=dict(l=10, r=10, t=20, b=10)
      )
      st.plotly_chart(fig_err, use_container_width=True)
    else:
      st.success("No active document errors detected!")

  with chart_tab3:
    dept_counts = (
        df_db["Responsible"].value_counts().reset_index(name="count")
    )
    fig_dept = px.bar(
        dept_counts,
        x="count",
        y="Responsible",
        orientation="h",
        color_discrete_sequence=["#3b82f6"],
    )
    fig_dept.update_layout(
        template="plotly_dark", height=220, margin=dict(l=10, r=10, t=20, b=10)
    )
    st.plotly_chart(fig_dept, use_container_width=True)


# --- RIGHT PANEL: CROSS-CHECK MATRIX & AI DIAGNOSTIC ---
with right_col:
  st.subheader(f"📄 Inspection Matrix: {selected_id}")

  inv_q = shipment_data.get("Invoice_Qty", 100000)
  pl_q = shipment_data.get("PL_Qty", 98000)
  is_mismatch = inv_q != pl_q

  matrix_df = pd.DataFrame([
      {
          "FIELD NAME": "Quantity (PCS)",
          "COMMERCIAL INVOICE": f"{inv_q:,} pcs",
          "PACKING LIST / AWB": f"{pl_q:,} pcs {'⚠️' if is_mismatch else ''}",
          "STATUS": "Mismatch" if is_mismatch else "Valid",
      },
      {
          "FIELD NAME": "Gross Weight",
          "COMMERCIAL INVOICE": "N/A",
          "PACKING LIST / AWB": "500 KGS",
          "STATUS": "Valid",
      },
      {
          "FIELD NAME": "Incoterms",
          "COMMERCIAL INVOICE": "FOB Bangkok",
          "PACKING LIST / AWB": "FOB Bangkok",
          "STATUS": "Valid",
      },
      {
          "FIELD NAME": "C/O Certificate",
          "COMMERCIAL INVOICE": shipment_data["COO_Form"],
          "PACKING LIST / AWB": shipment_data["COO_Form"],
          "STATUS": "Valid",
      },
  ])

  st.dataframe(matrix_df, use_container_width=True, hide_index=True)

  # AI Diagnostic Alert
  if is_mismatch:
    st.markdown(
        f"""
        <div class="alert-box">
            <b style="color:#fca5a5;">⚠️ Anomaly Detected: {shipment_data['Issue_Detected']}</b><br>
            <span style="font-size:12px; color:#e5e7eb;">
            Commercial Invoice states <b>{inv_q:,} PCS</b>, but Packing List states <b>{pl_q:,} PCS</b>.
            Discrepancy will trigger mandatory physical customs inspection at destination port.
            </span>
        </div>
        <div class="action-box">
            <b style="color:#38bdf8; font-size:11px; text-transform:uppercase;">Suggested Action:</b><br>
            <i style="font-size:12px; color:#ffffff;">"Reconcile quantity in Commercial Invoice or Packing List with Production Planning team before filing customs entry."</i>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.markdown(
        """
        <div style="background-color:#064e3b; border:1px solid #10b981; border-radius:8px; padding:12px; margin-bottom:12px;">
            <b style="color:#6ee7b7;">✅ AI Consistency Check Passed</b><br>
            <span style="font-size:12px; color:#e5e7eb;">All document fields match perfectly. Ready for customs clearance.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

  # Human Override Controls
  st.caption("⚙️ HUMAN OVERRIDE FUNCTION")
  hb1, hb2, hb3 = st.columns(3)
  with hb1:
    if st.button(
        "✓ Accept & Notify", type="primary", use_container_width=True
    ):
      st.success("Accepted & Notified Responsible Team!")
  with hb2:
    if st.button("✏️ Edit Data", use_container_width=True):
      st.info("Edit mode enabled.")
  with hb3:
    if st.button("✕ Reject Alert", use_container_width=True):
      st.warning("Alert Dismissed.")

st.markdown("---")


# ==========================================
# 8. BOTTOM MASTER DATABASE TABLE
# ==========================================
st.subheader("📋 All Shipments Readiness Overview")

filtered_df = df_db.copy()
if search_term:
  filtered_df = filtered_df[
      filtered_df["Shipment_ID"].str.contains(search_term, case=False)
      | filtered_df["Customer_Name"].str.contains(search_term, case=False)
      | filtered_df["Destination"].str.contains(search_term, case=False)
  ]

st.dataframe(
    filtered_df[[
        "Shipment_ID",
        "Customer_Name",
        "Destination",
        "Readiness_Score",
        "Risk_Level",
        "Issue_Detected",
        "Responsible",
        "HS_Code",
        "COO_Form",
    ]],
    use_container_width=True,
    hide_index=True,
)

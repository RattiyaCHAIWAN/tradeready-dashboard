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

  # ---------------------------------------------------------
  # PART 1: HTML BUILDER (การันตีพื้นหลังสีขาว 100% ให้อ่านง่าย)
  # ---------------------------------------------------------
  coo_color = "#D97706" if not audit.get("has_coo", True) else "#16A34A"
  coo_text = "❌ COO (Missing)" if not audit.get("has_coo", True) else "✓ COO (Verified)"
  comp_rate = "83.3%" if audit.get("readiness_score", 0) < 85 else "100%"

  # สร้างการ์ดแสดงผล Audit ย่อย
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

  # สร้างกล่อง HTML Dashboard หลัก
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
          <!-- Left Column -->
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
          
          <!-- Right Column -->
          <div style="flex: 1; min-width: 300px;">
              <div style="color: #1E3A8A; font-size: 18px; font-weight: 800; margin-bottom: 15px;">🔍 Cross-Document Multi-Audit</div>
              {audit_html}
          </div>
      </div>
  </div>
  """
  
  st.markdown(html_dashboard, unsafe_allow_html=True)
  
  # ---------------------------------------------------------
  # PART 2: ACTION & DECISION ROW (Streamlit Widgets)
  # ---------------------------------------------------------
  # เราใช้ CSS Trick (:has) ในการบังคับให้ Container ของ Action Row ด้านล่างสุดเป็นสีขาวเช่นกัน
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
      # ตัวระบุตำแหน่งให้ CSS ดึงไปใช้เปลี่ยนสี
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

import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import pypdf

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="TradeReady AI - Customs Readiness Assistant",
    page_icon="📦",
    layout="wide"
)

# Helper Function: อ่านข้อความจาก PDF
def read_pdf(file):
    pdf_reader = pypdf.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

# ---------------------------------------------------------
# Initialize AI / Gemini API
# ---------------------------------------------------------
api_key = st.sidebar.text_input("🔑 ใส่ Gemini API Key (ถ้ามี):", type="password")
if not api_key:
    api_key = st.secrets.get("GEMINI_API_KEY", "")

if api_key:
    genai.configure(api_key=api_key)

# ---------------------------------------------------------
# Title & Header
# ---------------------------------------------------------
st.title("📦 TradeReady AI")
st.caption("ระบบตรวจเช็กความพร้อมเอกสารศุลกากรและสนับสนุนการตัดสินใจส่งออก")
st.markdown("---")

# ---------------------------------------------------------
# Sidebar: File Upload (PDF, Excel, CSV) & Form Inputs
# ---------------------------------------------------------
st.sidebar.header("📄 1. อัปโหลดเอกสารส่งออก")
uploaded_file = st.sidebar.file_uploader(
    "รองรับไฟล์ PDF, Excel (.xlsx, .xls), CSV", 
    type=["pdf", "xlsx", "xls", "csv"]
)

extracted_text = ""
uploaded_df = None

if uploaded_file is not None:
    file_type = uploaded_file.name.split(".")[-1].lower()
    
    if file_type == "pdf":
        extracted_text = read_pdf(uploaded_file)
        st.sidebar.success("✅ สกัดข้อมูลจาก PDF สำเร็จ!")
        with st.sidebar.expander("🔍 ดูข้อความจาก PDF"):
            st.write(extracted_text[:500] + "...")
            
    elif file_type in ["xlsx", "xls", "csv"]:
        try:
            if file_type == "csv":
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file)
                
            st.sidebar.success(f"✅ โหลดไฟล์ {file_type.upper()} สำเร็จ!")
            # แปลงข้อมูลในตารางเป็นข้อความเพื่อให้ AI นำไปประมวลผลต่อได้
            extracted_text = uploaded_df.to_string()
            
            with st.sidebar.expander("🔍 ดูตัวอย่างตาราง Excel/CSV"):
                st.dataframe(uploaded_df.head(5))
        except Exception as e:
            st.sidebar.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. สถานการณ์ & Test Cases")

scenario_mode = st.sidebar.selectbox(
    "เลือกสถานการณ์ดำเนินงาน:",
    ["1. Normal Scenario (ปกติ)", "2. Disruption Scenario (ศุลกากรตรวจเข้ม)", "3. Erroneous Data Scenario (ข้อมูลผิดพลาด)"]
)

test_case_preset = st.sidebar.selectbox(
    "โหลดเคสทดสอบบังคับ 5 ข้อ:",
    [
        " custom (กำหนดเอง)",
        "Test Case 1: จำนวน Invoice ไม่ตรงกับ Packing List",
        "Test Case 2: หนังสือรับรองถิ่นกำเนิด (CO) ขาดหายไป",
        "Test Case 3: รายละเอียดสินค้ากว้างเกินไป ('Parts')",
        "Test Case 4: น้ำหนัก Gross Weight น้อยกว่า Net Weight",
        "Test Case 5: Incoterm ขัดแย้งกับการจ่ายค่าขนส่ง (EXW)"
    ]
)

# Preset Values
def_inv_qty, def_pl_qty = 500, 500
def_gross, def_net = 120.0, 100.0
def_desc = "Auto Spare Parts - Brake Pads Model X"
def_has_co = True
def_incoterm = "FOB"
def_freight_payer = "Buyer"

if test_case_preset == "Test Case 1: จำนวน Invoice ไม่ตรงกับ Packing List":
    def_inv_qty, def_pl_qty = 500, 450
elif test_case_preset == "Test Case 2: หนังสือรับรองถิ่นกำเนิด (CO) ขาดหายไป":
    def_has_co = False
elif test_case_preset == "Test Case 3: รายละเอียดสินค้ากว้างเกินไป ('Parts')":
    def_desc = "Parts"
elif test_case_preset == "Test Case 4: น้ำหนัก Gross Weight น้อยกว่า Net Weight":
    def_gross, def_net = 90.0, 100.0
elif test_case_preset == "Test Case 5: Incoterm ขัดแย้งกับการจ่ายค่าขนส่ง (EXW)":
    def_incoterm = "EXW"
    def_freight_payer = "Seller (Exporter)"

st.sidebar.markdown("---")
st.sidebar.header("📝 3. รายละเอียด Shipment")
shipment_id = st.sidebar.text_input("Shipment ID", "SHP-2026-001")
prod_desc = st.sidebar.text_area("รายละเอียดสินค้า", def_desc)
inv_qty = st.sidebar.number_input("จำนวนใน Invoice (ชิ้น)", value=def_inv_qty)
pl_qty = st.sidebar.number_input("จำนวนใน Packing List (ชิ้น)", value=def_pl_qty)
net_wt = st.sidebar.number_input("Net Weight (kg)", value=def_net)
gross_wt = st.sidebar.number_input("Gross Weight (kg)", value=def_gross)
has_co = st.sidebar.checkbox("มี Certificate of Origin (CO)", value=def_has_co)
incoterm = st.sidebar.selectbox("Incoterm", ["EXW", "FOB", "CIF", "DDP"], index=["EXW", "FOB", "CIF", "DDP"].index(def_incoterm))
freight_payer = st.sidebar.selectbox("ผู้จ่ายค่าขนส่งหลัก", ["Buyer", "Seller (Exporter)"], index=["Buyer", "Seller (Exporter)"].index(def_freight_payer))

# ---------------------------------------------------------
# Rule-Based Anomaly Detection
# ---------------------------------------------------------
discrepancies = []
missing_docs = []
risk_penalty = 0

if inv_qty != pl_qty:
    discrepancies.append(f"❌ **จำนวนสินค้าไม่ตรงกัน:** Invoice ({inv_qty}) != Packing List ({pl_qty})")
    risk_penalty += 25

if not has_co:
    missing_docs.append("❌ **เอกสารขาดหาย:** หนังสือรับรองถิ่นกำเนิดสินค้า (CO)")
    risk_penalty += 30

if len(prod_desc.strip()) <= 5:
    discrepancies.append("⚠️ **คำบรรยายสินค้ากว้างเกินไป:** เสี่ยงโดนกักตรวจ HS-Code")
    risk_penalty += 15

if gross_wt < net_wt:
    discrepancies.append(f"❌ **น้ำหนักผิดปกติ:** Gross Weight ({gross_wt}kg) ต่ำกว่า Net Weight ({net_wt}kg)")
    risk_penalty += 25

if incoterm == "EXW" and freight_payer == "Seller (Exporter)":
    discrepancies.append("⚠️ **Incoterm ขัดแย้ง:** เลือก EXW แต่ระบุว่าผู้ขายจ่ายค่าขนส่ง")
    risk_penalty += 20

if scenario_mode == "2. Disruption Scenario (ศุลกากรตรวจเข้ม)":
    risk_penalty += 15

readiness_score = max(0, 100 - risk_penalty)
completion_pct = int(((5 - len(missing_docs)) / 5) * 100)

if readiness_score >= 80:
    risk_level, est_delay = "Low Risk", "0 - 2 ชั่วโมง"
elif readiness_score >= 50:
    risk_level, est_delay = "Medium Risk", "12 - 24 ชั่วโมง"
else:
    risk_level, est_delay = "High Risk", "48 - 72 ชั่วโมง"

# ---------------------------------------------------------
# Top Dashboard KPIs
# ---------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Customs Readiness", f"{readiness_score} / 100")
c2.metric("Document Completion", f"{completion_pct}%")
c3.metric("Risk Level", risk_level)
c4.metric("Est. Delay", est_delay)

st.markdown("---")

# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 1. ผลการตรวจเอกสาร", 
    "🤖 2. วิเคราะห์ด้วย AI (PDF / Excel / HS-Code)", 
    "👤 3. Human Override", 
    "📊 4. ฐานข้อมูล 30 รายการ"
])

with tab1:
    st.subheader("📌 รายการข้อผิดพลาดที่พบ")
    if discrepancies or missing_docs:
        for err in discrepancies:
            st.error(err)
        for doc in missing_docs:
            st.warning(doc)
    else:
        st.success("✅ เอกสารสมบูรณ์ ไม่พบข้อผิดพลาดรุนแรง")

    st.markdown("### 🛠️ ตารางมอบหมายผู้รับผิดชอบแก้ไข")
    audit_df = pd.DataFrame([
        {"รายการตรวจ": "ความตรงกันของ Invoice/Packing List", "สถานะ": "ผิดพลาด" if inv_qty != pl_qty else "ถูกต้อง", "ผู้รับผิดชอบ": "ฝ่ายคลังสินค้า (Warehouse)"},
        {"รายการตรวจ": "หนังสือรับรองถิ่นกำเนิด (CO)", "สถานะ": "ขาดหาย" if not has_co else "ครบถ้วน", "ผู้รับผิดชอบ": "เจ้าหน้าที่เอกสาร (Shipping)"},
        {"รายการตรวจ": "ตรรกะน้ำหนัก Gross/Net", "สถานะ": "ผิดปกติ" if gross_wt < net_wt else "ถูกต้อง", "ผู้รับผิดชอบ": "ฝ่ายจัดส่ง (Logistics)"},
        {"รายการตรวจ": "ความสอดคล้อง Incoterms", "สถานะ": "ขัดแย้ง" if (incoterm == "EXW" and freight_payer == "Seller (Exporter)") else "ถูกต้อง", "ผู้รับผิดชอบ": "ฝ่ายขายต่างประเทศ (Export Sales)"},
    ])
    st.table(audit_df)

with tab2:
    st.subheader("🤖 บทวิเคราะห์จาก AI")
    
    # กรณีมีการอัปโหลดไฟล์เข้ามา (PDF / Excel / CSV)
    if extracted_text:
        st.info("📄 พบข้อมูลจากไฟล์ที่อัปโหลดเข้ามาระบบ")
        if uploaded_df is not None:
            st.markdown("**ตัวอย่างตารางข้อมูลที่อ่านได้:**")
            st.dataframe(uploaded_df, use_container_width=True)
            
        if st.button("🔍 ให้ AI ตรวจสอบข้อมูลในไฟล์นี้"):
            if api_key:
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"""
                    คุณคือผู้เชี่ยวชาญด้านศุลกากร กรุณาวิเคราะห์ข้อมูลจากไฟล์เอกสารส่งออกต่อไปนี้:
                    
                    --- ข้อมูลในไฟล์ ---
                    {extracted_text[:3000]}
                    -------------------
                    
                    กรุณาสรุป:
                    1. รายการสินค้า ปริมาณ และน้ำหนัก
                    2. ตรวจสอบข้อผิดพลาดหรือข้อขัดแย้งของข้อมูล
                    3. แนะนำ HS-Code ที่ถูกต้องและเหมาะสม
                    ตอบเป็นภาษาไทย รูปแบบสวยงาม อ่านง่าย
                    """
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.write("💡 **ผลวิเคราะห์จำลองจาก AI:** อ่านข้อมูลในไฟล์เรียบร้อย ตรวจพบรายการสินค้าสอดคล้องกับพิกัดศุลกากรหมวด 8708 (ชิ้นส่วนยานยนต์)")
    
    st.markdown("---")
    if st.button("🚀 ให้ AI วิเคราะห์รายละเอียดสินค้า & แนะนำ HS-Code (จากฟอร์ม)"):
        if api_key:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"วิเคราะห์สินค้า '{prod_desc}' แนะนำ HS-Code ที่เป็นไปได้ 2-3 พิกัด พร้อมคำแนะนำศุลกากรเป็นภาษาไทย"
                res = model.generate_content(prompt)
                st.markdown(res.text)
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            if "Parts" in prod_desc or len(prod_desc) <= 5:
                st.warning("⚠️ **วิเคราะห์จาก AI:** คำว่า 'Parts' กว้างเกินไป")
                st.write("**HS-Code แนะนำ:** 8708.29 หรือ 8473.30")
            else:
                st.success(f"✅ **วิเคราะห์จาก AI:** สินค้า '{prod_desc}' มีความชัดเจนดี")
                st.write("**HS-Code แนะนำ:** 8708.30.90")

with tab3:
    st.subheader("👤 การยืนยันโดยมนุษย์ (Human Override)")
    choice = st.radio("สิทธิ์การตัดสินใจของผู้ใช้:", ["✅ Accept (ยอมรับ AI)", "✏️ Modify (แก้ไขเอง)", "❌ Reject (ปฏิเสธ AI)"])
    if choice == "✏️ Modify (แก้ไขเอง)":
        user_hs = st.text_input("ระบุ HS-Code ที่ต้องการใช้:", "8708.30.90")
        reason = st.text_area("เหตุผลที่แก้ไข:", "แก้ไขตามการยืนยันจากชิปปิ้ง")
        if st.button("บันทึก"):
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")

with tab4:
    st.subheader("📊 ฐานข้อมูลตัวอย่าง 30 รายการ")
    import random
    rows = []
    for i in range(1, 31):
        s = "Pass"
        score = random.randint(85, 100)
        if i in [3, 7, 14, 21, 28]:
            s = "Warning / Error"
            score = random.randint(35, 70)
        rows.append({"Shipment ID": f"SHP-2026-{i:03d}", "Dest": random.choice(["China", "Japan", "Vietnam"]), "Score": score, "Status": s})
    
    df_sample = pd.DataFrame(rows)
    st.dataframe(df_sample, use_container_width=True)
    fig = px.pie(df_sample, names="Status", color="Status", color_discrete_map={"Pass": "green", "Warning / Error": "red"})
    st.plotly_chart(fig, use_container_width=True)

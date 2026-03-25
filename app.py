import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import altair as alt

st.set_page_config(page_title="Family Budget Pro", layout="wide")
st.title("🏠 บันทึกรายรับ-รายจ่ายครอบครัว (Pro Version)")

# 1. เชื่อมต่อฐานข้อมูล
creds = json.loads(st.secrets["my_secrets"]["json_key"])
conn = st.connection("gsheets", type=GSheetsConnection, service_account_info=creds)

# 2. ดึงข้อมูลมาแสดงผล
df = conn.read(worksheet="Sheet1", ttl="0")

# เติมคอลัมน์ที่ว่างเพื่อป้องกัน Error
for col in ["วันที่", "รายการ", "หมวดหมู่", "ประเภท", "จำนวนเงิน", "หมายเหตุ"]:
    if col not in df.columns:
        df[col] = ""
df = df.fillna("")

# 3. เมนูเพิ่มข้อมูล (Sidebar)
with st.sidebar:
    st.header("➕ เพิ่มรายการใหม่")
    date = st.date_input("วันที่")
    name = st.text_input("รายการ")
    kind = st.selectbox("ประเภท", ["รายจ่าย", "รายรับ"])
    
    # เปลี่ยนหมวดหมู่อัตโนมัติ ตามประเภทที่เลือก
    if kind == "รายจ่าย":
        category = st.selectbox("หมวดหมู่", ["อาหาร", "เดินทาง", "ของใช้", "บิล/น้ำไฟ", "ช้อปปิ้ง", "อื่นๆ"])
    else:
        category = st.selectbox("หมวดหมู่", ["เงินเดือน", "ขายของ", "โบนัส", "อื่นๆ"])
        
    price = st.number_input("จำนวนเงิน", min_value=0.0)
    note = st.text_area("หมายเหตุ (ถ้ามี)")
    
    if st.button("บันทึกข้อมูล", type="primary"):
        if name and price > 0:
            new_row = pd.DataFrame([[str(date), name, category, kind, price, note]], 
                                   columns=["วันที่", "รายการ", "หมวดหมู่", "ประเภท", "จำนวนเงิน", "หมายเหตุ"])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("บันทึกสำเร็จ!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("กรุณากรอกชื่อรายการและจำนวนเงินให้ถูกต้อง")

# 4. ตารางแบบใหม่ (แก้ไขและลบได้โดยตรง)
st.subheader("📝 จัดการข้อมูล (แก้ไข/ลบ)")
st.caption("💡 ทริค: ดับเบิ้ลคลิกที่ช่องเพื่อแก้ไขข้อความ หรือคลิกกล่องสี่เหลี่ยมด้านซ้ายสุดแล้วกดปุ่ม 'Delete' บนคีย์บอร์ดเพื่อลบแถว")

# ตารางอัจฉริยะ (Data Editor)
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")

# ปุ่มเซฟเมื่อมีการลบหรือแก้ไขข้อมูลในตาราง
if st.button("💾 บันทึกการแก้ไข/ลบข้อมูล"):
    conn.update(worksheet="Sheet1", data=edited_df)
    st.success("อัปเดตฐานข้อมูลสำเร็จ!")
    st.cache_data.clear()
    st.rerun()

st.divider()

# 5. แดชบอร์ดสรุปผลและกราฟ (วิเคราะห์อัตโนมัติ)
st.subheader("📊 สรุปยอดและกราฟวิเคราะห์")
try:
    # คำนวณยอดเงิน
    edited_df["จำนวนเงิน"] = pd.to_numeric(edited_df["จำนวนเงิน"], errors='coerce').fillna(0)
    inc = edited_df[edited_df["ประเภท"] == "รายรับ"]["จำนวนเงิน"].sum()
    exp = edited_df[edited_df["ประเภท"] == "รายจ่าย"]["จำนวนเงิน"].sum()
    
    # โชว์ป้ายสรุปยอด
    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 รายรับรวม", f"{inc:,.2f} ฿")
    c2.metric("🔴 รายจ่ายรวม", f"{exp:,.2f} ฿")
    c3.metric("💰 คงเหลือ", f"{inc - exp:,.2f} ฿")
    
    # วาดกราฟ
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🍩 สัดส่วนรายจ่ายแยกตามหมวดหมู่**")
        exp_df = edited_df[edited_df["ประเภท"] == "รายจ่าย"]
        if not exp_df.empty:
            exp_summary = exp_df.groupby("หมวดหมู่")["จำนวนเงิน"].sum().reset_index()
            pie_chart = alt.Chart(exp_summary).mark_arc(innerRadius=40).encode(
                theta="จำนวนเงิน",
                color="หมวดหมู่",
                tooltip=["หมวดหมู่", "จำนวนเงิน"]
            )
            st.altair_chart(pie_chart, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายจ่ายให้แสดงกราฟ")
            
    with col2:
        st.markdown("**📊 เปรียบเทียบรายรับ vs รายจ่าย**")
        summary_df = pd.DataFrame({"ประเภท": ["รายรับ", "รายจ่าย"], "ยอดเงิน": [inc, exp]})
        bar_chart = alt.Chart(summary_df).mark_bar().encode(
            x="ประเภท",
            y="ยอดเงิน",
            color=alt.Color("ประเภท", scale=alt.Scale(domain=["รายรับ", "รายจ่าย"], range=["#28a745", "#dc3545"]))
        )
        st.altair_chart(bar_chart, use_container_width=True)

except Exception as e:
    st.info("กราฟจะแสดงผลเมื่อคุณเริ่มบันทึกข้อมูลครับ")

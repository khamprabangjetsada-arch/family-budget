import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Family Budget", layout="wide")
st.title("🏠 บันทึกรายรับ-รายจ่ายครอบครัว")

conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl="0")

with st.sidebar:
    st.header("➕ เพิ่มรายการ")
    date = st.date_input("วันที่")
    name = st.text_input("รายการ")
    kind = st.selectbox("ประเภท", ["รายรับ", "รายจ่าย"])
    price = st.number_input("จำนวนเงิน", min_value=0.0)
    
    if st.button("บันทึก"):
        if name:
            new_row = pd.DataFrame([[str(date), name, kind, price]], columns=df.columns)
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("บันทึกสำเร็จ!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("กรุณากรอกชื่อรายการ")

st.dataframe(df, use_container_width=True)

try:
    inc = df[df["ประเภท"] == "รายรับ"]["จำนวนเงิน"].astype(float).sum()
    exp = df[df["ประเภท"] == "รายจ่าย"]["จำนวนเงิน"].astype(float).sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("รายรับ", f"{inc:,.2f} ฿")
    c2.metric("รายจ่าย", f"{exp:,.2f} ฿")
    c3.metric("คงเหลือ", f"{inc - exp:,.2f} ฿")
except:
    st.info("ยังไม่มีข้อมูลสำหรับคำนวณ")

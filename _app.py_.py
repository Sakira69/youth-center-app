import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# ---------- เชื่อมต่อ Google Sheets ----------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open("youth_center_data").worksheet("records")
    return sheet

sheet = connect_sheet()

def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def add_record(record_date, court_name, amount, note):
    sheet.append_row([str(record_date), court_name, amount, note])

# ---------- ระบบล็อกอิน ----------
USERS = {
    "badminton": {"password": "bad2569", "role": "court", "name": "สนามแบดมินตัน"},
    "admin": {"password": "admin2569", "role": "admin", "name": "ผู้ดูแลระบบ"},
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("เข้าสู่ระบบ")
    username = st.text_input("ชื่อผู้ใช้")
    password = st.text_input("รหัสผ่าน", type="password")
    if st.button("เข้าสู่ระบบ"):
        user = USERS.get(username)
        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = user["role"]
            st.session_state.name = user["name"]
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# ---------- หน้าหลังล็อกอิน ----------
st.sidebar.write(f"เข้าสู่ระบบในนาม: **{st.session_state.name}**")
if st.sidebar.button("ออกจากระบบ"):
    st.session_state.logged_in = False
    st.rerun()

if st.session_state.role == "court":
    st.title(f"บันทึกรายได้ - {st.session_state.name}")
    record_date = st.date_input("วันที่", value=date.today())
    amount = st.number_input("จำนวนเงิน (บาท)", min_value=0, step=10)
    note = st.text_input("หมายเหตุ (ถ้ามี)")
    if st.button("บันทึกข้อมูล"):
        add_record(record_date, st.session_state.name, amount, note)
        st.success("บันทึกข้อมูลเรียบร้อยแล้ว")

elif st.session_state.role == "admin":
    st.title("ภาพรวมข้อมูลทุกสนาม")
    df = load_data()
    if df.empty:
        st.info("ยังไม่มีข้อมูล")
    else:
        st.dataframe(df, use_container_width=True)
        st.subheader("สรุปยอดรวมตามสนาม")
        summary = df.groupby("court_name")["amount"].sum().reset_index()
        st.bar_chart(summary.set_index("court_name"))
        total = df["amount"].sum()
        st.metric("ยอดรวมทั้งหมด", f"{total:,.0f} บาท")

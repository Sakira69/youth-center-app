import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date, datetime

SHEET_NAME = "youth_center_data"
WORKSHEET_NAME = "records"
HEADER = ["record_date", "facility", "sub_category",
          "male_count", "female_count", "total_count",
          "updated_by", "updated_at"]

FACILITIES = {
    "แบดมินตัน": [None],
    "สนามฟุตบอลใหญ่": [
        "ผู้ใช้บริการสนามฟุตบอล",
        "โรงเรียนกีฬากรุงเทพ",
        "ผู้ใช้บริการลู่วิ่ง",
    ],
    "สระว่ายน้ำ": [
        "ผู้เรียนขั้นพื้นฐาน",
        "ผู้เรียนขั้นพัฒนาทักษะ",
        "ผู้เรียนชั้นผู้ใหญ่",
        "ผู้เรียนพิเศษ",
        "ผู้สูงอายุ",
        "โรงเรียนกีฬา",
        "ผู้ใช้บริการ",
        "กรณีพิเศษ",
    ],
    "สควอช": [None],
}

# ---------- บัญชีผู้ใช้ ----------
USERS = {
    "badminton": {"password": "bad12345", "role": "facility", "facility": "แบดมินตัน", "name": "ผู้ดูแลแบดมินตัน"},
    "football":  {"password": "foot12345", "role": "facility", "facility": "สนามฟุตบอลใหญ่", "name": "ผู้ดูแลสนามฟุตบอล"},
    "pool":      {"password": "pool12345", "role": "facility", "facility": "สระว่ายน้ำ", "name": "ผู้ดูแลสระว่ายน้ำ"},
    "squash":    {"password": "squ12345", "role": "facility", "facility": "สควอช", "name": "ผู้ดูแลสควอช"},
    "admin":     {"password": "admin54321", "role": "admin", "facility": None, "name": "ผู้บริหาร"},
}

# ---------------- Google Sheets ----------------
@st.cache_resource
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    client = gspread.authorize(creds)
    sh = client.open(SHEET_NAME)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=2000, cols=len(HEADER))
        ws.append_row(HEADER)
    return ws

@st.cache_data(ttl=15, show_spinner=False)
def load_all():
    ws = get_sheet()
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=HEADER)
    else:
        df["male_count"] = pd.to_numeric(df["male_count"], errors="coerce").fillna(0).astype(int)
        df["female_count"] = pd.to_numeric(df["female_count"], errors="coerce").fillna(0).astype(int)
        df["total_count"] = pd.to_numeric(df["total_count"], errors="coerce").fillna(0).astype(int)
        df["record_date"] = df["record_date"].astype(str)
        df["sub_category"] = df["sub_category"].fillna("").astype(str)
    return df

def save_facility_data(record_date, facility, subs_data, user):
    """subs_data: list of (sub_category, male, female)"""
    ws = get_sheet()
    all_values = ws.get_all_values()
    existing_rows = all_values[1:] if len(all_values) > 1 else []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    updates, appends = [], []
    for sub, male, female in subs_data:
        sub_val = sub or ""
        total = male + female
        new_row = [record_date, facility, sub_val, male, female, total, user, now_str]
        found_idx = None
        for i, row in enumerate(existing_rows, start=2):
            if len(row) >= 3 and row[0] == record_date and row[1] == facility and row[2] == sub_val:
                found_idx = i
                break
        if found_idx:
            updates.append((found_idx, new_row))
        else:
            appends.append(new_row)

    if updates:
        ws.batch_update([{"range": f"A{i}:H{i}", "values": [row]} for i, row in updates])
    if appends:
        ws.append_rows(appends)

    load_all.clear()  # เคลียร์ cache หลังบันทึก

def load_day(record_date, facility=None):
    df = load_all()
    if df.empty:
        return df
    df = df[df["record_date"] == record_date]
    if facility:
        df = df[df["facility"] == facility]
    return df

def load_range(start_date, end_date):
    df = load_all()
    if df.empty:
        return df
    df = df[(df["record_date"] >= start_date) & (df["record_date"] <= end_date)]
    return df.sort_values("record_date")

# ---------------- Login ----------------
def login_screen():
    st.title("🔐 เข้าสู่ระบบ")
    st.caption("ศูนย์เยาวชนกรุงเทพมหานคร (ไทย-ญี่ปุ่น)")
    username = st.text_input("ชื่อผู้ใช้")
    password = st.text_input("รหัสผ่าน", type="password")
    if st.button("เข้าสู่ระบบ", type="primary"):
        user = USERS.get(username)
        if user and user["password"] == password:
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

# ---------------- App ----------------
st.set_page_config(page_title="ศูนย์เยาวชนกรุงเทพฯ (ไทย-ญี่ปุ่น)", layout="wide")

if "user" not in st.session_state:
    login_screen()
    st.stop()

current_user = USERS[st.session_state["user"]]

with st.sidebar:
    st.write(f"👤 เข้าสู่ระบบในนาม: **{current_user['name']}**")
    if st.button("ออกจากระบบ"):
        del st.session_state["user"]
        st.rerun()

st.title("📋 ระบบบันทึกยอดผู้ใช้บริการรายวัน")
st.caption("ศูนย์เยาวชนกรุงเทพมหานคร (ไทย-ญี่ปุ่น)")

# ---------- โหมดผู้ดูแลสนาม ----------
if current_user["role"] == "facility":
    facility = current_user["facility"]
    subs = FACILITIES[facility]

    selected_date = st.date_input("วันที่บันทึกข้อมูล", value=date.today(), format="DD/MM/YYYY")
    record_date_str = selected_date.strftime("%Y-%m-%d")

    st.subheader(f"📝 บันทึกข้อมูล: {facility}")

    existing = load_day(record_date_str, facility)

    for sub in subs:
        label = sub if sub else facility
        prev_m, prev_f = 0, 0
        if not existing.empty:
            row = existing[existing["sub_category"] == (sub or "")]
            if not row.empty:
                prev_m = int(row.iloc[0]["male_count"])
                prev_f = int(row.iloc[0]["female_count"])

        cols = st.columns([3, 1, 1, 1])
        cols[0].write(f"**{label}**")
        male = cols[1].number_input(
    "ชาย", min_value=0, step=1, value=prev_m,
    key=f"m_{facility}_{sub}_{record_date_str}"
)
female = cols[2].number_input(
    "หญิง", min_value=0, step=1, value=prev_f,
    key=f"f_{facility}_{sub}_{record_date_str}"
)
cols[3].metric("รวม", male + female)

if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
        subs_data = []
        for sub in subs:
            male = st.session_state.get(f"m_{facility}_{sub}_{record_date_str}", 0)
            female = st.session_state.get(f"f_{facility}_{sub}_{record_date_str}", 0)
            subs_data.append((sub, male, female))
        save_facility_data(record_date_str, facility, subs_data, current_user["name"])
        st.success(f"บันทึกข้อมูล {facility} วันที่ {selected_date.strftime('%d/%m/%Y')} เรียบร้อยแล้ว ✅")

# ---------- โหมดผู้บริหาร ----------
else:
    tab1, tab2 = st.tabs(["📊 แดชบอร์ดผู้บริหาร", "📤 สร้างข้อความรายงาน"])

    with tab1:
        col1, col2 = st.columns(2)
        view_date = col1.date_input("เลือกวันที่ดูข้อมูล", value=date.today())
        view_date_str = view_date.strftime("%Y-%m-%d")

        df_day = load_day(view_date_str)
        if df_day.empty:
            st.info("ยังไม่มีข้อมูลบันทึกในวันนี้")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("รวมชายทั้งหมด", f"{df_day['male_count'].sum():,} คน")
            m2.metric("รวมหญิงทั้งหมด", f"{df_day['female_count'].sum():,} คน")
            m3.metric("รวมทั้งสิ้น", f"{df_day['total_count'].sum():,} คน")

            display_df = df_day[["facility", "sub_category", "male_count", "female_count", "total_count", "updated_by", "updated_at"]]
            display_df.columns = ["สนาม/บริการ", "ประเภทย่อย", "ชาย", "หญิง", "รวม", "บันทึกโดย", "เวลาอัปเดต"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.subheader("สรุปยอดรวมแยกตามสนาม")
            by_facility = df_day.groupby("facility")["total_count"].sum().reset_index()
            st.bar_chart(by_facility.set_index("facility"))

        st.divider()
        st.subheader("📈 แนวโน้มย้อนหลัง")
        c1, c2 = st.columns(2)
        start = c1.date_input("จากวันที่", value=date.today())
        end = c2.date_input("ถึงวันที่", value=date.today())
        df_range = load_range(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if not df_range.empty:
            trend = df_range.groupby("record_date")["total_count"].sum().reset_index()
            st.line_chart(trend.set_index("record_date"))
        else:
            st.info("ไม่มีข้อมูลในช่วงวันที่เลือก")

    with tab2:
        st.subheader("สร้างข้อความรายงานสำหรับส่งไลน์")
        rep_date = st.date_input("เลือกวันที่", value=date.today(), key="rep_date")
        rep_date_str = rep_date.strftime("%Y-%m-%d")
        df_rep = load_day(rep_date_str)

        def get_val(facility, sub=None):
            row = df_rep[(df_rep["facility"] == facility) & (df_rep["sub_category"] == (sub or ""))]
            if row.empty:
                return 0, 0, 0
            r = row.iloc[0]
            return int(r["male_count"]), int(r["female_count"]), int(r["total_count"])

        if df_rep.empty:
            st.warning("ยังไม่มีข้อมูลของวันนี้")
        else:
            thai_months_short = ['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.']
            thai_months_full = ['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม']
            buddhist_year_short = str(rep_date.year + 543)[2:]
            buddhist_year_full = rep_date.year + 543

            text = f"{rep_date.strftime('%d')} {thai_months_short[rep_date.month-1]} {buddhist_year_short}\n"
            m, f, t = get_val("แบดมินตัน")
            text += f"แบดมินตัน\nช. {m} คน\nญ. {f} คน\nรวม {t} คน\n\n"

            text += f"รายงานยอดสนามฟุตบอลใหญ่\nวันที่ {rep_date.strftime('%d')} {thai_months_full[rep_date.month-1]} {buddhist_year_full}\n"
            m, f, _ = get_val("สนามฟุตบอลใหญ่", "ผู้ใช้บริการสนามฟุตบอล")
            text += f"📌ผู้ใช้บริการสนามฟุตบอล\nชาย {m}\nหญิง {f}\n"
            m, f, _ = get_val("สนามฟุตบอลใหญ่", "โรงเรียนกีฬากรุงเทพ")
            text += f"📌โรงเรียนกีฬากรุงเทพ📌\nชาย {m}\nหญิง {f}\n"
            m, f, _ = get_val("สนามฟุตบอลใหญ่", "ผู้ใช้บริการลู่วิ่ง")
            text += f"📌ผู้ใช้บริการลู่วิ่ง📌\nชาย {m}\nหญิง {f}\n\n"

            text += f"ยอดผู้ใช้บริการสระว่ายน้ำ\n👉 วันที่ {rep_date.strftime('%d')} {thai_months_full[rep_date.month-1]} {buddhist_year_full}\n\n"
            swim_labels = {
                "ผู้เรียนขั้นพื้นฐาน": "(1) ผู้เรียนขั้นพื้นฐาน",
                "ผู้เรียนขั้นพัฒนาทักษะ": "(2) ผู้เรียนขั้นพัฒนาทักษะ",
                "ผู้เรียนชั้นผู้ใหญ่": "(3) ผู้เรียนชั้นผู้ใหญ่",
                "ผู้เรียนพิเศษ": "(4) ผู้เรียนพิเศษ",
                "ผู้สูงอายุ": "(5) ผู้สูงอายุ",
                "โรงเรียนกีฬา": "(6) โรงเรียนกีฬา",
                "ผู้ใช้บริการ": "(7) ผู้ใช้บริการ",
                "กรณีพิเศษ": "(8) กรณีพิเศษ",
            }
            sum_m, sum_f, sum_t = 0, 0, 0
            for sub, label in swim_labels.items():
                m, f, t = get_val("สระว่ายน้ำ", sub)
                sum_m += m; sum_f += f; sum_t += t
                text += f"{label}\n🏊‍♂️ ชาย : {m} คน\n🏊‍♀️ หญิง : {f} คน\nรวม : {t} คน\n\n"
            text += f"😍 รวมทุกประเภท\n🏊‍♂️ ชาย : {sum_m} คน\n🏊‍♀️ หญิง : {sum_f} คน\nยอดรวมทั้งสิ้น : {sum_t} คน\n\n"

            m, f, t = get_val("สควอช")
            text += f"สควอช\nวันที่ {rep_date.strftime('%d')} {thai_months_short[rep_date.month-1]}{buddhist_year_short}\nชาย {m} คน\nหญิง {f} คน\nรวม {t} คน"

            st.text_area("คัดลอกข้อความนี้ไปวางในไลน์", value=text, height=500)

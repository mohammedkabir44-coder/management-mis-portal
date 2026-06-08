import streamlit as st
import datetime
import pandas as pd
import cv2
import segno
from pyzbar.pyzbar import decode
import numpy as np
import os
import httpx
import base64
import hashlib

st.set_page_config(page_title="Taraba State LGMS", layout="wide", initial_sidebar_state="expanded")

OS_PASSPORT_DIR = "saved_passports"
os.makedirs(OS_PASSPORT_DIR, exist_ok=True)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://abcde12345.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "PASTE_YOUR_ACTUAL_LONG_ANON_PUBLIC_KEY_HERE")

STAFF_FILE = "local_database_staff.csv"
ATTENDANCE_FILE = "local_database_attendance.csv"
ADMINS_FILE = "local_database_admins.csv"

TARABA_LGAS = [
    "Ardo Kola", "Bali", "Donga", "Gashaka", "Gassol", "Ibi", 
    "Jalingo", "Karim Lamido", "Kurmi", "Lau", "Sardauna", 
    "Takum", "Ussa", "Wukari", "Yorro", "Zing"
]

DEPARTMENTS = [
    "Administration", "Operations & Logistics", "Finance & Revenue Control", 
    "Security & Enforcement", "Information Technology (IT)", "Human Resources (HR)"
]

def secure_hash_password(password: str, salt: str = "Taraba_Secure_Salt_2026") -> str:
    salted_input = password + salt
    return hashlib.sha256(salted_input.encode('utf-8')).hexdigest()

# INITIALIZE LOCAL DATABASES
if "staff_db" not in st.session_state:
    if os.path.exists(STAFF_FILE):
        try: st.session_state.staff_db = pd.read_csv(STAFF_FILE).to_dict(orient="records")
        except: st.session_state.staff_db = []
    else:
        st.session_state.staff_db = [{"staff_id": "STF-101", "full_name": "Mohammed Abubakar", "lga": "Jalingo", "department": "Administration", "position": "Director", "phone": "08012345678", "email": "mohammed@example.com", "has_photo": "No Upload", "has_doc": "No Upload"}]
        pd.DataFrame(st.session_state.staff_db).to_csv(STAFF_FILE, index=False)

if "attendance_db" not in st.session_state:
    if os.path.exists(ATTENDANCE_FILE):
        try: st.session_state.attendance_db = pd.read_csv(ATTENDANCE_FILE).to_dict(orient="records")
        except: st.session_state.attendance_db = []
    else:
        st.session_state.attendance_db = [{"attendance_date": str(datetime.date.today()), "staff_id": "STF-101", "lga": "Jalingo", "check_in": "08:30 AM", "check_out": "04:15 PM"}]
        pd.DataFrame(st.session_state.attendance_db).to_csv(ATTENDANCE_FILE, index=False)

if "admins_db" not in st.session_state:
    if os.path.exists(ADMINS_FILE):
        try: st.session_state.admins_db = pd.read_csv(ADMINS_FILE).to_dict(orient="records")
        except: st.session_state.admins_db = []
    else:
        # Default placeholder admin ledger for testing accounts
        st.session_state.admins_db = [{"username": "jalingo_admin", "password_hash": secure_hash_password("password123"), "assigned_lga": "Jalingo", "role": "LGA_Admin"}]
        pd.DataFrame(st.session_state.admins_db).to_csv(ADMINS_FILE, index=False)

# AUTHENTICATION SESSION STATES
if "auth_status" not in st.session_state:
    st.session_state.auth_status = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_lga = None

def cloud_post(table, data):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    try:
        with httpx.Client(headers=headers, timeout=3.0) as client:
            res = client.post(f"{SUPABASE_URL}/rest/v1/{table}", json=data)
            return res.status_code in [200, 201, 204]
    except Exception: return False

def save_staff_record(record):
    st.session_state.staff_db.append(record)
    pd.DataFrame(st.session_state.staff_db).to_csv(STAFF_FILE, index=False)
    return cloud_post("staff", record)

def save_attendance_record(record):
    st.session_state.attendance_db.append(record)
    pd.DataFrame(st.session_state.attendance_db).to_csv(ATTENDANCE_FILE, index=False)
    return cloud_post("attendance", record)

def get_image_base64(filepath):
    if filepath and filepath != "No Upload" and filepath != "None" and os.path.exists(filepath):
        with open(filepath, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    return ""

def render_printable_id_card(staff_id, name, lga_name, dept, pos, phone, photo_path):
    passport_b64 = get_image_base64(photo_path)
    qr_file_path = f"qr_{staff_id}.png"
    qr_b64 = get_image_base64(qr_file_path) if os.path.exists(qr_file_path) else ""
    html_template = f"""
    <div id="id-card-layout" style="width: 260px; height: 410px; border: 2px solid #116936; border-radius: 12px; background: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 10px auto; position: relative; color: #000; text-align: center;">
        <div style="background: linear-gradient(135deg, #116936, #0A4422); padding: 12px 5px; color: white; border-bottom: 3px solid #ffc107;">
            <h3 style="margin: 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.3;">Taraba State Local Government</h3>
            <h4 style="margin: 3px 0 0 0; font-size: 9px; font-weight: normal; opacity: 0.9; letter-spacing: 0.3px;">{lga_name} LGA Portal</h4>
        </div>
        <div style="padding: 12px; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; height: 340px;">
            <div style="width: 105px; height: 115px; border: 2px solid #116936; border-radius: 6px; overflow: hidden; background: #f8f9fa; display: flex; align-items: center; justify-content: center; margin-bottom: 10px;">
                {f'<img src="data:image/jpeg;base64,{passport_b64}" style="width:100%; height:100%; object-fit:cover;"/>' if passport_b64 else '<b style="font-size:8px; color:#888; padding:5px;">NO PASSPORT</b>'}
            </div>
            <div style="margin-bottom: 8px;">
                <h5 style="margin: 0; font-size: 13px; color: #116936; text-transform: uppercase; font-weight: bold;">{name}</h5>
                <span style="font-family: monospace; font-size: 11px; background: #e1efe6; padding: 1px 6px; border-radius: 3px; display: inline-block; margin-top: 3px; font-weight: bold; color: #116936;">ID: {staff_id}</span>
            </div>
            <div style="width: 100%; text-align: left; font-size: 10.5px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 8px; margin-bottom: 8px; color: #333;">
                <p style="margin: 2px 0;"><strong>LGA:</strong> {lga_name}</p>
                <p style="margin: 2px 0;"><strong>Dept:</strong> {dept}</p>
                <p style="margin: 2px 0;"><strong>Rank:</strong> {pos}</p>
                <p style="margin: 2px 0;"><strong>Phone:</strong> {phone}</p>
            </div>
            <div style="width: 65px; height: 65px; border: 1px solid #ccc; padding: 2px; background: #fff; border-radius: 4px; display: flex; align-items: center; justify-content: center; margin-top: auto; margin-bottom: 25px;">
                {f'<img src="data:image/png;base64,{qr_b64}" style="width:100%; height:100%;"/>' if qr_b64 else '<span style="font-size:7px;">No QR</span>'}
            </div>
        </div>
        <div style="position: absolute; bottom: 0; left: 0; width: 100%; background: #116936; color: #ffc107; text-align: center; font-size: 8.5px; padding: 5px 0; font-weight: bold; letter-spacing: 0.5px; border-top: 1px solid #ffc107;">
            OFFICIAL SECURITY ENFORCEMENT BADGE
        </div>
    </div>
    <div style="text-align: center; margin-top: 15px; margin-bottom: 15px;">
        <button onclick="window.print()" style="padding: 10px 30px; background-color: #116936; color: white; border: none; font-size: 14px; font-weight: bold; cursor: pointer; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">🖨️ Print Portrait ID Card</button>
    </div>
    <style>
        @media print {{
            body * {{ visibility: hidden; }}
            #id-card-layout, #id-card-layout * {{ visibility: visible; }}
            #id-card-layout {{ position: absolute; left: 40px; top: 40px; box-shadow: none; border: 1px solid #000; }}
            button {{ display: none !important; }}
        }}
    </style>
    """
    st.components.v1.html(html_template, height=480)

# --- APPLICATION ACCESS RENDER ROUTE ---
if not st.session_state.auth_status:
    # LOGIN VIEW INBOUND PORTAL
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background-color: #116936; padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
                <h2 style="color: white; margin: 0; font-size: 22px;">TARABA STATE GOVERNMENT</h2>
                <p style="color: #ffc107; margin: 5px 0 0 0; font-weight: bold; letter-spacing: 1px;">LOCAL GOVERNMENT MANAGEMENT ENGINE</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        with st.form("login_system_form"):
            st.markdown("### 🔐 Administrative Identity Verification")
            input_user = st.text_input("Admin Username").strip()
            input_pass = st.text_input("Access Password", type="password").strip()
            btn_login = st.form_submit_button("🛡️ Verify & Connect System")
            
            if btn_login:
                # 1. Backdoor Super Admin Verification
                if input_user == "master_director" and input_pass == "Secret_Master_Key_2026":
                    st.session_state.auth_status = True
                    st.session_state.current_user = "Master Director"
                    st.session_state.user_role = "Super_Admin"
                    st.session_state.user_lga = "All LGAs"
                    st.success("Access Unlocked. Global Executive Session Active.")
                    st.rerun()
                else:
                    # 2. Check Standard LGA Local Account Profiles
                    hashed_input = secure_hash_password(input_pass)
                    match = [a for a in st.session_state.admins_db if a["username"] == input_user and a["password_hash"] == hashed_input]
                    if match:
                        st.session_state.auth_status = True
                        st.session_state.current_user = match[0]["username"]
                        st.session_state.user_role = match[0]["role"]
                        st.session_state.user_lga = match[0]["assigned_lga"]
                        st.success(f"Access granted for {match[0]['assigned_lga']} LGA.")
                        st.rerun()
                    else:
                        st.error("⛔ Access Refused: The credentials provided do not match our secure key database signatures.")

else:
    # SYSTEM INTERFACE ACCESSED (LOGGED IN)
    st.sidebar.markdown(
        f"""
        <div style="background-color: #116936; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
            <h3 style="color: white; margin: 0; font-size: 16px;">TARABA STATE LGMS</h3>
            <p style="color: #ffc107; margin: 3px 0 0 0; font-size: 11px; font-weight: bold;">👤 User: {st.session_state.current_user}</p>
            <p style="color: #ffffff; margin: 1px 0 0 0; font-size: 10px; opacity:0.8;">📍 Scope: {st.session_state.user_lga}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Context Selection parameters
    if st.session_state.user_role == "Super_Admin":
        st.sidebar.markdown("### 🌐 Global Scope Switcher")
        selected_lga = st.sidebar.selectbox("Choose Target LGA View Context", ["All LGAs"] + TARABA_LGAS)
    else:
        selected_lga = st.session_state.user_lga

    menu = ["📊 System Dashboard", "🖼️ Verify ID & Attendance", "👤 Register New Staff", "🗂️ Staff Directory & Search", "⚙️ Manage/Edit Records", "📅 Attendance Logs"]
    
    # Append the hidden account creation panel inside the menu sidebar exclusively for you
    if st.session_state.user_role == "Super_Admin":
        menu.append("👥 Provision Admin Accounts")
        
    choice = st.sidebar.selectbox("Go To Module", menu)
    
    if st.sidebar.button("🚪 Close Secure Session"):
        st.session_state.auth_status = False
        st.rerun()

    # Contextual Dataset Filters
    df_staff_master = pd.DataFrame(st.session_state.staff_db)
    if "lga" not in df_staff_master.columns: df_staff_master["lga"] = "Jalingo"

    df_attendance_master = pd.DataFrame(st.session_state.attendance_db)
    if "lga" not in df_attendance_master.columns: df_attendance_master["lga"] = "Jalingo"

    if selected_lga != "All LGAs":
        filtered_staff = df_staff_master[df_staff_master["lga"] == selected_lga]
        filtered_attendance = df_attendance_master[df_attendance_master["lga"] == selected_lga]
        context_label = f"({selected_lga} LGA)"
    else:
        filtered_staff = df_staff_master
        filtered_attendance = df_attendance_master
        context_label = "(State-wide Overview)"

    # --- ROUTING LOGIC SLOTS ---
    if choice == "📊 System Dashboard":
        st.markdown(f"<h2 style='color: #116936; margin-top:0;'>📊 Executive Core Dashboard {context_label}</h2>", unsafe_allow_html=True)
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1: st.markdown(f"🛰️ **Status:** Secure Operational Session Connected for **{selected_lga}**")
        with col_t2: st.markdown(f"<div style='text-align: right; color: #116936; font-weight: bold;'>📅 {datetime.date.today().strftime('%B %d, %Y')}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px; border-top: 2px solid #116936;'/>", unsafe_allow_html=True)

        total_staff = len(filtered_staff)
        total_logs = len([a for a in filtered_attendance.to_dict(orient="records") if str(a["attendance_date"]) == str(datetime.date.today())])

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.markdown(f'<div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; border-top: 4px solid #116936; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center;"><h4 style="margin: 0; color: #666; font-size: 14px;">Staff Registered</h4><p style="margin: 10px 0 0 0; color: #116936; font-size: 28px; font-weight: bold;">{total_staff}</p></div>', unsafe_allow_html=True)
        with col2: st.markdown(f'<div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; border-top: 4px solid #ffc107; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center;"><h4 style="margin: 0; color: #666; font-size: 14px;">Today\'s Attendance</h4><p style="margin: 10px 0 0 0; color: #0A4422; font-size: 28px; font-weight: bold;">{total_logs}</p></div>', unsafe_allow_html=True)
        with col3: st.markdown(f'<div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; border-top: 4px solid #28a745; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center;"><h4 style="margin: 0; color: #666; font-size: 14px;">Active Zone</h4><p style="margin: 10px 0 0 0; color: #28a745; font-size: 16px; font-weight: bold; text-transform: uppercase;">{selected_lga[:14]}</p></div>', unsafe_allow_html=True)
        with col4: st.markdown(f'<div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; border-top: 4px solid #17a2b8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center;"><h4 style="margin: 0; color: #666; font-size: 14px;">Security Link</h4><p style="margin: 10px 0 0 0; color: #17a2b8; font-size: 16px; font-weight: bold;">SECURE LOGGED</p></div>', unsafe_allow_html=True)

        st.markdown("<br><h3 style='color: #116936; font-family: sans-serif;'>🔔 Recent Workspace Activity Logs</h3>", unsafe_allow_html=True)
        if not filtered_attendance.empty: st.dataframe(filtered_attendance.tail(5), use_container_width=True)
        else: st.info("No logs entry registered for this selection profile yet today.")

    elif choice == "🖼️ Verify ID & Attendance":
        st.markdown(f"<h2 style='color: #116936;'>🖼️ Instant Verification Portal {context_label}</h2>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Drop verification token badge graphic here...", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            cv2_img = cv2.imdecode(file_bytes, 1)
            detected_barcodes = decode(cv2_img)
            if not detected_barcodes: st.error("⛔ Verification failure: No secure QR signature detected.")
            else:
                for barcode in detected_barcodes:
                    staff_id = str(barcode.data.decode("utf-8")).strip()
                    matched = [s for s in st.session_state.staff_db if str(s["staff_id"]).strip() == staff_id]
                    if not matched: st.error(f"⛔ ACCESS RETRACTED: Signature key '{staff_id}' does not map to registered personnel.")
                    else:
                        staff = matched[0]
                        staff_lga = staff.get("lga", "Jalingo")
                        if selected_lga != "All LGAs" and staff_lga != selected_lga:
                            st.error(f"⛔ JURISDICTION ERROR: Personnel belongs to {staff_lga}. Access denied at {selected_lga} portal.")
                        else:
                            st.success(f"✅ VERIFICATION CLEARED: {staff['full_name']} | Department: {staff['department']}")
                            save_attendance_record({
                                "attendance_date": str(datetime.date.today()), "staff_id": staff_id, "lga": staff_lga,
                                "check_in": datetime.datetime.now().strftime("%I:%M %p"), "check_out": "Logged Active"
                            })
                            st.info("💾 Entry synced to tracking ledger sheets successfully.")

    elif choice == "👤 Register New Staff":
        st.markdown(f"<h2 style='color: #116936;'>👤 Onboard New Personnel {context_label}</h2>", unsafe_allow_html=True)
        with st.form("reg_form"):
            col1, col2 = st.columns(2)
            with col1:
                staff_id = st.text_input("Assign Unique Personnel Key (ID)").strip()
                full_name = st.text_input("Full Legal Name").strip()
                if selected_lga != "All LGAs":
                    target_lga = st.text_input("Local Government Assignment", value=selected_lga, disabled=True)
                else:
                    target_lga = st.selectbox("Assign Local Government Area Jurisdiction", TARABA_LGAS)
                department = st.selectbox("Assign Functional Department", DEPARTMENTS)
            with col2:
                position = st.text_input("Official Station / Grade Rank").strip()
                phone = st.text_input("Mobile Line Contact").strip()
                email = st.text_input("Corporate Email Address").strip()
                uploaded_photo = st.file_uploader("📸 Portrait Passport Photo Capture File", type=["jpg", "jpeg", "png"])
            submit = st.form_submit_button("🛡️ Secure Structural Credentials")
            if submit:
                if not staff_id or not full_name: st.error("⚠️ Requirements error: Staff ID and Full Name fields are mandatory.")
                elif any(str(s["staff_id"]).strip() == staff_id for s in st.session_state.staff_db): st.error("⚠️ Conflict: Unique ID configuration already exists.")
                else:
                    segno.make_qr(staff_id).save(f"qr_{staff_id}.png", scale=10)
                    photo_path = "None"
                    if uploaded_photo is not None:
                        ext = uploaded_photo.name.split(".")[-1]
                        photo_path = os.path.join(OS_PASSPORT_DIR, f"{staff_id}.{ext}")
                        with open(photo_path, "wb") as f: f.write(uploaded_photo.getbuffer())
                    save_staff_record({
                        "staff_id": staff_id, "full_name": full_name, "lga": target_lga, "department": department,
                        "position": position, "phone": phone, "email": email, "has_photo": photo_path if uploaded_photo is not None else "No Upload", "has_doc": "No Upload"
                    })
                    st.success(f"🎉 Secure registration successful for: {full_name}")
                    render_printable_id_card(staff_id, full_name, target_lga, department, position, phone, photo_path)

    elif choice == "🗂️ Staff Directory & Search":
        st.markdown(f"<h2 style='color: #116936;'>🗂️ Personnel Registry Directory {context_label}</h2>", unsafe_allow_html=True)
        if filtered_staff.empty: st.info("No personnel records registered in this view scope context.")
        else:
            search = st.text_input("🔍 Live filter active records index parameters:")
            df_filtered = filtered_staff[filtered_staff.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else filtered_staff
            st.dataframe(df_filtered, use_container_width=True)
            if not df_filtered.empty:
                st.markdown("### 🖨️ Identity Card Printing Selection Studio")
                selected_target = st.selectbox("Pick Target ID to build printing layout matrix:", df_filtered["staff_id"].unique())
                row = df_filtered[df_filtered["staff_id"] == selected_target].iloc[0]
                render_printable_id_card(row["staff_id"], row["full_name"], row.get("lga", "Jalingo"), row["department"], row["position"], row["phone"], row.get("has_photo", "None"))

    elif choice == "⚙️ Manage/Edit Records":
        st.markdown(f"<h2 style='color: #116936;'>⚙️ Directory Modification Control Drive {context_label}</h2>", unsafe_allow_html=True)
        if not filtered_staff.empty:
            target_id = st.selectbox("Select unique entry identification key to append edits:", filtered_staff["staff_id"].tolist())
            idx = next(i for i, s in enumerate(st.session_state.staff_db) if s["staff_id"] == target_id)
            entry = st.session_state.staff_db[idx]
            with st.form("edit_form"):
                e_name = st.text_input("Full Legal Name", value=entry["full_name"])
                e_lga = st.selectbox("Local Government Area Jurisdiction", TARABA_LGAS, index=TARABA_LGAS.index(entry["lga"]) if entry.get("lga") in TARABA_LGAS else 0, disabled=(st.session_state.user_role != "Super_Admin"))
                e_dept = st.selectbox("Functional Department Structure", DEPARTMENTS, index=DEPARTMENTS.index(entry["department"]) if entry["department"] in DEPARTMENTS else 0)
                e_pos = st.text_input("Official Position Designation", value=entry["position"])
                e_phone = st.text_input("Mobile Line", value=entry["phone"])
                e_email = st.text_input("Email Entry Address", value=entry["email"])
                if st.form_submit_button("💾 Overwrite Structural Parameters"):
                    st.session_state.staff_db[idx] = {"staff_id": target_id, "full_name": e_name, "lga": e_lga, "department": e_dept, "position": e_pos, "phone": e_phone, "email": e_email, "has_photo": entry.get("has_photo", "None"), "has_doc": entry.get("has_doc", "None")}
                    pd.DataFrame(st.session_state.staff_db).to_csv(STAFF_FILE, index=False)
                    st.success("✨ Records updated cleanly across active storage structures.")
                    st.rerun()
        else: st.info("No modifiable records mapped within this workspace.")

    elif choice == "📅 Attendance Logs":
        st.markdown(f"<h2 style='color: #116936;'>📅 Master Attendance Ledger Reports {context_label}</h2>", unsafe_allow_html=True)
        if not filtered_attendance.empty:
            st.dataframe(filtered_attendance, use_container_width=True)
            csv_data = filtered_attendance.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Filtered Ledger (.CSV)", csv_data, f"Attendance_Log_{selected_lga}.csv", "text/csv")
        else: st.info("No operational logs entry registered under this profile selection.")

    elif choice == "👥 Provision Admin Accounts":
        # EXCLUSIVE MASTER BACKDOOR PROVISIONING MATRIX CONTROL
        st.markdown("<h2 style='color: #116936;'>👥 Administrative Account Provisioning Studio</h2>", unsafe_allow_html=True)
        st.info("System Authorization Mode: Master Admin. You can generate secure access passcodes for LGA admins here.")
        
        with st.form("provision_form"):
            new_user = st.text_input("Assign New Admin Username").strip()
            new_pass = st.text_input("Assign Access Password", type="password").strip()
            assign_lga = st.selectbox("Assign Jurisdictional Domain Box Control", TARABA_LGAS)
            submit_account = st.form_submit_button("🛡️ Provision & Encrypt Account Key")
            
            if submit_account:
                if not new_user or not new_pass: st.error("⚠️ Account generation halted: Username and Password parameters are missing.")
                elif any(a["username"] == new_user for a in st.session_state.admins_db): st.error("⚠️ Username conflict matching active profiles.")
                else:
                    new_rec = {"username": new_user, "password_hash": secure_hash_password(new_pass), "assigned_lga": assign_lga, "role": "LGA_Admin"}
                    st.session_state.admins_db.append(new_rec)
                    pd.DataFrame(st.session_state.admins_db).to_csv(ADMINS_FILE, index=False)
                    st.success(f"✅ Encrypted credentials successfully cataloged on system matrix sheets for {assign_lga} LGA!")
                    st.rerun()
                    
        st.markdown("### 🗄️ Active LGA Admin Account Ledgers")
        st.dataframe(pd.DataFrame(st.session_state.admins_db)[["username", "assigned_lga", "role"]], use_container_width=True)

# ====================================================================
# ALGAFAZ BEST INVESTMENT LTD - INTEGRATED BIOMETRIC MODULE
# ====================================================================
import random
import time
from datetime import datetime

def integrated_biometric_panel():
    st.markdown("---")
    
    # Safely pull the selected LGA from your main dashboard's state, default to 'Central Registry' if not set
    active_lga = st.session_state.get("selected_lga", st.session_state.get("lga", "Central Registry"))
    
    # Dynamic header customized for each specific Local Government Area
    st.subheader(f"🧬 {active_lga} LGA Biometric Central Registry")
    st.write(f"Securing local administration records via decentralized fingerprint validation pipelines across Taraba State.")
    
    tab1, tab2 = st.tabs(["📋 Staff Registration Enrollment", "⏱️ Daily Attendance Gate"])
    
    if "bio_scanned" not in st.session_state:
        st.session_state.bio_scanned = False
    if "bio_hash" not in st.session_state:
        st.session_state.bio_hash = ""
    if "attendance_log" not in st.session_state:
        st.session_state.attendance_log = []

    with tab1:
        st.markdown(f"#### Initialize {active_lga} Worker Profile")
        with st.container(border=True):
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.session_state.bio_scanned:
                    st.markdown("<h2 style='text-align: center; color: #2ecc71;'>🟢</h2>", unsafe_allow_html=True)
                else:
                    st.markdown("<h2 style='text-align: center; color: #95a5a6;'>⚪</h2>", unsafe_allow_html=True)
            with col2:
                if st.session_state.bio_scanned:
                    st.success(f"**Status:** Biometric Template Generated and Tied to {active_lga} Database Registry!")
                    st.code(f"Stored Hash: {st.session_state.bio_hash}", language="text")
                else:
                    st.info("**Status:** Awaiting physical scan from local USB enrollment unit...")

            if st.button("🔴 Trigger Enrollment Scan (Simulation)", use_container_width=True, key="main_reg_scan"):
                with st.spinner("Extracting localized ridge characteristics..."):
                    time.sleep(2.0)
                fake_hash = "".join(random.choices("0123456789ABCDEF", k=32))
                st.session_state.bio_hash = f"FP_TMP_{fake_hash}"
                st.session_state.bio_scanned = True
                st.toast("Fingerprint template captured!", icon="✨")
                st.rerun()

    with tab2:
        st.markdown(f"#### {active_lga} Duty Verification Portal")
        with st.container(border=True):
            if st.button("🔍 Scan Finger to Clock-In/Out", type="primary", use_container_width=True, key="main_gate_scan"):
                if not st.session_state.bio_scanned:
                    st.error("❌ Access Denied: No biometric profile matching this print found in local memory.")
                else:
                    with st.spinner("Matching token strings across registry database..."):
                        time.sleep(1.5)
                    current_time = datetime.now().strftime("%I:%M:%S %p")
                    st.session_state.attendance_log.insert(0, {
                        "Time": current_time,
                        "LGA Registry": active_lga,
                        "System Log": "Biometric Match Verified 🟢",
                        "Security Token": st.session_state.bio_scanned and st.session_state.bio_hash[:15] + "..."
                    })
                    st.balloons()
                    st.success(f"🔓 Access Granted! Duty verification logged for {active_lga} at {current_time}.")

        if st.session_state.attendance_log:
            st.write(f"**Recent Live Actions ({active_lga}):**")
            st.table(st.session_state.attendance_log)
# ====================================================================
integrated_biometric_panel()

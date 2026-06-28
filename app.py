import eventlet
eventlet.monkey_patch()
from flask import (Flask,render_template,request,redirect,session,flash,url_for,jsonify)
from database import db
from flask_socketio import SocketIO, join_room, emit
from bson.objectid import ObjectId
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import join_room, emit
import smtplib
import os
import bcrypt

from config import (
    MONGO_URI,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    SECRET_KEY
)

app = Flask(__name__)
app.secret_key = SECRET_KEY

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    manage_session=False
)

# ==========================
# JOIN ROOM
# ==========================

@socketio.on("join_room")
def join_chat(data):

    room = data.get("room")

    if not room:
        return

    join_room(room)

    print(f"✅ Join room: {room}")

# ==========================
# SOCKET CHAT
# ==========================

@socketio.on("send_message")
def send_chat(data):

    try:

        room = data["room"]

        doctor_id, user_id = room.split("_", 1)

        db.messages.insert_one({

            "doctor_id": doctor_id,

            "user_id": user_id,

            "sender_name": data["sender_name"],

            "sender_role": data["sender_role"],

            "message": data["message"],

            "created_at": datetime.now()

        })

        socketio.emit(

            "receive_message",

            {

                "sender_name": data["sender_name"],

                "sender_role": data["sender_role"],

                "message": data["message"]

            },

            to=room

        )

        print("✅ Emit:", room)

    except Exception as e:

        print(e)

# ==========================
# Bác sĩ nhận tin nhắn
# ==========================
@app.route("/load-messages/<doctor_id>")
def load_messages(doctor_id):

    messages=list(db.messages.find({

        "doctor_id":doctor_id,

        "user_id":str(session["user_id"])

    }).sort("created_at",1))

    result=[]

    for m in messages:

        result.append({

            "sender_name":m["sender_name"],

            "sender_role":m["sender_role"],

            "message":m["message"]

        })

    return result

# ==========================
# GỬI EMAIL
# ==========================

def send_email(to_email, subject, content):

    server = None

    try:

        msg = MIMEText(
            content,
            "plain",
            "utf-8"
        )

        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=30
        )

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(
            EMAIL_ADDRESS,
            EMAIL_PASSWORD
        )

        server.sendmail(
            EMAIL_ADDRESS,
            [to_email],
            msg.as_string()
        )

        print(f"✅ Email đã gửi tới: {to_email}")

        return True

    except smtplib.SMTPAuthenticationError:

        print("❌ Sai EMAIL_ADDRESS hoặc EMAIL_PASSWORD")

        return False

    except smtplib.SMTPConnectError:

        print("❌ Không kết nối được Gmail SMTP")

        return False

    except Exception as e:

        print(f"❌ Lỗi gửi email: {e}")

        return False

    finally:

        if server:

            try:
                server.quit()
            except:
                pass

# ==========================
# KIỂM TRA ADMIN
# ==========================

def is_admin():
    return session.get("role") == "admin"


# ==========================
# TRANG CHỦ
# ==========================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# CHỌN LOẠI ĐĂNG KÝ
# ==========================

@app.route("/register")
def register_choice():

    return render_template(
        "register_choice.html"
    )

# ==========================
# ĐĂNG KÝ NGƯỜI DÙNG
# ==========================

@app.route("/user-register", methods=["GET", "POST"])
def register():

    try:

        if request.method == "POST":

            fullname = request.form.get("fullname")
            email = request.form.get("email")
            password = request.form.get("password")

            existing_user = db.users.find_one({
                "email": email
            })

            if existing_user:

                flash("Email đã tồn tại!", "danger")
                return redirect(url_for("register"))

            hashed_password = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            )

            db.users.insert_one({

                "fullname": fullname,
                "email": email,
                "password": hashed_password,
                "role": "user"

            })

            flash(
                "Đăng ký thành công! Vui lòng đăng nhập để sử dụng hệ thống.",
                "success"
            )

            return redirect(url_for("login"))

        return render_template("register.html")

    except Exception as e:

        import traceback
        traceback.print_exc()

        flash("Có lỗi xảy ra khi đăng ký!", "danger")

        return redirect(url_for("register"))

# ==========================
# ĐĂNG KÝ TÀI KHOẢN BÁC SĨ
# ==========================
@app.route("/doctor-register", methods=["GET", "POST"])
def doctor_register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        specialty = request.form["specialty"]
        phone = request.form["phone"]
        clinic_address = request.form["clinic_address"]

        experience = request.form["experience"] + " năm"

        existing_user = db.users.find_one({
            "email": email
        })

        if existing_user:
            return """
            <script>
                alert('Email đã tồn tại!');
                window.location='/doctor-register';
            </script>
            """

        image_path = ""

        if "image" in request.files:

            image = request.files["image"]

            if image.filename != "":

                filename = secure_filename(image.filename)

                upload_folder = os.path.join(
                    app.root_path,
                    "static",
                    "uploads",
                    "doctors"
                )

                os.makedirs(
                    upload_folder,
                    exist_ok=True
                )

                image.save(
                    os.path.join(
                        upload_folder,
                        filename
                    )
                )

                image_path = (
                    "/static/uploads/doctors/" +
                    filename
                )

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        db.users.insert_one({

            "fullname": fullname,
            "email": email,
            "password": hashed_password,

            "role": "doctor_pending",

            "specialty": specialty,
            "phone": phone,
            "clinic_address": clinic_address,
            "experience": experience,

            "image": image_path,

            "created_at": datetime.now()

        })

        return """
        <script>
            alert('Đăng ký hồ sơ bác sĩ thành công. Vui lòng chờ quản trị viên xét duyệt.');
            window.location='/login';
        </script>
        """

    specialties = list(
        db.specialties.find()
    )

    return render_template(
        "doctor_register.html",
        specialties=specialties
    )

# ==========================
# ĐĂNG NHẬP
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = db.users.find_one({
            "email": email
        })

        if user and bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"]
        ):

            if user.get("role") == "doctor_pending":

                return render_template(
                    "login.html",
                    error="Tài khoản bác sĩ đang chờ Admin duyệt!"
                )

            session["user_id"] = str(user["_id"])
            session["fullname"] = user["fullname"]
            session["role"] = user.get("role", "user")

            if user.get("role") == "admin":
                return redirect("/dashboard")

            elif user.get("role") == "doctor":
                return redirect("/doctor-dashboard")

            else:
                return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Sai email hoặc mật khẩu!"
        )

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    role = session.get("role")

    if role == "admin":
        return redirect("/admin-dashboard")

    elif role == "doctor":
        return redirect("/doctor-dashboard")

    else:
        return redirect("/user-dashboard")

# ==========================
# ADMIN DASHBOARD
# ==========================

@app.route("/admin-dashboard")
def admin_dashboard():

    # Kiểm tra đăng nhập
    if "user_id" not in session:
        return redirect("/login")

    # Chỉ Admin được truy cập
    if session.get("role") != "admin":
        return redirect("/dashboard")

    # Tổng số bác sĩ
    doctor_count = db.doctors.count_documents({})

    # Tổng số phòng khám
    clinic_count = db.clinics.count_documents({})

    # Tổng số lịch khám
    appointment_count = db.appointments.count_documents({})

    # Ngày hiện tại
    today = datetime.now().strftime("%Y-%m-%d")

    # Lịch khám hôm nay
    today_appointments = db.appointments.count_documents({
        "date": today
    })

    # Thống kê lịch khám theo tháng
    months = [0] * 12

    appointments = db.appointments.find()

    for appt in appointments:

        try:
            month = int(appt["date"].split("-")[1])
            months[month - 1] += 1

        except Exception:
            pass

    return render_template(
        "admin_dashboard.html",
        fullname=session["fullname"],
        doctor_count=doctor_count,
        clinic_count=clinic_count,
        appointment_count=appointment_count,
        today_appointments=today_appointments,
        months=months
    )

# ==========================
# USER DASHBOARD
# ==========================

@app.route("/user-dashboard")
def user_dashboard():

    # Chưa đăng nhập
    if "user_id" not in session:
        return redirect("/login")

    # Chỉ tài khoản user được vào
    if session.get("role") != "user":
        return redirect("/login")

    reminders = []

    now = datetime.now()

    appointments = db.appointments.find({
        "user_id": session["user_id"]
    })

    for appt in appointments:

        try:

            appointment_datetime = datetime.strptime(
                f"{appt['date']} {appt['time']}",
                "%Y-%m-%d %H:%M"
            )

            time_left = appointment_datetime - now

            # Lịch đã qua
            if time_left.total_seconds() < 0:
                continue

            days_left = time_left.days
            hours_left = int(time_left.total_seconds() // 3600)
            minutes_left = int(time_left.total_seconds() // 60)

            # -----------------------
            # Nội dung thông báo
            # -----------------------

            if days_left == 3:

                message = "📅 Còn 3 ngày nữa đến lịch khám."

            elif days_left == 1:

                message = "📅 Ngày mai bạn có lịch khám."

            elif days_left == 0 and hours_left >= 1:

                message = f"⏰ Hôm nay còn khoảng {hours_left} giờ nữa đến lịch khám."

            elif 0 <= minutes_left <= 60:

                message = "🚨 Đã đến giờ khám!"

            else:
                continue

            reminders.append({

                "doctor": appt["doctor"],
                "date": appt["date"],
                "time": appt["time"],
                "message": message

            })

        except Exception as e:
            print("Dashboard:", e)

    return render_template(

        "user_dashboard.html",

        fullname=session["fullname"],

        reminders=reminders,

        notification_count=len(reminders)

    )

# ==========================
# DASHBOARD BÁC SĨ
# ==========================

@app.route("/doctor-dashboard")
def doctor_dashboard():

    # Kiểm tra đăng nhập
    if "user_id" not in session:
        return redirect("/login")

    # Chỉ bác sĩ được truy cập
    if session.get("role") != "doctor":
        return redirect("/login")

    # Lấy tài khoản đang đăng nhập
    user = db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    if not user:
        return redirect("/logout")

    # Tìm hồ sơ bác sĩ
    doctor = db.doctors.find_one({
        "email": user["email"]
    })

    if not doctor:
        return "<h3>Không tìm thấy hồ sơ bác sĩ</h3>"

    # ==========================
    # THỐNG KÊ
    # ==========================

    # Tổng lịch khám
    appointment_count = db.appointments.count_documents({
        "doctor_id": str(doctor["_id"])
    })

    # Đếm số bệnh nhân đã nhắn tin
    patient_ids = db.messages.distinct(
        "user_id",
        {
            "doctor_id": str(doctor["_id"])
        }
    )

    message_count = len(patient_ids)

    # Đếm số thuốc đã đăng
    medicine_count = db.medicines.count_documents({
        "doctor_id": str(doctor["_id"])
    })

    return render_template(
        "doctor_dashboard.html",
        doctor=doctor,
        appointment_count=appointment_count,
        message_count=message_count,
        medicine_count=medicine_count
    )

# ==========================
# NHẮC LỊCH CHO BÁC SĨ
# ==========================

def check_doctor_appointments():

    now = datetime.now()

    appointments = db.appointments.find()

    for appt in appointments:

        try:

            appointment_datetime = datetime.strptime(
                appt["date"] + " " + appt["time"],
                "%Y-%m-%d %H:%M"
            )

            time_left = appointment_datetime - now

            days_left = time_left.days

            seconds_left = time_left.total_seconds()

            doctor_email = appt.get("doctor_email")

            if not doctor_email:
                continue

            subject = ""
            content = ""

            # ======================
            # TRƯỚC 3 NGÀY
            # ======================

            if (
                2 <= days_left <= 3
                and not appt.get("doctor_email_3days")
            ):

                subject = "Nhắc lịch khám sau 3 ngày"

                content = f"""
Xin chào Bác sĩ {appt['doctor']}

Sau khoảng 3 ngày bạn có lịch khám.

Bệnh nhân:
{appt['patient']}

Ngày:
{appt['date']}

Giờ:
{appt['time']}
"""

                send_email(
                    doctor_email,
                    subject,
                    content
                )

                db.appointments.update_one(
                    {"_id": appt["_id"]},
                    {
                        "$set":{
                            "doctor_email_3days":True
                        }
                    }
                )

            # ======================
            # TRƯỚC 1 NGÀY
            # ======================

            elif (
                0 <= days_left <= 1
                and not appt.get("doctor_email_1day")
            ):

                subject = "Nhắc lịch khám ngày mai"

                content = f"""
Xin chào Bác sĩ {appt['doctor']}

Ngày mai bạn có lịch khám.

Bệnh nhân:
{appt['patient']}

Ngày:
{appt['date']}

Giờ:
{appt['time']}
"""

                send_email(
                    doctor_email,
                    subject,
                    content
                )

                db.appointments.update_one(
                    {"_id": appt["_id"]},
                    {
                        "$set":{
                            "doctor_email_1day":True
                        }
                    }
                )

            # ======================
            # ĐÚNG NGÀY
            # ======================

            elif (
                days_left == 0
                and seconds_left > 3600
                and not appt.get("doctor_email_today")
            ):

                subject = "Hôm nay có lịch khám"

                content = f"""
Xin chào Bác sĩ {appt['doctor']}

Hôm nay bạn có lịch khám.

Bệnh nhân:
{appt['patient']}

Giờ:
{appt['time']}
"""

                send_email(
                    doctor_email,
                    subject,
                    content
                )

                db.appointments.update_one(
                    {"_id": appt["_id"]},
                    {
                        "$set":{
                            "doctor_email_today":True
                        }
                    }
                )

            # ======================
            # TRƯỚC 30 PHÚT
            # ======================

            elif (
                0 <= seconds_left <= 1800
                and not appt.get("doctor_email_30minutes")
            ):

                subject = "Sắp đến giờ khám"

                content = f"""
Xin chào Bác sĩ {appt['doctor']}

Chỉ còn khoảng 30 phút nữa sẽ đến lịch khám.

Bệnh nhân:
{appt['patient']}

Giờ khám:
{appt['time']}
"""

                send_email(
                    doctor_email,
                    subject,
                    content
                )

                db.appointments.update_one(
                    {"_id": appt["_id"]},
                    {
                        "$set":{
                            "doctor_email_30minutes":True
                        }
                    }
                )

        except Exception as e:

            print("Lỗi nhắc lịch bác sĩ:", e)

# ==========================
# DANH SÁCH BÁC SĨ CHỜ DUYỆT
# ==========================

@app.route("/doctor-requests")
def doctor_requests():

    # Kiểm tra đăng nhập
    if "user_id" not in session:
        return redirect("/login")

    # Chỉ admin mới được truy cập
    if session.get("role") != "admin":
        return "<h3>Không có quyền truy cập</h3>"

    # Lấy danh sách bác sĩ chờ duyệt
    doctors = list(
        db.users.find({
            "role": "doctor_pending"
        })
    )

    return render_template(
        "doctor_requests.html",
        doctors=doctors
    )
    
# ==========================
# DUYỆT TÀI KHOẢN BÁC SĨ
# ==========================

@app.route("/approve-doctor/<user_id>")
def approve_doctor(user_id):

        if "user_id" not in session:
            return redirect("/login")

        if session.get("role") != "admin":
            return "<h3>Không có quyền truy cập</h3>"

        doctor = db.users.find_one({
            "_id": ObjectId(user_id)
        })

        if doctor:

            # Cập nhật quyền
            db.users.update_one(
                {
                    "_id": ObjectId(user_id)
                },
                {
                    "$set": {
                        "role": "doctor"
                    }
                }
            )

            # Kiểm tra đã tồn tại trong collection doctors chưa
            existing_doctor = db.doctors.find_one({
                "user_id": str(doctor["_id"])
            })

            if not existing_doctor:

                db.doctors.insert_one({

                    "user_id": str(doctor["_id"]),

                    "name": doctor.get("fullname", ""),

                    "specialty": doctor.get("specialty", ""),

                    "phone": doctor.get("phone", ""),

                    "email": doctor.get("email", ""),

                    "experience": doctor.get("experience", ""),

                    # Địa chỉ phòng khám
                    "clinic": doctor.get("clinic_address", "")

                })

        return redirect("/doctor-requests")

# ==========================
# ĐĂNG XUẤT
# ==========================

@app.route("/logout")
def logout():

        session.clear()
        return redirect("/")

# ==========================
# DANH SÁCH CHUYÊN KHOA
# ==========================

@app.route("/specialties")
def specialties():

    specialties = list(
        db.specialties.find()
    )

    return render_template(
        "specialty_list.html",
        specialties=specialties
    )


# ==========================
# THÊM CHUYÊN KHOA
# ==========================

@app.route("/specialties/add", methods=["GET", "POST"])
def add_specialty():

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    if request.method == "POST":

        db.specialties.insert_one({
            "name": request.form["name"]
        })

        return redirect("/specialties")

    return render_template("add_specialty.html")

# ==========================
# SỬA CHUYÊN KHOA
# ==========================
@app.route("/specialties/edit/<id>", methods=["GET", "POST"])
def edit_specialty(id):

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    specialty = db.specialties.find_one({
        "_id": ObjectId(id)
    })

    if request.method == "POST":

        db.specialties.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "name": request.form["name"]
                }
            }
        )

        return redirect("/specialties")

    return render_template(
        "edit_specialty.html",
        specialty=specialty
    )


# ==========================
# XÓA CHUYÊN KHOA
# ==========================
@app.route("/specialties/delete/<id>")
def delete_specialty(id):

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    db.specialties.delete_one({
        "_id": ObjectId(id)
    })

    return redirect("/specialties")


# ==========================
# DANH SÁCH PHÒNG KHÁM
# ==========================
@app.route("/clinics")
def clinics():

    clinics = list(
        db.clinics.find()
    )

    return render_template(
        "clinic_list.html",
        clinics=clinics
    )


# ==========================
# THÊM PHÒNG KHÁM
# ==========================
@app.route("/clinics/add", methods=["GET", "POST"])
def add_clinic():

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    if request.method == "POST":

        db.clinics.insert_one({

            "name": request.form["name"],

            "address": request.form["address"],

            "phone": request.form["phone"],

            "specialty": request.form["specialty"],

            "lat": request.form["lat"],

            "lng": request.form["lng"]

        })

        return redirect("/clinics")

    specialties = list(
        db.specialties.find()
    )

    return render_template(
        "add_clinic.html",
        specialties=specialties
    )


# ==========================
# SỬA PHÒNG KHÁM
# ==========================
@app.route("/clinics/edit/<id>", methods=["GET", "POST"])
def edit_clinic(id):

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    clinic = db.clinics.find_one({
        "_id": ObjectId(id)
    })

    if request.method == "POST":

        db.clinics.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "name": request.form["name"],
                    "address": request.form["address"],
                    "phone": request.form["phone"]
                }
            }
        )

        return redirect("/clinics")

    return render_template(
        "edit_clinic.html",
        clinic=clinic
    )


# ==========================
# XÓA PHÒNG KHÁM
# ==========================
@app.route("/clinics/delete/<id>")
def delete_clinic(id):

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    db.clinics.delete_one({
        "_id": ObjectId(id)
    })

    return redirect("/clinics")


# ==========================
# DANH SÁCH BÁC SĨ (ADMIN)
# ==========================

@app.route("/doctors")
def doctors():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/dashboard")

    doctors = list(db.doctors.find().sort("name", 1))

    return render_template(
        "doctor_list.html",
        doctors=doctors
    )


# ==========================
# DANH SÁCH BÁC SĨ (USER)
# ==========================

@app.route("/doctor-list")
def doctor_list():

    if "user_id" not in session:
        return redirect("/login")

    doctors = list(db.doctors.find().sort("name", 1))

    for doctor in doctors:
        print(doctor)

    return render_template(
        "doctor_list_user.html",
        doctors=doctors
    )

# ==========================
# THÊM BÁC SĨ
# ==========================
@app.route("/doctors/add", methods=["GET", "POST"])
def add_doctor():

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    if request.method == "POST":

        name = request.form["name"]
        specialty = request.form["specialty"]
        clinic = request.form["clinic"]
        phone = request.form["phone"]
        email = request.form["email"]
        experience = request.form["experience"]

        # ==========================
        # Upload ảnh bác sĩ
        # ==========================

        image = request.files.get("image")

        image_path = ""

        if image and image.filename != "":

            filename = secure_filename(image.filename)

            upload_folder = os.path.join(
                app.root_path,
                "static",
                "uploads",
                "doctors"
            )

            os.makedirs(upload_folder, exist_ok=True)

            image.save(
                os.path.join(upload_folder, filename)
            )

            image_path = f"/static/uploads/doctors/{filename}"

        db.doctors.insert_one({

            "name": name,
            "specialty": specialty,
            "clinic": clinic,
            "phone": phone,
            "email": email,
            "experience": experience,
            "image": image_path

        })

        flash("Thêm bác sĩ thành công!", "success")

        return redirect("/doctors")

    specialties = list(db.specialties.find())
    clinics = list(db.clinics.find())

    return render_template(
        "add_doctor.html",
        specialties=specialties,
        clinics=clinics
    )

# ==========================
# SỬA BÁC SĨ
# ==========================
@app.route("/doctors/edit/<id>", methods=["GET", "POST"])
def edit_doctor(id):

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    doctor = db.doctors.find_one({
        "_id": ObjectId(id)
    })

    if not doctor:
        return "<h3>Không tìm thấy bác sĩ</h3>"

    specialties = list(db.specialties.find())
    clinics = list(db.clinics.find())

    if request.method == "POST":

        image_path = doctor.get("image", "")

        file = request.files.get("image")

        if file and file.filename != "":

            filename = secure_filename(file.filename)

            upload_folder = os.path.join(
                app.root_path,
                "static",
                "uploads",
                "doctors"
            )

            os.makedirs(upload_folder, exist_ok=True)

            save_path = os.path.join(
                upload_folder,
                filename
            )

            file.save(save_path)

            image_path = f"/static/uploads/doctors/{filename}"

        db.doctors.update_one(
            {
                "_id": ObjectId(id)
            },
            {
                "$set": {
                    "name": request.form["name"],
                    "specialty": request.form["specialty"],
                    "clinic": request.form["clinic"],
                    "phone": request.form["phone"],
                    "email": request.form["email"],
                    "experience": request.form["experience"],
                    "image": image_path
                }
            }
        )

        flash("Cập nhật bác sĩ thành công!", "success")

        return redirect("/doctors")

    return render_template(
        "edit_doctor.html",
        doctor=doctor,
        specialties=specialties,
        clinics=clinics
    )

# ==========================
# XÓA BÁC SĨ
# ==========================
@app.route("/doctors/delete/<id>")
def delete_doctor(id):

    if not is_admin():
        return "<h3>Không có quyền truy cập</h3>"

    db.doctors.delete_one({
        "_id": ObjectId(id)
    })

    return redirect("/doctors")

# ==========================
# THÊM LỊCH KHÁM
# ==========================

@app.route("/appointments/add", methods=["GET", "POST"])
def add_appointment():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        patient = request.form["patient"]
        doctor = request.form["doctor"]
        date = request.form["date"]
        time = request.form["time"]

        # ==========================
        # KIỂM TRA NGÀY KHÁM
        # ==========================

        today = datetime.now().date()

        selected_date = datetime.strptime(
            date,
            "%Y-%m-%d"
        ).date()

        if selected_date < today:

            flash(
                "Không thể đặt lịch trước ngày hiện tại!",
                "danger"
            )

            return redirect("/appointments/add")

        # ==========================
        # THÔNG TIN BÁC SĨ
        # ==========================

        doctor_info = db.doctors.find_one({

            "name": doctor

        })

        if not doctor_info:

            flash(
                "Không tìm thấy bác sĩ.",
                "danger"
            )

            return redirect("/appointments/add")

        # ==========================
        # THÔNG TIN NGƯỜI DÙNG
        # ==========================

        user = db.users.find_one({

            "_id": ObjectId(session["user_id"])

        })

        if not user:

            flash(
                "Không tìm thấy tài khoản.",
                "danger"
            )

            return redirect("/login")

        # ==========================
        # KIỂM TRA TRÙNG LỊCH
        # ==========================

        existed = db.appointments.find_one({

            "doctor": doctor,
            "date": date,
            "time": time

        })

        if existed:

            flash(
                "Khung giờ này của bác sĩ đã có người đặt. Vui lòng chọn thời gian khác!",
                "danger"
            )

            return redirect("/appointments/add")

        # ==========================
        # LƯU LỊCH KHÁM
        # ==========================

        appointment = {

            "patient": patient,

            "doctor": doctor,

            "doctor_id": str(doctor_info["_id"]),

            "doctor_email": doctor_info.get("email", ""),

            "user_id": str(session["user_id"]),

            "user_email": user["email"],

            "date": date,

            "time": time,

            "doctor_reminder_sent": False,

            "user_reminder_sent": False,

            "created_at": datetime.now()

        }

        db.appointments.insert_one(appointment)

        # ==========================
        # GỬI EMAIL XÁC NHẬN
        # ==========================

        subject = "Xác nhận đặt lịch khám"

        content = f"""
Xin chào {user['fullname']},

Bạn đã đặt lịch khám thành công.

==============================

Bệnh nhân:
{patient}

Bác sĩ:
{doctor}

Ngày khám:
{date}

Giờ khám:
{time}

==============================

Vui lòng đến trước 15 phút.

Health Booking System
"""

        email_ok = send_email(

            user["email"],

            subject,

            content

        )

        if email_ok:

            flash(
                "Đặt lịch thành công! Email xác nhận đã được gửi.",
                "success"
            )

        else:

            flash(
                "Đặt lịch thành công nhưng không gửi được email.",
                "warning"
            )

        return redirect("/appointments")

    # ==========================
    # HIỂN THỊ FORM
    # ==========================

    doctors = list(
        db.doctors.find()
    )

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    return render_template(

        "add_appointment.html",

        doctors=doctors,

        today=today

    )

# ==========================
# DANH SÁCH LỊCH KHÁM
# ==========================
@app.route("/appointments")
def appointments():

    if "user_id" not in session:
        return redirect("/login")

    if is_admin():

        appointments = list(
            db.appointments.find()
        )

    else:

        appointments = list(
            db.appointments.find({
                "user_id": session["user_id"]
            })
        )

    return render_template(
        "appointment_list.html",
        appointments=appointments
    )

# ==========================
# KIỂM TRA LỊCH KHÁM
# ==========================

def check_appointments():

    today = datetime.now().date()

    appointments = db.appointments.find()

    for appt in appointments:

        try:

            appointment_date = datetime.strptime(
                appt["date"],
                "%Y-%m-%d"
            ).date()

            days_left = (
                appointment_date - today
            ).days

            # Chỉ nhắc 3 ngày, 1 ngày và đúng ngày khám
            if days_left in [3, 1, 0]:

                # Kiểm tra đã gửi email chưa
                already_sent = appt.get(
                    f"email_sent_{days_left}",
                    False
                )

                if already_sent:
                    continue

                user = db.users.find_one({
                    "_id": ObjectId(
                        appt["user_id"]
                    )
                })

                if not user:
                    continue

                subject = "Nhắc lịch khám"

                if days_left == 0:

                    content = f"""
Xin chào {user['fullname']}

Hôm nay bạn có lịch khám.

Bác sĩ:
{appt['doctor']}

Thời gian:
{appt['time']}

Ngày:
{appt['date']}
"""

                else:

                    content = f"""
Xin chào {user['fullname']}

Còn {days_left} ngày nữa bạn có lịch khám.

Bác sĩ:
{appt['doctor']}

Ngày:
{appt['date']}

Giờ:
{appt['time']}
"""

                # Gửi email
                send_email(
                    user["email"],
                    subject,
                    content
                )

                # Đánh dấu đã gửi
                db.appointments.update_one(
                    {
                        "_id": appt["_id"]
                    },
                    {
                        "$set": {
                            f"email_sent_{days_left}": True
                        }
                    }
                )

        except Exception as e:

            print("Lỗi lịch khám:", e)

# ==========================
# SỬA LỊCH KHÁM
# ==========================
@app.route("/appointments/edit/<id>", methods=["GET", "POST"])
def edit_appointment(id):

    if "user_id" not in session:
        return redirect("/login")

    if is_admin():

        appointment = db.appointments.find_one({
            "_id": ObjectId(id)
        })

    else:

        appointment = db.appointments.find_one({
            "_id": ObjectId(id),
            "user_id": session["user_id"]
        })

        if not appointment:
            return redirect("/appointments")

    doctors = list(
        db.doctors.find()
    )

    if request.method == "POST":

        db.appointments.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "patient": request.form["patient"],
                    "doctor": request.form["doctor"],
                    "date": request.form["date"],
                    "time": request.form["time"]
                }
            }
        )

        return redirect("/appointments")

    return render_template(
        "edit_appointment.html",
        appointment=appointment,
        doctors=doctors
    )


# ==========================
# XÓA LỊCH KHÁM
# ==========================
@app.route("/appointments/delete/<id>")
def delete_appointment(id):

    if "user_id" not in session:
        return redirect("/login")

    if is_admin():

        db.appointments.delete_one({
            "_id": ObjectId(id)
        })

    else:

        db.appointments.delete_one({
            "_id": ObjectId(id),
            "user_id": session["user_id"]
        })

    return redirect("/appointments")

# ==========================
# BẢN ĐỒ PHÒNG KHÁM
# ==========================

@app.route("/map")
def clinic_map():

    clinics = list(
        db.clinics.find()
    )

    specialties = list(
        db.specialties.find()
    )

    return render_template(
        "map.html",
        clinics=clinics,
        specialties=specialties
    )

# ==========================
# LỊCH KHÁM CỦA BÁC SĨ
# ==========================

@app.route("/doctor-appointments")
def doctor_appointments():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "doctor":
        return redirect("/login")

    appointments = list(
        db.appointments.find({
            "doctor_id": str(session["user_id"])
        })
    )

    return render_template(
        "doctor_appointments.html",
        appointments=appointments
    )
  
# ===========================================
# TƯ VẤN CHUYÊN KHOA
# ===========================================

@app.route("/symptom-checker", methods=["GET", "POST"])
def symptom_checker():

    if "user_id" not in session:
        return redirect("/login")

    if "chat_history" not in session:
        session["chat_history"] = []

    recommendation = None
    top_specialties = []

    if request.method == "POST":

        symptom = request.form.get("symptom", "").lower().strip()

        specialty = "Đa khoa"

        # ==========================
        # Xác định chuyên khoa
        # ==========================

        if any(x in symptom for x in [
            "tim",
            "đau ngực",
            "cao huyết áp",
            "hồi hộp"
        ]):
            specialty = "Tim mạch"

        elif any(x in symptom for x in [
            "da",
            "mụn",
            "dị ứng",
            "ngứa",
            "nấm"
        ]):
            specialty = "Da liễu"

        elif any(x in symptom for x in [
            "mắt",
            "mờ",
            "đỏ mắt",
            "cận"
        ]):
            specialty = "Mắt"

        elif any(x in symptom for x in [
            "tai",
            "mũi",
            "họng",
            "viêm họng",
            "ho"
        ]):
            specialty = "Tai Mũi Họng"

        elif any(x in symptom for x in [
            "bụng",
            "dạ dày",
            "tiêu chảy",
            "đầy hơi"
        ]):
            specialty = "Tiêu hóa"

        elif any(x in symptom for x in [
            "xương",
            "khớp",
            "đau lưng",
            "gãy"
        ]):
            specialty = "Cơ xương khớp"

        recommendation = (
            f"Dựa trên triệu chứng của bạn, "
            f"nên khám chuyên khoa {specialty}."
        )

        # ==========================
        # Lấy bác sĩ phù hợp
        # ==========================

        top_specialties = list(
            db.doctors.find({
                "specialty": {
                    "$regex": specialty,
                    "$options": "i"
                }
            })
        )

        # ==========================
        # Lưu lịch sử chat
        # ==========================

        history = session["chat_history"]

        history.append({

            "question": symptom,

            "answer": recommendation,

            "time": datetime.now().strftime("%H:%M")

        })

        session["chat_history"] = history

    return render_template(

        "symptom_checker.html",

        chat_history=session.get("chat_history", []),

        recommendation=recommendation,

        top_specialties=top_specialties

    )


# ==========================
# XÓA LỊCH SỬ CHAT
# ==========================

@app.route("/clear-chat")
def clear_chat():

    session.pop("chat_history", None)

    return redirect("/symptom-checker")
    
# ==========================
# CHAT CHI TIẾT (BỆNH NHÂN)
# ==========================

@app.route("/chat/<doctor_id>", methods=["GET", "POST"])
def chat_room(doctor_id):

        if "user_id" not in session:
            return redirect("/login")

        try:
            doctor = db.doctors.find_one({
                "_id": ObjectId(doctor_id)
            })

        except Exception as e:
            return f"Lỗi ObjectId: {e}"

        if not doctor:
            return f"Không tìm thấy bác sĩ với ID: {doctor_id}"

# ==========================
# TỰ ĐỘNG GỬI YÊU CẦU TƯ VẤN THUỐC
# ==========================

        consult_medicine = session.get("consult_medicine")

        if consult_medicine:

            existed = db.messages.find_one({
                "doctor_id": doctor_id,
                "user_id": str(session["user_id"]),
                "message": f"Tôi muốn tư vấn về thuốc: {consult_medicine['medicine_name']}"
            })

            if not existed:

                db.messages.insert_one({
                    "doctor_id": doctor_id,
                    "user_id": str(session["user_id"]),
                    "sender_name": session["fullname"],
                    "sender_role": "user",
                    "message": f"Tôi muốn tư vấn về thuốc: {consult_medicine['medicine_name']}",
                    "created_at": datetime.now()
                })

            session.pop("consult_medicine", None)

# ==========================
# GỬI TIN NHẮN THỦ CÔNG
# ==========================

        if request.method == "POST":

            db.messages.insert_one({
                "doctor_id": doctor_id,
                "user_id": str(session["user_id"]),
                "sender_name": session["fullname"],
                "sender_role": session["role"],
                "message": request.form["message"],
                "created_at": datetime.now()
            })

            return redirect(f"/chat/{doctor_id}")

# ==========================
# LỊCH SỬ CHAT
# ==========================

        messages = list(
            db.messages.find({
                "doctor_id": doctor_id,
                "user_id": str(session["user_id"])
            }).sort("created_at", 1)
        )

        return render_template(
            "chat_room.html",
            doctor=doctor,
            messages=messages
        )

# ==========================
# DANH SÁCH BÁC SĨ ĐỂ CHAT
# ==========================

@app.route("/chat-doctor")
def chat_doctor():

        if "user_id" not in session:
            return redirect("/login")

        doctors = list(db.doctors.find())

        consult_medicine = session.get(
            "consult_medicine"
        )

        return render_template(
            "chat.html",
            doctors=doctors,
            consult_medicine=consult_medicine
        )


# ==========================
# TIN NHẮN BÁC SĨ
# ==========================

@app.route("/doctor-messages")
def doctor_messages():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "doctor":
        return redirect("/login")

    user = db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    if not user:
        return "<h3>Không tìm thấy tài khoản bác sĩ</h3>"

    doctor = db.doctors.find_one({
        "email": user["email"]
    })

    if not doctor:
        return "<h3>Không tìm thấy hồ sơ bác sĩ</h3>"

    conversations = list(
        db.messages.aggregate([
            {
                "$match": {
                    "doctor_id": str(doctor["_id"])
                }
            },
            {
                "$sort": {
                    "created_at": 1
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "sender_name": {
                        "$last": "$sender_name"
                    },
                    "last_message": {
                        "$last": "$message"
                    },
                    "created_at": {
                        "$last": "$created_at"
                    }
                }
            },
            {
                "$sort": {
                    "created_at": -1
                }
            }
        ])
    )

    return render_template(
        "doctor_messages.html",
        doctor=doctor,
        conversations=conversations
    )

# ==========================
# CHAT CỦA BÁC SĨ VỚI BỆNH NHÂN
# ==========================

@app.route("/doctor-chat/<user_id>", methods=["GET", "POST"])
def doctor_chat(user_id):

        if "user_id" not in session:
            return redirect("/login")

        if session.get("role") != "doctor":
            return redirect("/login")

        # Tài khoản bác sĩ đang đăng nhập
        user = db.users.find_one({
            "_id": ObjectId(session["user_id"])
        })

        if not user:
            return "<h3>Không tìm thấy tài khoản bác sĩ</h3>"

        # Hồ sơ bác sĩ
        doctor = db.doctors.find_one({
            "email": user["email"]
        })

        if not doctor:
            return "<h3>Không tìm thấy hồ sơ bác sĩ</h3>"

        # Thông tin bệnh nhân
        patient = db.users.find_one({
            "_id": ObjectId(user_id)
        })

        if not patient:
            return "<h3>Không tìm thấy bệnh nhân</h3>"

        # Gửi tin nhắn
        if request.method == "POST":

            db.messages.insert_one({
                "doctor_id": str(doctor["_id"]),
                "user_id": user_id,
                "sender_name": session["fullname"],
                "sender_role": "doctor",
                "message": request.form["message"],
                "created_at": datetime.now()
            })

            return redirect(f"/doctor-chat/{user_id}")

        # Lấy lịch sử chat
        messages = list(
            db.messages.find({
                "doctor_id": str(doctor["_id"]),
                "user_id": user_id
            }).sort("created_at", 1)
        )

        return render_template(
            "doctor_chat.html",
            doctor=doctor,
            patient=patient,
            messages=messages
        )

# ==========================
# HỒ SƠ BÁC SĨ
# ==========================

@app.route("/doctor-profile", methods=["GET", "POST"])
def doctor_profile():

        if "user_id" not in session:
            return redirect("/login")

        if session.get("role") != "doctor":
            return redirect("/login")

        # Tài khoản đăng nhập
        user = db.users.find_one({
            "_id": ObjectId(session["user_id"])
        })

        if not user:
            return redirect("/logout")

        # Hồ sơ bác sĩ
        doctor = db.doctors.find_one({
            "email": user["email"]
        })

        if not doctor:
            return "<h3>Không tìm thấy hồ sơ bác sĩ</h3>"

        if request.method == "POST":

            db.doctors.update_one(
                {
                    "_id": doctor["_id"]
                },
                {
                    "$set": {
                        "phone": request.form["phone"],
                        "specialty": request.form["specialty"],
                        "experience": request.form["experience"],
                        "clinic": request.form["clinic"]
                    }
                }
            )

            return """
            <script>
                alert('Cập nhật hồ sơ thành công!');
                window.location.href='/doctor-profile';
            </script>
            """

        return render_template(
            "doctor_profile.html",
            doctor=doctor
        )

# ==========================
# THÊM THUỐC
# ==========================

@app.route("/add-medicine", methods=["GET", "POST"])
def add_medicine():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "doctor":
        return redirect("/login")

    user = db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    doctor = db.doctors.find_one({
        "email": user["email"]
    })

    if request.method == "POST":

        image = request.files["image"]

        image_path = ""

        if image and image.filename != "":

            filename = secure_filename(image.filename)

            os.makedirs(
                "static/uploads/medicines",
                exist_ok=True
            )

            image.save(
                os.path.join(
                    "static/uploads/thuoc",
                    filename
                )
            )

            image_path = "/static/uploads/thuoc/" + filename

        db.medicines.insert_one({

            "doctor_id": str(doctor["_id"]),
            "doctor_name": doctor["name"],

            "name": request.form["name"],

            "price": int(request.form["price"]),

            "quantity": int(request.form["quantity"]),

            "description": request.form["description"],

            "image": image_path,

            "created_at": datetime.now()

        })

        return """
        <script>
            alert('Đăng thuốc thành công!');
            window.location.href='/my-medicines';
        </script>
        """

    return render_template(
        "add_medicine.html"
    )

# ==========================
# SỬA THUỐC
# ==========================

@app.route("/edit-medicine/<medicine_id>", methods=["GET", "POST"])
def edit_medicine(medicine_id):

    if "user_id" not in session:
        return redirect("/login")

    medicine = db.medicines.find_one({
        "_id": ObjectId(medicine_id)
    })

    if not medicine:
        return "<h3>Không tìm thấy thuốc</h3>"

    if request.method == "POST":

        image_path = medicine.get("image", "")

        file = request.files.get("image")

        if file and file.filename != "":

            filename = secure_filename(file.filename)

            os.makedirs(
                "static/uploads/thuoc",
                exist_ok=True
            )

            save_path = os.path.join(
                "static/uploads/thuocs",
                filename
            )

            file.save(save_path)

            image_path = "/static/uploads/thuoc/" + filename

        db.medicines.update_one(
            {
                "_id": ObjectId(medicine_id)
            },
            {
                "$set": {
                    "name": request.form["name"],
                    "price": int(request.form["price"]),
                    "quantity": int(request.form["quantity"]),
                    "description": request.form["description"],
                    "image": image_path
                }
            }
        )

        return redirect("/my-medicines")

    return render_template(
        "edit_medicine.html",
        medicine=medicine
    )
 
# ==========================
# THUỐC CỦA TÔI
# ==========================

@app.route("/my-medicines")
def my_medicines():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "doctor":
        return redirect("/login")

    user = db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    doctor = db.doctors.find_one({
        "email": user["email"]
    })

    medicines = list(
        db.medicines.find({
            "doctor_id": str(doctor["_id"])
        })
    )

    return render_template(
        "my_medicines.html",
        medicines=medicines
    )
    
# ==========================
# XÓA THUỐC
# ==========================

@app.route("/delete-medicine/<id>")
def delete_medicine(id):

    if "user_id" not in session:
        return redirect("/login")

    db.medicines.delete_one({
        "_id": ObjectId(id)
    })

    return redirect("/my-medicines")

# ==========================
# DANH SÁCH THUỐC
# ==========================

@app.route("/medicines")
def medicines():

    medicines = list(
        db.medicines.find()
    )

    return render_template(
        "medicine_list.html",
        medicines=medicines
    )

# ==========================
# TƯ VẤN THUỐC
# ==========================

@app.route("/medicine-consult/<medicine_id>")
def medicine_consult(medicine_id):

    if "user_id" not in session:
        return redirect("/login")

    medicine = db.medicines.find_one({
        "_id": ObjectId(medicine_id)
    })

    if not medicine:
        return "<h3>Không tìm thấy thuốc</h3>"

    session["consult_medicine"] = {
        "medicine_id": str(medicine["_id"]),
        "medicine_name": medicine["name"],
        "doctor_name": medicine["doctor_name"],
        "doctor_id": medicine["doctor_id"]
    }

    return redirect("/chat-doctor")

# ==========================
# MUA THUỐC
# ==========================

@app.route("/buy-medicine/<medicine_id>")
def buy_medicine(medicine_id):

    if "user_id" not in session:
        return redirect("/login")

    medicine = db.medicines.find_one({
        "_id": ObjectId(medicine_id)
    })

    if not medicine:
        return "<h3>Không tìm thấy thuốc</h3>"

    flash(
        "Vui lòng thêm sản phẩm vào giỏ hàng trước khi thanh toán.",
        "info"
    )

    return redirect("/medicines")
    
# ==========================
# THÊM VÀO GIỎ HÀNG
# ==========================

@app.route("/add-cart/<medicine_id>")
def add_cart(medicine_id):

    if "user_id" not in session:
        return redirect("/login")

    medicine = db.medicines.find_one({
        "_id": ObjectId(medicine_id)
    })

    if not medicine:
        return redirect("/medicines")

    cart_item = db.cart.find_one({
        "user_id": str(session["user_id"]),
        "medicine_id": medicine_id
    })

    if cart_item:

        db.cart.update_one(
            {
                "_id": cart_item["_id"]
            },
            {
                "$inc": {
                    "quantity": 1
                }
            }
        )

    else:

        db.cart.insert_one({

            "user_id": str(session["user_id"]),

            "medicine_id": medicine_id,

            "medicine_name": medicine["name"],

            "price": medicine["price"],

            "image": medicine.get("image", ""),

            "quantity": 1
        })

    return redirect("/medicines")

# ==========================
# GIỎ HÀNG
# ==========================

@app.route("/cart")
def cart():

    if "user_id" not in session:
        return redirect("/login")

    carts = list(
        db.cart.find({
            "user_id": str(session["user_id"])
        })
    )

    total = 0

    for item in carts:
        total += item["price"] * item["quantity"]

    return render_template(
        "cart.html",
        carts=carts,
        total=total
    )

# ==========================
# TĂNG SỐ LƯỢNG
# ==========================

@app.route("/cart/increase/<cart_id>")
def increase_cart(cart_id):

    if "user_id" not in session:
        return redirect("/login")

    db.cart.update_one(
        {
            "_id": ObjectId(cart_id)
        },
        {
            "$inc": {
                "quantity": 1
            }
        }
    )

    return redirect("/cart")

# ==========================
# GIẢM SỐ LƯỢNG
# ==========================

@app.route("/cart/decrease/<cart_id>")
def decrease_cart(cart_id):

    if "user_id" not in session:
        return redirect("/login")

    item = db.cart.find_one({
        "_id": ObjectId(cart_id)
    })

    if item:

        if item["quantity"] > 1:

            db.cart.update_one(
                {
                    "_id": item["_id"]
                },
                {
                    "$inc": {
                        "quantity": -1
                    }
                }
            )

        else:

            db.cart.delete_one({
                "_id": item["_id"]
            })

    return redirect("/cart")

# ==========================
# XÓA SẢN PHẨM KHỎI GIỎ
# ==========================

@app.route("/cart/delete/<cart_id>")
def delete_cart(cart_id):

    if "user_id" not in session:
        return redirect("/login")

    db.cart.delete_one({
        "_id": ObjectId(cart_id)
    })

    return redirect("/cart")

# ==========================
# THANH TOÁN
# ==========================

@app.route("/checkout")
def checkout():

    if "user_id" not in session:
        return redirect("/login")

    carts = list(
        db.cart.find({
            "user_id": str(session["user_id"])
        })
    )

    if not carts:
        return redirect("/cart")

    total = 0

    for item in carts:
        total += item["price"] * item["quantity"]

    return render_template(
        "checkout.html",

        carts=carts,

        total=total,

        bank_name="MB Bank",

        bank_number="123456789",

        bank_owner="NGUYEN VAN A"
    )
    
# ==========================
# XÁC NHẬN THANH TOÁN
# ==========================

@app.route("/confirm-payment", methods=["POST"])
def confirm_payment():

    # ==========================
    # KIỂM TRA ĐĂNG NHẬP
    # ==========================
    if "user_id" not in session:
        return redirect("/login")

    # ==========================
    # LẤY GIỎ HÀNG
    # ==========================
    carts = list(
        db.cart.find({
            "user_id": str(session["user_id"])
        })
    )

    # Nếu giỏ hàng trống
    if not carts:
        return redirect("/cart")

    # ==========================
    # TÍNH TỔNG TIỀN
    # ==========================
    total = 0

    for item in carts:

        total += (
            item["price"] *
            item["quantity"]
        )

    # ==========================
    # LƯU ĐƠN HÀNG
    # ==========================
    db.orders.insert_one({

        # Người mua
        "user_id": str(session["user_id"]),

        # Tên người mua
        "fullname": session["fullname"],

        # Danh sách sản phẩm
        "items": carts,

        # Tổng tiền
        "total": total,

        # Trạng thái đơn
        # pending = chờ admin xác nhận
        # paid = đã xác nhận
        # cancel = hủy
        "status": "pending",

        # Thời gian tạo đơn
        "created_at": datetime.now()

    })

    # ==========================
    # XÓA GIỎ HÀNG
    # ==========================
    db.cart.delete_many({

        "user_id": str(session["user_id"])

    })

    # ==========================
    # THÔNG BÁO THÀNH CÔNG
    # ==========================

    flash(
        "🎉 Đặt hàng thành công! Đơn hàng đang chờ xác nhận thanh toán.",
        "success"
    )

    return redirect("/order-history")

# ==========================
# LỊCH SỬ ĐƠN HÀNG
# ==========================

@app.route("/order-history")
def order_history():

    if "user_id" not in session:
        return redirect("/login")

    orders = list(
        db.orders.find({
            "user_id": str(session["user_id"])
        }).sort(
            "created_at",
            -1
        )
    )

    return render_template(
        "order_history.html",
        orders=orders
    )

# ==========================
# QUẢN LÝ ĐƠN HÀNG (ADMIN)
# ==========================

@app.route("/admin-orders")
def admin_orders():

    # Kiểm tra đăng nhập
    if "user_id" not in session:
        return redirect("/login")

    # Chỉ admin được truy cập
    if session.get("role") != "admin":
        return redirect("/dashboard")

    # Lấy tất cả đơn hàng
    orders = list(
        db.orders.find().sort(
            "created_at",
            -1
        )
    )

    return render_template(
        "admin_orders.html",
        orders=orders
    )

# ==========================
# XÁC NHẬN ĐƠN HÀNG
# ==========================

@app.route("/approve-order/<order_id>")
def approve_order(order_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/dashboard")

    db.orders.update_one(
        {
            "_id": ObjectId(order_id)
        },
        {
            "$set": {
                "status": "paid"
            }
        }
    )

    return redirect("/admin-orders")

# ==========================
# HỦY ĐƠN HÀNG
# ==========================

@app.route("/cancel-order/<order_id>")
def cancel_order(order_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/dashboard")

    db.orders.update_one(
        {
            "_id": ObjectId(order_id)
        },
        {
            "$set": {
                "status": "cancel"
            }
        }
    )

    return redirect("/admin-orders")

# ==========================
# AUTO EMAIL REMINDER
# ==========================

scheduler = BackgroundScheduler()

scheduler.add_job(
    check_appointments,
    "interval",
    hours=24
)

scheduler.start()

# ==========================
# APSCHEDULER
# ==========================

scheduler = BackgroundScheduler()

scheduler.add_job(
    check_doctor_appointments,
    "cron",
    hour=8,
    minute=0
)

# ==========================
# CHẠY FLASK
# ==========================

if __name__ == "__main__":
    scheduler.start()
    socketio.run(app)

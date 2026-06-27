from flask import Flask, render_template, request, redirect, session
from database import db
from bson.objectid import ObjectId
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
from apscheduler.schedulers.background import BackgroundScheduler
from config import MONGO_URI, EMAIL_ADDRESS, EMAIL_PASSWORD
import smtplib
import os
import bcrypt

app = Flask(__name__)
from config import SECRET_KEY
app.secret_key = SECRET_KEY

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

@socketio.on("join_room")
def handle_join(data):

    room = data["room"]

    join_room(room)

@socketio.on("send_message")
def handle_message(data):

    print("=== SEND_MESSAGE ===")
    print(data)

    room = data["room"]
    doctor_id, user_id = room.split("_", 1)

    db.messages.insert_one({
        "doctor_id": doctor_id,
        "user_id": user_id,
        "sender_name": data["sender_name"],
        "sender_role": data.get("sender_role", "user"),
        "message": data["message"],
        "created_at": datetime.now()
    })

    print("Đã lưu MongoDB")

    emit("receive_message", data, room=room)

# ==========================
# GỬI EMAIL
# ==========================

def send_email(to_email, subject, content):

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
            587
        )

        server.starttls()

        server.login(
            EMAIL_ADDRESS,
            EMAIL_PASSWORD
        )

        server.send_message(msg)

        server.quit()

        print("Đã gửi email thành công")

    except Exception as e:

        print("Lỗi gửi email:", e)

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

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = db.users.find_one({
            "email": email
        })

        if existing_user:
            return """
            <script>
                alert('Email đã tồn tại!');
                window.location.href='/user-register';
            </script>
            """

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        result = db.users.insert_one({
            "fullname": fullname,
            "email": email,
            "password": hashed_password,
            "role": "user"
        })

        session["user_id"] = str(result.inserted_id)
        session["fullname"] = fullname
        session["role"] = "user"

        return """
        <script>
            alert('Đăng ký thành công!');
            window.location.href='/dashboard';
        </script>
        """

    return render_template("register.html")


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

# ==========================
# DASHBOARD CHUNG
# ==========================

@app.route("/dashboard")
def dashboard():

# Kiểm tra đăng nhập
    if "user_id" not in session:
        return redirect("/login")

# ==========================
# ADMIN DASHBOARD
# ==========================
    if session.get("role") == "admin":

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
                month = int(
                    appt["date"].split("-")[1]
                )

                months[month - 1] += 1

            except:
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
# DOCTOR DASHBOARD
# ==========================
    if session.get("role") == "doctor":

        return redirect("/doctor-dashboard")

# ==========================
# USER DASHBOARD
# ==========================

    today = datetime.now().date()

    reminders = []

    appointments = db.appointments.find({
        "user_id": session["user_id"]
    })

    for appt in appointments:

        try:

            appointment_date = datetime.strptime(
                appt["date"],
                "%Y-%m-%d"
            ).date()

            days_left = (
                appointment_date - today
            ).days

            # Nhắc lịch khám trong 3 ngày tới
            if 0 <= days_left <= 3:

                reminders.append({
                    "doctor": appt["doctor"],
                    "date": appt["date"],
                    "time": appt["time"],
                    "days_left": days_left
                })

        except:
            pass

# Đếm số thông báo
    notification_count = len(reminders)

    return render_template(
            "user_dashboard.html",
            fullname=session["fullname"],
            reminders=reminders,
            notification_count=notification_count
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
# NHẮC LỊCH BÁC SĨ
# ==========================

def check_doctor_appointments():

    tomorrow = (
        datetime.now() +
        timedelta(days=1)
    ).strftime("%Y-%m-%d")

    appointments = db.appointments.find({

        "date": tomorrow,

        "doctor_reminder_sent": False

    })

    for appt in appointments:

        doctor = db.doctors.find_one({

            "_id": ObjectId(
                appt["doctor_id"]
            )

        })

        if not doctor:
            continue

        content = f"""
Xin chào {doctor['name']}

Bạn có lịch khám vào ngày mai.

Bệnh nhân:
{appt['fullname']}

Ngày:
{appt['date']}

Giờ:
{appt['time']}
"""

        send_email(

            doctor["email"],

            "Nhắc lịch khám ngày mai",

            content

        )

        db.appointments.update_one(

            {
                "_id": appt["_id"]
            },

            {
                "$set": {
                    "doctor_reminder_sent": True
                }
            }

        )

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
# DANH SÁCH BÁC SĨ
# ==========================

@app.route("/doctors")
def doctors():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/dashboard")

    doctors = list(
        db.doctors.find()
    )

    return render_template(
        "doctor_list.html",
        doctors=doctors
    )

# ==========================
# DANH SÁCH BÁC SĨ CHO USER
# ==========================

@app.route("/doctor-list")
def doctor_list():

    if "user_id" not in session:
        return redirect("/login")

    doctors = list(
        db.doctors.find()
    )

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

        # Ảnh bác sĩ
        image = request.files["image"]

        filename = secure_filename(
            image.filename
        )

        os.makedirs(
            "static/uploads/doctors",
            exist_ok=True
        )

        image.save(
            os.path.join(
                "static/uploads/doctors",
                filename
            )
        )

        image_path = (
            "/static/uploads/doctors/" +
            filename
        )

        db.doctors.insert_one({

            "name": name,
            "specialty": specialty,
            "clinic": clinic,
            "phone": phone,
            "email": email,
            "experience": experience,
            "image": image_path

        })

        return redirect("/doctors")

    specialties = list(
        db.specialties.find()
    )

    clinics = list(
        db.clinics.find()
    )

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

    specialties = list(db.specialties.find())
    clinics = list(db.clinics.find())

    if request.method == "POST":

        image_path = doctor.get("image", "")

        file = request.files.get("image")

        if file and file.filename != "":

            filename = secure_filename(
                file.filename
            )

            os.makedirs(
                "static/uploads/doctors",
                exist_ok=True
            )

            save_path = os.path.join(
                "static/uploads/doctors",
                filename
            )

            file.save(save_path)

            image_path = (
                "/static/uploads/doctors/" +
                filename
            )

        db.doctors.update_one(
            {"_id": ObjectId(id)},
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

    # Kiểm tra đăng nhập
    if "user_id" not in session:
        return redirect("/login")

    # Khi người dùng bấm đặt lịch
    if request.method == "POST":

        # Lấy dữ liệu từ form
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

        # Không cho đặt lịch quá khứ
        if selected_date < today:

            return """
            <h3>Không thể đặt lịch trước ngày hiện tại!</h3>
            <a href='/appointments/add'>Quay lại</a>
            """

        # ==========================
        # LẤY THÔNG TIN BÁC SĨ
        # ==========================

        doctor_info = db.doctors.find_one({

            "name": doctor

        })

        # ==========================
        # LƯU LỊCH KHÁM
        # ==========================

        db.appointments.insert_one({

            # Tên bệnh nhân
            "patient": patient,

            # Tên bác sĩ
            "doctor": doctor,

            # Email bác sĩ
            "doctor_email": (
                doctor_info["email"]
                if doctor_info and "email" in doctor_info
                else ""
            ),

            # Ngày khám
            "date": date,

            # Giờ khám
            "time": time,

            # Người đặt lịch
            "user_id": str(session["user_id"]),

            # Đánh dấu đã gửi email nhắc chưa
            "doctor_reminder_sent": False,

            "user_reminder_sent": False,

            # Thời gian tạo lịch
            "created_at": datetime.now()

        })

        # Quay lại danh sách lịch khám
        return redirect("/appointments")

    # ==========================
    # HIỂN THỊ FORM ĐẶT LỊCH
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
  
# ==========================
# Tư vấn chuyên khoa thông minh
# ==========================

@app.route("/symptom-checker", methods=["GET", "POST"])
def symptom_checker():

    if "chat_history" not in session:
        session["chat_history"] = []

    specialty = None
    doctor_name = None
    recommendation = None
    chatbot_question = None
    urgency = None
    top_specialties = []

    if request.method == "POST":

        symptom = request.form["symptom"].lower()

        specialties = {

            "Tim mạch": {
                "đau ngực": 10,
                "tức ngực": 10,
                "nghẹn ngực": 9,
                "khó thở": 8,
                "hồi hộp": 7,
                "đánh trống ngực": 7,
                "cao huyết áp": 6,
                "tim đập nhanh": 6
            },

            "Hô hấp": {
                "ho": 8,
                "khó thở": 8,
                "đờm": 7,
                "viêm họng": 6,
                "sổ mũi": 5,
                "nghẹt mũi": 5,
                "hen": 8,
                "viêm phổi": 10,
                "cúm": 6
            },

            "Tiêu hóa": {
                "đau bụng": 10,
                "bụng": 4,
                "tiêu chảy": 8,
                "buồn nôn": 7,
                "nôn": 7,
                "đầy hơi": 6,
                "ợ chua": 6,
                "dạ dày": 8,
                "táo bón": 6
            },

            "Thần kinh": {
                "đau đầu": 10,
                "chóng mặt": 8,
                "hoa mắt": 7,
                "mất ngủ": 6,
                "tê tay": 7,
                "tê chân": 7,
                "co giật": 10
            },

            "Da liễu": {
                "mụn": 5,
                "ngứa": 8,
                "dị ứng": 8,
                "nổi mẩn": 8,
                "phát ban": 9
            },

            "Tai Mũi Họng": {
                "tai": 4,
                "mũi": 4,
                "họng": 4,
                "nghẹt mũi": 6,
                "ù tai": 7,
                "viêm xoang": 8
            },

            "Mắt": {
                "mắt": 4,
                "mờ mắt": 8,
                "đau mắt": 8,
                "nhức mắt": 7
            },

            "Răng Hàm Mặt": {
                "răng": 4,
                "đau răng": 10,
                "sâu răng": 8,
                "nướu": 6,
                "lợi": 6
            },

            "Cơ Xương Khớp": {
                "khớp": 5,
                "xương": 5,
                "đau lưng": 8,
                "đau vai": 8,
                "đau gối": 8,
                "thoái hóa": 10
            },

            "Tiết niệu": {
                "tiểu": 4,
                "thận": 7,
                "tiểu buốt": 9,
                "tiểu nhiều": 7,
                "sỏi thận": 10
            },

            "Nội tiết": {
                "tiểu đường": 10,
                "đường huyết": 8,
                "tuyến giáp": 8,
                "nội tiết": 6
            },

            "Nam khoa": {
                "sinh lý nam": 10,
                "xuất tinh": 8,
                "dương vật": 8
            },

            "Sản phụ khoa": {
                "kinh nguyệt": 8,
                "mang thai": 10,
                "phụ khoa": 8,
                "rong kinh": 9
            },

            "Nhi khoa": {
                "trẻ em": 10,
                "em bé": 10,
                "trẻ nhỏ": 10,
                "bé": 8
            },

            "Tâm lý - Tâm thần": {
                "stress": 8,
                "lo âu": 9,
                "trầm cảm": 10,
                "căng thẳng": 8,
                "tâm lý": 7
            },

            "Nội tổng quát": {
                "sốt": 6,
                "mệt": 5,
                "mệt mỏi": 7,
                "yếu": 5,
                "chán ăn": 6,
                "đau người": 6
            }
        }

        scores = {}

        for spec, keywords in specialties.items():

            score = 0

            for keyword, weight in keywords.items():

                if keyword in symptom:
                    score += weight

            scores[spec] = score

        top_specialties = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_specialties = [
            item for item in top_specialties
            if item[1] > 0
        ]

        if len(top_specialties) == 0:

            chatbot_question = (
                "Bạn có thể mô tả chi tiết hơn không? "
                "Ví dụ: đau ở đâu, sốt, ho, khó thở, đau bụng..."
            )

            session["chat_history"].append({
                "user": symptom,
                "specialty": "Chưa xác định",
                "doctor": "",
                "question": chatbot_question,
                "urgency": "Chưa xác định"
            })

        else:

            specialty = top_specialties[0][0]

            urgency = "Bình thường"

            if (
                "đau ngực" in symptom or
                "tức ngực" in symptom or
                "khó thở" in symptom or
                "co giật" in symptom
            ):
                urgency = "Khẩn cấp"

            elif (
                "sốt cao" in symptom or
                "nôn nhiều" in symptom
            ):
                urgency = "Cần khám sớm"

            if specialty == "Tim mạch":
                chatbot_question = "Bạn có bị khó thở hoặc hồi hộp tim không?"

            elif specialty == "Hô hấp":
                chatbot_question = "Bạn có sốt hoặc có đờm không?"

            elif specialty == "Tiêu hóa":
                chatbot_question = "Bạn có bị tiêu chảy hoặc buồn nôn không?"

            elif specialty == "Thần kinh":
                chatbot_question = "Bạn có bị chóng mặt hoặc mất ngủ không?"

            doctor = db.doctors.find_one(
                {"specialty": specialty},
                sort=[("experience", -1)]
            )

            if doctor:
                doctor_name = doctor["name"]
            else:
                doctor_name = "Chưa có bác sĩ phù hợp"

            recommendation = (
                f"Chuyên khoa phù hợp nhất: {specialty}"
            )

            session["chat_history"].append({
                "user": symptom,
                "specialty": specialty,
                "doctor": doctor_name,
                "question": chatbot_question,
                "urgency": urgency
            })

        session.modified = True

    return render_template(
        "symptom_checker.html",
        specialty=specialty,
        doctor=doctor_name,
        recommendation=recommendation,
        chatbot_question=chatbot_question,
        urgency=urgency,
        top_specialties=top_specialties,
        chat_history=session.get("chat_history", [])
    )

# ==========================
# Xóa lịch sử chat
# ==========================

@app.route("/clear-chat")
def clear_chat():

    session.pop(
        "chat_history",
        None
    )

    return redirect(
        "/symptom-checker"
    )
    
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

            filename = secure_filename(
                image.filename
            )

            image.save(
                os.path.join(
                    "static/uploads",
                    filename
                )
            )

            db.medicines.insert_one({

                "doctor_id": str(doctor["_id"]),
                "doctor_name": doctor["name"],

                "name": request.form["name"],

                "price": int(
                    request.form["price"]
                ),

                "quantity": int(
                    request.form["quantity"]
                ),

                "description":
                    request.form["description"],

                "image":
                    "/static/uploads/" + filename,

                "created_at":
                    datetime.now()
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

                upload_folder = "static/uploads"

                os.makedirs(upload_folder, exist_ok=True)

                save_path = os.path.join(
                    upload_folder,
                    filename
                )

                file.save(save_path)

                image_path = "/" + save_path.replace("\\", "/")

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

    return f"""
    <script>
        alert('Chức năng thanh toán sẽ được xây dựng ở bước tiếp theo.');
        window.location='/medicines';
    </script>
    """
    
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
    return """
    <script>
        alert('Đơn hàng đã được tạo và đang chờ xác nhận thanh toán!');
        window.location='/dashboard';
    </script>
    """

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

    # Chỉ chạy Scheduler khi chạy trực tiếp (Local)
    scheduler.start()

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )
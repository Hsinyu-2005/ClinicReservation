from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-in-real-project"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clinic.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# --------------------
# Models
# --------------------
class Member(db.Model):
    __tablename__ = "members"
    member_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    medical_record = db.Column(db.String(50))
    password_hash = db.Column(db.String(128), nullable=False)

    appointments = db.relationship("AppointmentRecord", backref="member", lazy=True)


class OutpatientSchedule(db.Model):
    __tablename__ = "outpatient_schedules"
    schedule_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)
    doctor_name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    max_quota = db.Column(db.Integer, nullable=False, default=10)
    current_quota = db.Column(db.Integer, nullable=False, default=0)  # 已預約人數

    appointments = db.relationship("AppointmentRecord", backref="schedule", lazy=True)

    @property
    def remaining_quota(self):
        return self.max_quota - self.current_quota


class AppointmentRecord(db.Model):
    __tablename__ = "appointment_records"
    appointment_id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default="Success")
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey("outpatient_schedules.schedule_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --------------------
# Helper functions (AppointmentManager-ish)
# --------------------
def verify_login(email, password):
    member = Member.query.filter_by(email=email).first()
    if member and bcrypt.check_password_hash(member.password_hash, password):
        return member
    return None


def get_available_schedules(target_date: date):
    return OutpatientSchedule.query.filter_by(date=target_date).all()


def validate_quota(schedule_id: int) -> bool:
    schedule = OutpatientSchedule.query.get(schedule_id)
    if not schedule:
        return False
    return schedule.remaining_quota > 0


def create_appointment(member_id: int, schedule_id: int):
    schedule = OutpatientSchedule.query.get(schedule_id)
    if not schedule:
        return None

    if schedule.remaining_quota <= 0:
        return None

    schedule.current_quota += 1
    appointment = AppointmentRecord(
        member_id=member_id,
        schedule_id=schedule_id,
        status="Success",
    )
    db.session.add(appointment)
    db.session.commit()
    return appointment


# --------------------
# Routes
# --------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        member = verify_login(email, password)
        if member:
            session["member_id"] = member.member_id
            session["member_name"] = member.name
            flash("登入成功", "success")
            return redirect(url_for("appointment"))
        else:
            flash("帳號或密碼錯誤", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已登出", "info")
    return redirect(url_for("index"))


@app.route("/appointment", methods=["GET", "POST"])
def appointment():
    if "member_id" not in session:
        flash("請先登入再進行預約", "warning")
        return redirect(url_for("login"))

    # 選擇日期（預設今天）
    date_str = request.args.get("date")
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    schedules = get_available_schedules(target_date)

    # 預約動作（按下預約按鈕）
    if request.method == "POST":
        schedule_id = int(request.form.get("schedule_id"))
        if validate_quota(schedule_id):
            appt = create_appointment(session["member_id"], schedule_id)
            if appt:
                flash("預約成功！", "success")
                return redirect(
                    url_for("my_appointments")
                )
            else:
                flash("預約建立失敗，請稍後再試", "danger")
        else:
            flash("此時段預約已滿", "danger")

        return redirect(
            url_for("appointment", date=target_date.strftime("%Y-%m-%d"))
        )

    return render_template(
        "appointment.html",
        target_date=target_date,
        schedules=schedules,
    )


@app.route("/my_appointments")
def my_appointments():
    if "member_id" not in session:
        flash("請先登入再查看預約紀錄", "warning")
        return redirect(url_for("login"))

    appts = (
        AppointmentRecord.query.filter_by(member_id=session["member_id"])
        .order_by(AppointmentRecord.created_at.desc())
        .all()
    )
    return render_template("my_appointments.html", appointments=appts)


# --------------------
# 初始化資料庫 & 測試資料
# --------------------
def init_db():
    db.create_all()

    # 如果沒有會員，建立一個測試帳號
    if not Member.query.first():
        password_hash = bcrypt.generate_password_hash("test1234").decode("utf-8")
        m = Member(
            name="測試會員",
            email="test@example.com",
            medical_record="MR001",
            password_hash=password_hash,
        )
        db.session.add(m)

    # 如果沒有排程，塞幾筆今天的門診
    if not OutpatientSchedule.query.first():
        today = date.today()
        demo_schedules = [
            OutpatientSchedule(
                date=today,
                time_slot="09:00-10:00",
                doctor_name="王大明",
                department="內科",
                max_quota=10,
                current_quota=2,
            ),
            OutpatientSchedule(
                date=today,
                time_slot="10:00-11:00",
                doctor_name="林小慧",
                department="小兒科",
                max_quota=8,
                current_quota=8,
            ),
            OutpatientSchedule(
                date=today,
                time_slot="14:00-15:00",
                doctor_name="陳文豪",
                department="骨科",
                max_quota=5,
                current_quota=1,
            ),
        ]
        db.session.add_all(demo_schedules)

    db.session.commit()


if __name__ == "__main__":
    if not os.path.exists("clinic.db"):
        with app.app_context():
            init_db()
    app.run(debug=True)

from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os


app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-in-real-project"


BASE_DIR = os.path.abspath(os.path.dirname(__file__))        # …/clinic_app
DB_PATH = os.path.join(BASE_DIR, "instance", "clinic.db")    # …/clinic_app/instance/clinic.db

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# Models
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
    current_quota = db.Column(db.Integer, nullable=False, default=0)

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



def get_session_label(time_slot: str) -> str:
    try:
        start = time_slot.split("-")[0]
        hour = int(start.split(":")[0])
    except Exception:
        return "其他"

    if hour < 12:
        return "上午診"
    elif hour < 17:
        return "中午診"
    else:
        return "夜間診"



@app.route("/")
def index():
    return redirect(url_for("schedule_table"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Demo用：不檢查密碼，只要按登入就幫你登入會員。
    """
    if request.method == "POST":
        member = Member.query.first()
        if not member:
            hash_pw = bcrypt.generate_password_hash("test1234").decode("utf-8")
            member = Member(
                name="測試會員",
                email="test@example.com",
                medical_record="MR001",
                password_hash=hash_pw,
            )
            db.session.add(member)
            db.session.commit()

        session["member_id"] = member.member_id
        session["member_name"] = member.name
        flash("登入成功", "success")
        return redirect(url_for("schedule_table"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已登出", "info")
    return redirect(url_for("login"))


@app.route("/my_appointments")
def my_appointments():
    if "member_id" not in session:
        flash("請先登入", "warning")
        return redirect(url_for("login"))

    appts = (
        AppointmentRecord.query.filter_by(member_id=session["member_id"])
        .order_by(AppointmentRecord.created_at.desc())
        .all()
    )
    return render_template("my_appointments.html", appointments=appts)


@app.route("/schedule_table")
def schedule_table():
    week_start_str = request.args.get("week_start")
    today = date.today()

    if week_start_str:
        week_start = datetime.strptime(week_start_str, "%Y-%m-%d").date()
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    day_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        days.append({
            "label": day_names[i],
            "date": d,
            "date_str": d.strftime("%Y-%m-%d"),
        })

    schedules = OutpatientSchedule.query.filter(
        OutpatientSchedule.date >= week_start,
        OutpatientSchedule.date <= week_end
    ).all()

    time_slots = ["上午診", "中午診", "夜間診"]

    schedule_map = {}
    for d in days:
        for slot in time_slots:
            schedule_map[f"{d['date_str']}_{slot}"] = None

    for s in schedules:
        label = get_session_label(s.time_slot)
        if label not in time_slots:
            continue

        key = f"{s.date.strftime('%Y-%m-%d')}_{label}"

        schedule_map[key] = {
            "schedule_id": s.schedule_id,
            "department": s.department,
            "doctor": s.doctor_name,
            "max_quota": s.max_quota,
            "remaining_quota": s.remaining_quota,
        }

    return render_template(
        "schedule_table.html",
        days=days,
        time_slots=time_slots,
        schedule_map=schedule_map,
        prev_week_start=(week_start - timedelta(days=7)).strftime("%Y-%m-%d"),
        next_week_start=(week_start + timedelta(days=7)).strftime("%Y-%m-%d"),
        week_label=f"{week_start.strftime('%Y/%m/%d')} - {week_end.strftime('%Y/%m/%d')}",
    )


@app.route("/quick_book", methods=["POST"])
def quick_book():
    if "member_id" not in session:
        flash("請先登入", "warning")
        return redirect(url_for("login"))

    schedule_id = request.form.get("schedule_id", type=int)
    schedule = OutpatientSchedule.query.get(schedule_id)

    if not schedule or schedule.remaining_quota <= 0:
        flash("預約失敗或已額滿", "danger")
        return redirect(url_for("schedule_table"))

    schedule.current_quota += 1
    appt = AppointmentRecord(
        member_id=session["member_id"],
        schedule_id=schedule_id
    )

    db.session.add(appt)
    db.session.commit()
    flash("預約成功！", "success")

    return redirect(url_for("my_appointments"))


# 初始化資料（假資料）
def init_db():
    with app.app_context():
        db.create_all()

        if not Member.query.first():
            hash_pw = bcrypt.generate_password_hash("test1234").decode("utf-8")
            user = Member(
                name="測試會員",
                email="test@example.com",
                medical_record="MR001",
                password_hash=hash_pw,
            )
            db.session.add(user)

        if OutpatientSchedule.query.count() == 0:
            monday = date.today() - timedelta(days=date.today().weekday())
            doctors = [
                ("內科", "王醫師"),
                ("小兒科", "李醫師"),
                ("家醫科", "陳醫師"),
                ("骨科", "林醫師"),
                ("耳鼻喉科", "張醫師"),
                ("皮膚科", "黃醫師"),
                ("眼科", "周醫師"),
            ]
            time_slots = ["09:00-10:00", "13:00-14:00", "19:00-20:00"]

            demo = []
            for i in range(7):
                d = monday + timedelta(days=i)
                dept, doc = doctors[i % len(doctors)]
                for idx, ts in enumerate(time_slots):
                    demo.append(
                        OutpatientSchedule(
                            date=d,
                            time_slot=ts,
                            doctor_name=doc,
                            department=dept,
                            max_quota=10,
                            current_quota=(i + idx * 2) % 10
                        )
                    )
            db.session.add_all(demo)

        db.session.commit()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

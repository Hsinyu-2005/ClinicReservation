from flask import render_template, redirect, url_for, request, session, flash
from .database.init_db import get_schedules, book_schedule, get_my_appointments

def init_routes(app):

    # 首頁
    @app.route("/")
    def index():
        return render_template("index.html")

    # 週表
    @app.route("/schedule")
    def schedule_table():
        from .ui.appointment_ui import build_schedule_ui
        return build_schedule_ui()

    # 預約
    @app.route("/quick_book", methods=["POST"])
    def quick_book():
        schedule_id = request.form.get("schedule_id")
        member_id = session.get("member_id")

        if not member_id:
            flash("請先登入")
            return redirect(url_for("login"))

        success = book_schedule(schedule_id, member_id)

        if success:
            flash("預約成功！")
        else:
            flash("預約失敗或已額滿")

        return redirect(url_for("schedule_table"))

    # 我的預約
    @app.route("/my")
    def my_appointments():
        member_id = session.get("member_id")
        data = get_my_appointments(member_id)
        return render_template("my_appointments.html", appointments=data)

    # 登入
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            session["member_id"] = 1
            flash("登入成功！")
            return redirect(url_for("schedule_table"))
        return render_template("login.html")

    # 登出
    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))


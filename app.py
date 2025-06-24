import os
from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import date




base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, "templates")

app = Flask(__name__, template_folder=template_dir)

app.secret_key = "RAJ_SECRET_KEY_123"


@app.route("/")
def home():
    return render_template("home.html")

from flask import request, redirect
import sqlite3

@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        student_class = request.form["student_class"]
        address = request.form["address"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("INSERT INTO students (name, phone, student_class, address) VALUES (?, ?, ?, ?)",
                    (name, phone, student_class, address))
        conn.commit()
        conn.close()

        return redirect("/students")

    return render_template("add_student.html")

@app.route("/students")
def students():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()
    return render_template("view_student.html", students=students)

# Load students for selected class & date
@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if request.method == "POST":
        date = request.form["date"]
        student_class = request.form["student_class"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE student_class = ?", (student_class,))
        students = cur.fetchall()
        conn.close()

        return render_template("attendance.html", students=students, date=date, student_class=student_class)

    return render_template("attendance.html", students=None)

# Save marked present students
@app.route("/save_attendance", methods=["POST"])
def save_attendance():
    date = request.form["date"]
    student_class = request.form["student_class"]
    present_ids = request.form.getlist("present_ids")

    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    # पहले से delete कर दो ताकि बार-बार save न हो
    cur.execute("DELETE FROM attendance WHERE date=? AND student_class=?", (date, student_class))

    for sid in present_ids:
        cur.execute("INSERT INTO attendance (student_id, date, student_class) VALUES (?, ?, ?)",
                    (sid, date, student_class))

    conn.commit()
    conn.close()

    return redirect("/students")

@app.route("/add_fee", methods=["GET", "POST"])
def add_fee():
    if request.method == "POST":
        student_id = request.form["student_id"]
        total = int(request.form.get("total_fee", 0))
        paid = int(request.form.get("paid_fee", 0))
        last_paid = request.form["last_paid"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()

        # Check if student fee exists
        cur.execute("SELECT id FROM fees WHERE student_id=?", (student_id,))
        row = cur.fetchone()

        if row:
            cur.execute("""UPDATE fees SET total_fee=?, paid_fee=?, last_paid=?
                           WHERE student_id=?""",
                        (total, paid, last_paid, student_id))
        else:
            cur.execute("""INSERT INTO fees (student_id, total_fee, paid_fee, last_paid)
                           VALUES (?, ?, ?, ?)""",
                        (student_id, total, paid, last_paid))

        conn.commit()
        conn.close()
        return redirect("/fees")

    return render_template("add_fee.html")

from urllib.parse import quote

@app.route("/fees")
def fees():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("""
    SELECT s.id, s.name, f.total_fee, f.paid_fee, f.last_paid, s.phone
    FROM students s LEFT JOIN fees f ON s.id = f.student_id
    """)
    fees = cur.fetchall()
    conn.close()

    def msg(name, due):
        text = f"Hello {name}, your pending tuition fee is ₹{due}. Please pay soon. - Tuition"
        return quote(text)

    return render_template("fees.html", fees=fees, msg=msg)


from datetime import date

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/notes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/upload_notes", methods=["GET", "POST"])
def upload_notes():
    if request.method == "POST":
        class_ = request.form["class"]
        subject = request.form["subject"]
        topic = request.form["topic"]
        file = request.files["pdf"]
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("INSERT INTO notes (class, subject, topic, file_path) VALUES (?, ?, ?, ?)",
                    (class_, subject, topic, path))
        conn.commit()
        conn.close()
        return "✅ Notes uploaded successfully!"
    return render_template("upload_notes.html")


@app.route("/notes")
def notes():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT * FROM notes ORDER BY upload_date DESC")
    notes = cur.fetchall()
    conn.close()
    return render_template("notes.html", notes=notes)

@app.route("/fees_entry", methods=["GET", "POST"])
def fees_entry():
    if request.method == "POST":
        student_id = request.form["student_id"]
        amount_paid = int(request.form["amount_paid"])
        date_ = request.form["date"]
        note = request.form["note"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("""INSERT INTO fees_history (student_id, amount_paid, date, note)
                       VALUES (?, ?, ?, ?)""", (student_id, amount_paid, date_, note))
        conn.commit()
        conn.close()

        return redirect("/fees_history")

    return render_template("fees_entry.html")

@app.route("/ledger", methods=["GET"])
def ledger():
    student = None
    history = []
    total_fee = 0
    total_paid = 0

    student_id = request.args.get("student_id")
    if student_id:
        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()

        # get student info
        cur.execute("SELECT * FROM students WHERE id=?", (student_id,))
        student = cur.fetchone()

        # get total fee from fees table
        cur.execute("SELECT total_fee FROM fees WHERE student_id=?", (student_id,))
        fee_row = cur.fetchone()
        total_fee = fee_row[0] if fee_row else 0

        # get payment history
        cur.execute("SELECT * FROM fees_history WHERE student_id=? ORDER BY date", (student_id,))
        history = cur.fetchall()

        # calculate total paid
        total_paid = sum([row[2] for row in history])

        conn.close()

    return render_template("ledger.html", student=student, history=history,
                           total_fee=total_fee, total_paid=total_paid)

@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    error = None
    if request.method == "POST":
        student_id = request.form["student_id"]
        password = request.form["password"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT id, password, status FROM students WHERE id=? AND password=?", (student_id, password))
        student = cur.fetchone()
        conn.close()

        if student:
            if student[2] == "blocked":
                error = "❌ Access Denied: You are Blocked"
            elif student[2] == "left":
                error = "👋 You have been marked as LEFT"
            else:
                session["student_id"] = student[0]
                session["role"] = "student"
                return redirect(f"/student_dashboard/{student[0]}")
        else:
            error = "❌ Invalid ID or Password"
    
    return render_template("student_login.html", error=error)


@app.route("/student_dashboard/<int:student_id>")
def student_dashboard(student_id):
    return render_template("student_dashboard.html", student_id=student_id)

@app.route("/student_attendance/<int:student_id>")
def student_attendance(student_id):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("""
        SELECT date, status, homework 
        FROM attendance 
        WHERE student_id=? 
        ORDER BY date DESC
    """, (student_id,))
    rows = cur.fetchall()
    conn.close()
    return render_template("student_attendance.html", data=rows, student_id=student_id)

@app.route("/notes/<int:student_id>")
def view_notes_filtered(student_id):   # ← function name change kiya
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    # get student class
    cur.execute("SELECT student_class FROM students WHERE id=?", (student_id,))
    row = cur.fetchone()
    if not row:
        return "Student not found"
    student_class = row[0]

    # fetch only active subjects' notes
    cur.execute("""
        SELECT * FROM notes
        WHERE class=? AND subject IN (
            SELECT subject FROM subject_enrollment
            WHERE student_id=? AND status='active'
        )
    """, (student_class, student_id))

    notes = cur.fetchall()
    conn.close()

    return render_template("notes.html", notes=notes)

@app.route("/test_marks/<int:student_id>")
def test_marks(student_id):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("""SELECT * FROM test_marks WHERE student_id=? ORDER BY date DESC""", (student_id,))
    marks = cur.fetchall()
    conn.close()
    return render_template("test_marks.html", marks=marks, student_id=student_id)

from datetime import datetime

@app.route("/ask_doubt/<int:student_id>", methods=["GET", "POST"])
def ask_doubt(student_id):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    if request.method == "POST":
        message = request.form["message"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur.execute("INSERT INTO doubts (student_id, message, date) VALUES (?, ?, ?)", 
                    (student_id, message, date))
        conn.commit()

    # Doubt list
    cur.execute("SELECT * FROM doubts WHERE student_id=? ORDER BY date DESC", (student_id,))
    doubts = cur.fetchall()
    conn.close()
    return render_template("ask_doubt.html", doubts=doubts, student_id=student_id)

import urllib.parse

@app.route("/send_whatsapp/<int:student_id>")
def send_whatsapp(student_id):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    # Get student info
    cur.execute("SELECT name, mobile FROM students WHERE id=?", (student_id,))
    stu = cur.fetchone()

    # Get total_fee
    cur.execute("SELECT total_fee FROM fees WHERE student_id=?", (student_id,))
    fee = cur.fetchone()
    total_fee = fee[0] if fee else 0

    # Get total paid
    cur.execute("SELECT amount_paid FROM fees_history WHERE student_id=?", (student_id,))
    all_paid = cur.fetchall()
    paid = sum([x[0] for x in all_paid])

    due = total_fee - paid

    msg = f"नमस्ते {stu[0]}, आपकी फीस ₹{due} बाकी है | कृपया जल्द भुगतान करें | - RAJ Tuition"
    url = "https://wa.me/" + stu[1] + "?text=" + urllib.parse.quote(msg)

    return redirect(url)

@app.route("/view_doubts")
def view_doubts():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT * FROM doubts ORDER BY date DESC")
    doubts = cur.fetchall()
    conn.close()
    return render_template("view_doubts.html", doubts=doubts)

@app.route("/reply_doubt/<int:doubt_id>", methods=["POST"])
def reply_doubt(doubt_id):
    reply = request.form["reply"]
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("UPDATE doubts SET reply=? WHERE id=?", (reply, doubt_id))
    conn.commit()
    conn.close()
    return redirect("/view_doubts")

@app.route("/mark_attendance", methods=["GET", "POST"])
def mark_attendance():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    if request.method == "POST":
        date = request.form["date"]
        homework = request.form["homework"]

        # सभी students की attendance entries
        cur.execute("SELECT id FROM students")
        all_students = cur.fetchall()

        for stu in all_students:
            sid = stu[0]
            status = request.form.get(f"status_{sid}")
            cur.execute("INSERT INTO attendance (student_id, date, status, homework) VALUES (?, ?, ?, ?)",
                        (sid, date, status, homework))

        conn.commit()
        conn.close()
        return "✅ Attendance saved successfully!"

    # GET → students दिखाओ
    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()
    conn.close()
    return render_template("mark_attendance.html", students=students)

@app.route("/bulk_whatsapp")
def bulk_whatsapp():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    # All students with fees
    cur.execute("SELECT id, name, mobile FROM students")
    students = cur.fetchall()

    due_list = []
    for stu in students:
        sid, name, mobile = stu
        cur.execute("SELECT total_fee FROM fees WHERE student_id=?", (sid,))
        f = cur.fetchone()
        total = f[0] if f else 0

        cur.execute("SELECT amount_paid FROM fees_history WHERE student_id=?", (sid,))
        paid_rows = cur.fetchall()
        paid = sum([x[0] for x in paid_rows])
        due = total - paid

        if due > 0:
            due_list.append([sid, name, mobile, total, paid, due])

    conn.close()
    return render_template("bulk_whatsapp.html", due_list=due_list)

@app.route("/upload_homework", methods=["GET", "POST"])
def upload_homework():
    if request.method == "POST":
        cls = request.form["class"]
        subject = request.form["subject"]
        date = request.form["date"]
        content = request.form["content"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("INSERT INTO homework (class, subject, date, content) VALUES (?, ?, ?, ?)",
                    (cls, subject, date, content))
        conn.commit()
        conn.close()
        return "✅ Homework uploaded!"

    return render_template("upload_homework.html")

@app.route("/student_homework/<int:student_id>")
def student_homework(student_id):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    cur.execute("SELECT class FROM students WHERE id=?", (student_id,))
    stu = cur.fetchone()
    cls = stu[0]

    cur.execute("SELECT * FROM homework WHERE class=? ORDER BY date DESC", (cls,))
    rows = cur.fetchall()
    conn.close()
    return render_template("student_homework.html", rows=rows, student_class=cls, student_id=student_id)

@app.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")

@app.route("/global_search", methods=["GET", "POST"])
def global_search():
    results = []
    keyword = ""

    if request.method == "POST":
        keyword = request.form["keyword"].lower()

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()

        # Load all students
        cur.execute("SELECT id, name, mobile, village, class FROM students")
        all_students = cur.fetchall()
        conn.close()

        for s in all_students:
            if (keyword in s[1].lower()) or (keyword in s[2]) or (keyword in (s[3] or "").lower()):
                results.append(s)

    return render_template("global_search.html", results=results, keyword=keyword)

from flask import session

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username=? AND password=?", (user, pwd))
        row = cur.fetchone()
        conn.close()

        if row:
            session["username"] = user
            session["role"] = row[0]

            if row[0] == "admin":
                return redirect("/admin_dashboard")
            else:
                return redirect("/teacher_dashboard")
        else:
            error = "❌ Invalid username or password"

    return render_template("login.html", error=error)

from flask import send_file
import os

@app.route("/backup")
def backup():
    if "role" not in session or session["role"] != "admin":
        return "⛔ Access Denied"

    db_path = "db.sqlite3"  # DB का नाम

    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True)
    else:
        return "❌ Database file not found!"

@app.route("/progress_report/<int:student_id>")
def progress_report(student_id):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    # 1. Student Info
    cur.execute("SELECT name, class, mobile FROM students WHERE id=?", (student_id,))
    stu = cur.fetchone()

    # 2. Test Marks
    cur.execute("SELECT subject, marks, date FROM test_marks WHERE student_id=?", (student_id,))
    test_data = cur.fetchall()

    # 3. Attendance
    cur.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?", (student_id,))
    total_days = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='present'", (student_id,))
    present_days = cur.fetchone()[0]

    # 4. Fees
    cur.execute("SELECT total_fee FROM fees WHERE student_id=?", (student_id,))
    fee_row = cur.fetchone()
    total_fee = fee_row[0] if fee_row else 0

    cur.execute("SELECT SUM(amount_paid) FROM fees_history WHERE student_id=?", (student_id,))
    paid = cur.fetchone()[0] or 0

    conn.close()

    return render_template("progress_report.html",
                           stu=stu,
                           test_data=test_data,
                           total_days=total_days,
                           present_days=present_days,
                           total_fee=total_fee,
                           paid=paid,
                           student_id=student_id)




@app.route("/update_status", methods=["POST"])
def update_status():
    if "role" not in session or session["role"] != "admin":
        return "⛔ Access Denied"

    role = request.form["role"]
    id_ = int(request.form["id"])
    status = request.form["status"]

    table = "students" if role == "student" else "teachers"
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute(f"UPDATE {table} SET status=? WHERE id=?", (status, id_))
    conn.commit()
    conn.close()
    return "✅ Status Updated"

@app.route("/teacher_login", methods=["GET", "POST"])
def teacher_login():
    error = None
    if request.method == "POST":
        mobile = request.form["mobile"]
        password = request.form["password"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT id, password, status FROM teachers WHERE mobile=? AND password=?", (mobile, password))
        teacher = cur.fetchone()
        conn.close()

        if teacher:
            if teacher[2] == "blocked":
                error = "❌ Access Denied: You are Blocked"
            elif teacher[2] == "left":
                error = "👋 You have been marked as LEFT"
            else:
                session["teacher_id"] = teacher[0]
                session["role"] = "teacher"
                return redirect("/teacher_dashboard")
        else:
            error = "❌ Invalid Login Details"

    return render_template("teacher_login.html", error=error)

@app.route("/teacher_dashboard")
def teacher_dashboard():
    if "role" not in session or session["role"] != "teacher":
        return "⛔ Access Denied"
    return render_template("teacher_dashboard.html")

@app.route("/student_change_password", methods=["GET", "POST"])
def student_change_password():
    if "student_id" not in session:
        return "⛔ Access Denied"
    
    error = None
    success = None
    if request.method == "POST":
        old = request.form["old_password"]
        new = request.form["new_password"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT password FROM students WHERE id=?", (session["student_id"],))
        current = cur.fetchone()[0]

        if old != current:
            error = "❌ Old password doesn't match"
        else:
            cur.execute("UPDATE students SET password=? WHERE id=?", (new, session["student_id"]))
            conn.commit()
            success = "✅ Password changed"
        conn.close()
    
    return render_template("student_change_password.html", error=error, success=success)

@app.route("/reset_password_admin", methods=["GET", "POST"])
def reset_password_admin():
    if "role" not in session or session["role"] != "admin":
        return "⛔ Access Denied"
    
    message = ""
    if request.method == "POST":
        role = request.form["role"]
        user_id = request.form["id"]
        new_pass = request.form["new_password"]

        table = "students" if role == "student" else "teachers"
        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute(f"UPDATE {table} SET password=? WHERE id=?", (new_pass, user_id))
        conn.commit()
        conn.close()
        message = f"✅ Password updated for {role} ID {user_id}"
    
    return render_template("reset_password_admin.html", message=message)

@app.route("/update_student_info", methods=["GET", "POST"])
def update_student_info():
    if "student_id" not in session:
        return "⛔ Access Denied"
    
    student_id = session["student_id"]
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    if request.method == "POST":
        fields = ["name", "phone", "student_class", "address"]
        cur.execute("SELECT name, phone, student_class, address FROM students WHERE id=?", (student_id,))
        old_data = cur.fetchone()

        for i, field in enumerate(fields):
            new_val = request.form[field]
            if new_val != old_data[i]:
                cur.execute("""INSERT INTO update_requests
                               (student_id, field, old_value, new_value, status, date)
                               VALUES (?, ?, ?, ?, 'pending', DATE('now'))""",
                            (student_id, field, old_data[i], new_val))
        
        conn.commit()
        conn.close()
        return render_template("update_student_info.html", success="✅ Update request sent for admin approval")

    cur.execute("SELECT name, phone, student_class, address FROM students WHERE id=?", (student_id,))
    student = cur.fetchone()
    conn.close()

    return render_template("update_student_info.html", student=student)

@app.route("/approve_updates", methods=["GET", "POST"])
def approve_updates():
    if "role" not in session or session["role"] != "admin":
        return "⛔ Access Denied"

    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    if request.method == "POST":
        req_id = request.form["request_id"]
        action = request.form["action"]

        cur.execute("SELECT student_id, field, new_value FROM update_requests WHERE id=?", (req_id,))
        row = cur.fetchone()
        if row and action == "approve":
            student_id, field, new_value = row
            cur.execute(f"UPDATE students SET {field}=? WHERE id=?", (new_value, student_id))
            cur.execute("UPDATE update_requests SET status='approved' WHERE id=?", (req_id,))
        elif row and action == "reject":
            cur.execute("UPDATE update_requests SET status='rejected' WHERE id=?", (req_id,))
        conn.commit()

    cur.execute("SELECT * FROM update_requests WHERE status='pending'")
    requests = cur.fetchall()
    conn.close()

    return render_template("approve_updates.html", requests=requests)

from datetime import date, timedelta

def auto_generate_monthly_fee():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    # Check if fee already generated this month
    month_str = date.today().strftime("%Y-%m")
    cur.execute("SELECT COUNT(*) FROM fees WHERE note=?", (f"AUTO {month_str}",))
    if cur.fetchone()[0] > 0:
        conn.close()
        return "Already Generated"

    # Get all students with active status
    cur.execute("SELECT id, fee_per_month, left_date FROM students WHERE status='active'")
    students = cur.fetchall()

    for stu in students:
        sid, fee, left = stu
        if left and left < month_str + "-01":
            continue  # skip left students

        # Count total working days in month
        start = date.today().replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        total_days = (end - start).days + 1
        working_days = sum(1 for i in range(total_days)
                           if (start + timedelta(days=i)).weekday() != 6)  # Exclude Sunday

        # Subtract holidays
        cur.execute("SELECT date FROM holidays WHERE date BETWEEN ? AND ?", (start, end))
        holiday_dates = [row[0] for row in cur.fetchall()]
        working_days -= len(holiday_dates)

        per_day_fee = fee / 30
        final_fee = round(per_day_fee * working_days)

        # Insert into fees table
        cur.execute("""INSERT INTO fees (student_id, amount, date, note)
                       VALUES (?, ?, DATE('now'), ?)""", (sid, final_fee, f"AUTO {month_str}"))

    conn.commit()
    conn.close()
    return "✅ Fee Generated"


@app.before_request
def auto_fee_trigger():
    today = date.today()
    if today.day == 1:
        auto_generate_monthly_fee()


@app.route("/mark_left", methods=["GET", "POST"])
def mark_left():
    if "role" not in session or session["role"] != "admin":
        return "⛔ Access Denied"

    message = ""
    if request.method == "POST":
        student_id = request.form["student_id"]
        left_date = request.form["left_date"]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("UPDATE students SET status='left', left_date=? WHERE id=?", (left_date, student_id))
        conn.commit()
        conn.close()
        message = f"✅ Student {student_id} marked as LEFT on {left_date}"

    return render_template("mark_left.html", message=message)









if __name__ == "__main__":
    app.run(debug=True)

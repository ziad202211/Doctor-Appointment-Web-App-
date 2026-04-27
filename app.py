from flask import Flask, render_template, request, redirect, session, url_for
import pymysql
import config
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

def get_db():
    return pymysql.connect(
        host=config.DB_HOST, user=config.DB_USER,
        password=config.DB_PASSWORD, db=config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

# --- AUTH ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('admin_dashboard') if user['role'] == 'admin' else url_for('user_dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- USER ---
@app.route('/user/dashboard')
def user_dashboard():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT a.*, d.name as doctor_name, d.specialty FROM appointments a JOIN doctors d ON a.doctor_id = d.id WHERE a.user_id = %s", (session['user_id'],))
    appointments = cur.fetchall()
    return render_template('user/dashboard.html', appointments=appointments)

@app.route('/user/book', methods=['GET', 'POST'])
def book():
    db = get_db(); cur = db.cursor()
    if request.method == 'POST':
        cur.execute("INSERT INTO appointments (user_id, doctor_id, date, time) VALUES (%s, %s, %s, %s)",
            (session['user_id'], request.form['doctor_id'], request.form['date'], request.form['time']))
        db.commit()
        return redirect(url_for('user_dashboard'))
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()
    return render_template('user/book.html', doctors=doctors)

# --- ADMIN ---
@app.route('/admin/dashboard')
def admin_dashboard():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT COUNT(*) as total FROM appointments")
    total = cur.fetchone()
    cur.execute("SELECT COUNT(*) as users FROM users")
    users = cur.fetchone()
    cur.execute("SELECT COUNT(*) as total FROM doctors")
    doctors_count = cur.fetchone()
    cur.execute("SELECT COUNT(*) as pending FROM appointments WHERE status='pending'")
    pending = cur.fetchone()
    cur.execute("""
        SELECT a.*, u.name as user_name, d.name as doctor_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.id DESC LIMIT 5
    """)
    recent = cur.fetchall()
    return render_template('admin/dashboard.html',
        total=total, users=users,
        doctors_count=doctors_count['total'],
        pending=pending, recent=recent)
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT COUNT(*) as total FROM appointments"); total = cur.fetchone()
    cur.execute("SELECT COUNT(*) as users FROM users"); users = cur.fetchone()
    return render_template('admin/dashboard.html', total=total, users=users)

@app.route('/admin/doctors', methods=['GET', 'POST'])
def admin_doctors():
    db = get_db(); cur = db.cursor()
    if request.method == 'POST':
        cur.execute("INSERT INTO doctors (name, specialty, available_days) VALUES (%s, %s, %s)",
            (request.form['name'], request.form['specialty'], request.form['days']))
        db.commit()
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()
    return render_template('admin/doctors.html', doctors=doctors)

@app.route('/admin/doctors/delete/<int:id>')
def delete_doctor(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM doctors WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('admin_doctors'))

@app.route('/admin/appointments')
def admin_appointments():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT a.*, u.name as user_name, d.name as doctor_name FROM appointments a JOIN users u ON a.user_id = u.id JOIN doctors d ON a.doctor_id = d.id")
    appointments = cur.fetchall()
    return render_template('admin/appointments.html', appointments=appointments)

@app.route('/admin/appointments/update/<int:id>/<status>')
def update_appointment(id, status):
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE appointments SET status = %s WHERE id = %s", (status, id))
    db.commit()
    return redirect(url_for('admin_appointments'))

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
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
        doctor_id = request.form['doctor_id']
        appointment_date = request.form['date']
        appointment_time = request.form['time']
        selected_day = request.form.get('day_of_week')
        
        # Validate that the selected date matches the selected day
        from datetime import datetime
        if selected_day:
            actual_day = datetime.strptime(appointment_date, '%Y-%m-%d').strftime('%A')
            if actual_day != selected_day:
                cur.execute("SELECT * FROM doctors")
                doctors = cur.fetchall()
                return render_template('user/book.html', doctors=doctors, 
                                     error=f"The selected date is a {actual_day}, but you selected {selected_day}. Please choose a matching date.")
        
        # Check if doctor is available at this time
        day_of_week = datetime.strptime(appointment_date, '%Y-%m-%d').strftime('%A')
        
        cur.execute("""
            SELECT * FROM doctor_availability 
            WHERE doctor_id = %s AND day_of_week = %s 
            AND start_time <= %s AND end_time >= %s
        """, (doctor_id, day_of_week, appointment_time, appointment_time))
        availability = cur.fetchone()
        
        if not availability:
            cur.execute("SELECT * FROM doctors")
            doctors = cur.fetchall()
            return render_template('user/book.html', doctors=doctors, 
                                 error="Doctor is not available at this time")
        
        # Check for existing appointment
        cur.execute("""
            SELECT * FROM appointments 
            WHERE doctor_id = %s AND appointment_date = %s AND appointment_time = %s
        """, (doctor_id, appointment_date, appointment_time))
        existing = cur.fetchone()
        
        if existing:
            cur.execute("SELECT * FROM doctors")
            doctors = cur.fetchall()
            return render_template('user/book.html', doctors=doctors, 
                                 error="This time slot is already booked")
        
        cur.execute("INSERT INTO appointments (user_id, doctor_id, appointment_date, appointment_time) VALUES (%s, %s, %s, %s)",
            (session['user_id'], doctor_id, appointment_date, appointment_time))
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

@app.route('/admin/doctors', methods=['GET', 'POST'])
def admin_doctors():
    db = get_db(); cur = db.cursor()
    if request.method == 'POST':
        cur.execute("INSERT INTO doctors (name, specialty) VALUES (%s, %s)",
            (request.form['name'], request.form['specialty']))
        db.commit()
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()
    return render_template('admin/doctors.html', doctors=doctors)

@app.route('/admin/doctors/delete/<int:id>')
def delete_doctor(id):
    db = get_db(); cur = db.cursor()
    try:
        # Delete related availability records first
        cur.execute("DELETE FROM doctor_availability WHERE doctor_id = %s", (id,))
        # Delete related appointments
        cur.execute("DELETE FROM appointments WHERE doctor_id = %s", (id,))
        # Now delete the doctor
        cur.execute("DELETE FROM doctors WHERE id = %s", (id,))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error deleting doctor: {e}")
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

@app.route('/admin/availability', methods=['GET', 'POST'])
def admin_availability():
    db = get_db(); cur = db.cursor()
    if request.method == 'POST':
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        # Validate time range
        if start_time >= end_time:
            cur.execute("SELECT * FROM doctors")
            doctors = cur.fetchall()
            cur.execute("""
                SELECT da.*, d.name as doctor_name 
                FROM doctor_availability da 
                JOIN doctors d ON da.doctor_id = d.id 
                ORDER BY d.name, da.day_of_week
            """)
            availability = cur.fetchall()
            return render_template('admin/availability.html', 
                                 availability=availability, doctors=doctors,
                                 error="Start time must be earlier than end time")
        
        cur.execute("INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s)",
            (request.form['doctor_id'], request.form['day_of_week'], start_time, end_time))
        db.commit()
    cur.execute("""
        SELECT da.*, d.name as doctor_name 
        FROM doctor_availability da 
        JOIN doctors d ON da.doctor_id = d.id 
        ORDER BY d.name, da.day_of_week
    """)
    availability = cur.fetchall()
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()
    return render_template('admin/availability.html', availability=availability, doctors=doctors)

@app.route('/admin/availability/delete/<int:id>')
def delete_availability(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM doctor_availability WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('admin_availability'))

@app.route('/api/doctor/<int:doctor_id>/availability')
def get_doctor_availability(doctor_id):
    try:
        db = get_db(); cur = db.cursor()
        cur.execute("""
            SELECT day_of_week, start_time, end_time 
            FROM doctor_availability 
            WHERE doctor_id = %s 
            ORDER BY FIELD(day_of_week, 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
        """, (doctor_id,))
        availability = cur.fetchall()
        
        # Convert timedelta objects to strings for JSON serialization
        availability_list = []
        for avail in availability:
            start_time = str(avail['start_time'])[:5]
            end_time = str(avail['end_time'])[:5]
            
            # Validate time range
            if start_time >= end_time:
                print(f"Invalid time range for {avail['day_of_week']}: {start_time} - {end_time}")
                continue  # Skip invalid entries
            
            availability_list.append({
                'day_of_week': avail['day_of_week'],
                'start_time': start_time,
                'end_time': end_time
            })
        
        return jsonify({'availability': availability_list})
    except Exception as e:
        print(f"Error fetching availability: {e}")
        return jsonify({'error': str(e), 'availability': []})

if __name__ == '__main__':
    app.run(debug=True)
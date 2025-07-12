from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import secrets
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-password'
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'

mail = Mail(app)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('DROP TABLE IF EXISTS events')
    conn.execute('CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, date TEXT NOT NULL, description TEXT NOT NULL)')
    conn.execute('DROP TABLE IF EXISTS bookings')
    conn.execute('CREATE TABLE bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, private_key TEXT NOT NULL, consumed INTEGER DEFAULT 0, FOREIGN KEY (event_id) REFERENCES events (id))')
    conn.execute("INSERT INTO events (name, date, description) VALUES ('Tech Conference 2024', '2024-12-01', 'A conference for tech enthusiasts.')")
    conn.execute("INSERT INTO events (name, date, description) VALUES ('Music Festival', '2024-08-15', 'An outdoor music festival.')")
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    return render_template('index.html', events=events)

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to])
    msg.body = body
    mail.send(msg)

@app.route('/book/<int:event_id>', methods=['GET', 'POST'])
def book(event_id):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        private_key = secrets.token_urlsafe(16)
        conn = get_db_connection()
        conn.execute('INSERT INTO bookings (event_id, name, email, private_key) VALUES (?, ?, ?, ?)',
                     (event_id, name, email, private_key))
        conn.commit()
        conn.close()

        send_email(email, 'Your Ticket Booking Confirmation', f'Thank you for booking a ticket for {event["name"]}. Your private key is: {private_key}')

        return "Booking successful! Your private key has been sent to your email."

    return render_template('booking.html', event=event)

@app.route('/validate', methods=['GET', 'POST'])
def validate():
    if request.method == 'POST':
        private_key = request.form['private_key']
        conn = get_db_connection()
        booking = conn.execute('SELECT * FROM bookings WHERE private_key = ?', (private_key,)).fetchone()
        if booking:
            event = conn.execute('SELECT * FROM events WHERE id = ?', (booking['event_id'],)).fetchone()
            conn.close()
            return render_template('ticket.html', booking=booking, event=event)
        else:
            conn.close()
            return "Invalid private key."
    return render_template('validate.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return 'Invalid username or password.'
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/validate', methods=['POST'])
def admin_validate():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    booking_id = request.form['booking_id']
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    if booking:
        event = conn.execute('SELECT * FROM events WHERE id = ?', (booking['event_id'],)).fetchone()
        conn.close()
        return render_template('admin_ticket_view.html', booking=booking, event=event)
    else:
        conn.close()
        return "Invalid booking ID."

@app.route('/admin/consume/<int:booking_id>', methods=['POST'])
def consume(booking_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute('UPDATE bookings SET consumed = 1 WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/create_event', methods=['POST'])
def create_event():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    name = request.form['name']
    date = request.form['date']
    description = request.form['description']
    conn = get_db_connection()
    conn.execute('INSERT INTO events (name, date, description) VALUES (?, ?, ?)',
                 (name, date, description))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

#run these command in terminal first to create a virtual environment and install dependencies
#python -m venv venv
#venv\Scripts\activate
#pip install flask flask-sqlalchemy flask-migrate flask-login sqlalchemy requests werkzeug
#python app.py
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
import requests
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import sqlite3

app = Flask(__name__)
app.secret_key = 'hotel_management_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images/hotels'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    points = db.Column(db.Integer, default=0)

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    room_types = db.Column(db.String(200), nullable=False)
    amenities = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200))
    image_url = db.Column(db.String(250), nullable=True)
    is_available = db.Column(db.Boolean, default=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Confirmed')
    paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='reservations')
    hotel = db.relationship('Hotel', backref='reservations')

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'))
    checkin = db.Column(db.Date)
    checkout = db.Column(db.Date)
    status = db.Column(db.String(20), default='Confirmed')
    paid = db.Column(db.Boolean, default=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_type = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    feedback_type = db.Column(db.String(50), nullable=True)
    feedback_details = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PackingChecklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    trip_type = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    season = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='packing_checklists')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    try:
        db.create_all()
        print("Database initialized successfully")
    except OperationalError as e:
        print(f"Database initialization error: {e}")
        flash("An error occurred while initializing the database.", "danger")

  
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(user)")).fetchall()
            columns = [row[1] for row in result]
            if "name" not in columns:
                connection.execute(text("ALTER TABLE user ADD COLUMN name TEXT"))
                print("Added 'name' column to 'user' table")
            if "email" not in columns:
                connection.execute(text("ALTER TABLE user ADD COLUMN email TEXT UNIQUE"))
                print("Added 'email' column to 'user' table")
            if "phone" not in columns:
                connection.execute(text("ALTER TABLE user ADD COLUMN phone TEXT"))
                print("Added 'phone' column to 'user' table")
            if "password" not in columns:
                connection.execute(text("ALTER TABLE user ADD COLUMN password TEXT"))
                print("Added 'password' column to 'user' table")
            if "is_admin" not in columns:
                connection.execute(text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
                print("Added 'is_admin' column to 'user' table")
            if "points" not in columns:
                connection.execute(text("ALTER TABLE user ADD COLUMN points INTEGER DEFAULT 0"))
                print("Added 'points' column to 'user' table")
    except OperationalError as e:
        print(f"User table migration error: {e}")
        flash("An error occurred while migrating the user table.", "danger")

  
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(hotel)")).fetchall()
            columns = [row[1] for row in result]
            if "city" not in columns:
                connection.execute(text("ALTER TABLE hotel ADD COLUMN city TEXT"))
                print("Added 'city' column to 'hotel' table")
            if "address" not in columns:
                connection.execute(text("ALTER TABLE hotel ADD COLUMN address TEXT"))
                print("Added 'address' column to 'hotel' table")
    except OperationalError as e:
        print(f"Hotel table migration error: {e}")
        flash("An error occurred while migrating the hotel table.", "danger")

   
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(booking)")).fetchall()
            columns = [row[1] for row in result]
            if "status" not in columns:
                connection.execute(text("ALTER TABLE booking ADD COLUMN status TEXT DEFAULT 'Confirmed'"))
                print("Added 'status' column to 'booking' table")
            if "paid" not in columns:
                connection.execute(text("ALTER TABLE booking ADD COLUMN paid BOOLEAN DEFAULT 0"))
                print("Added 'paid' column to 'booking' table")
    except OperationalError as e:
        print(f"Booking table migration error: {e}")
        flash("An error occurred while migrating the booking table.", "danger")


    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(reservation)")).fetchall()
            columns = [row[1] for row in result]
            if "status" not in columns:
                connection.execute(text("ALTER TABLE reservation ADD COLUMN status TEXT DEFAULT 'Confirmed'"))
                print("Added 'status' column to 'reservation' table")
            if "paid" not in columns:
                connection.execute(text("ALTER TABLE reservation ADD COLUMN paid BOOLEAN DEFAULT 0"))
                print("Added 'paid' column to 'reservation' table")
    except OperationalError as e:
        print(f"Reservation table migration error: {e}")
        flash("An error occurred while migrating the reservation table.", "danger")


room_data = {
    "Deluxe Room": (150, 50),
    "Standard Room": (100, 60),
    "Suite": (250, 25)
}

def get_discount_percentage(points):
    if points >= 500:
        return 20
    elif points >= 250:
        return 10
    elif points >= 100:
        return 5
    return 0


def init_hotels():
    Hotel.query.delete()
    db.session.commit()
    sample_hotels = [
        # Barishal
        Hotel(name="River View Barishal", city="Barishal", location="Band Road", rating=4.0, price_per_night=1200, room_types="Standard, Deluxe", amenities="WiFi, Breakfast", address="123 Band Road", image_url="default.jpg", is_available=True),
        Hotel(name="Pearl Inn Barishal", city="Barishal", location="Nathullabad", rating=3.8, price_per_night=900, room_types="Single, Double", amenities="WiFi, Parking", address="456 Nathullabad St", image_url="default.jpg", is_available=True),
        Hotel(name="Grand Barishal", city="Barishal", location="Sadar Road", rating=4.3, price_per_night=1800, room_types="Deluxe, Suite", amenities="WiFi, Pool, Gym", address="789 Sadar Road", image_url="default.jpg", is_available=True),
        Hotel(name="Coastal Retreat", city="Barishal", location="Kirtankhola River", rating=3.7, price_per_night=700, room_types="Standard", amenities="WiFi, Restaurant", address="101 Riverbank", image_url="default.jpg", is_available=False),

        # Chattagram (Chittagong)
        Hotel(name="Royal Chittagong", city="Chattagram", location="Agrabad", rating=4.3, price_per_night=3200, room_types="Deluxe, Family Suite", amenities="WiFi, Pool, Spa, Restaurant", address="101 Agrabad Commercial Area", image_url="default.jpg", is_available=True),
        Hotel(name="Bay View Chattagram", city="Chattagram", location="Patenga Beach", rating=4.1, price_per_night=2500, room_types="Deluxe, Suite", amenities="WiFi, Breakfast, Beach Access", address="234 Patenga Road", image_url="default.jpg", is_available=True),
        Hotel(name="Hilltop Residency", city="Chattagram", location="Khulshi", rating=3.9, price_per_night=1500, room_types="Standard, Double", amenities="WiFi, Parking", address="567 Khulshi Hills", image_url="default.jpg", is_available=True),
        Hotel(name="Port City Inn", city="Chattagram", location="Halishahar", rating=4.0, price_per_night=2000, room_types="Single, Deluxe", amenities="WiFi, Gym", address="890 Port Road", image_url="default.jpg", is_available=False),

        # Dhaka
        Hotel(name="Grand Paradise Dhaka", city="Dhaka", location="Gulshan", rating=4.5, price_per_night=3500, room_types="Deluxe, Suite", amenities="WiFi, Pool, Breakfast", address="123 Gulshan Avenue", image_url="default.jpg", is_available=True),
        Hotel(name="City Lights Dhaka", city="Dhaka", location="Banani", rating=4.2, price_per_night=2800, room_types="Standard, Deluxe", amenities="WiFi, Gym, Restaurant", address="456 Banani Road", image_url="default.jpg", is_available=True),
        Hotel(name="Metro Stay", city="Dhaka", location="Dhanmondi", rating=3.8, price_per_night=1200, room_types="Single, Double", amenities="WiFi, Breakfast", address="789 Dhanmondi 27", image_url="default.jpg", is_available=True),
        Hotel(name="Elite Residency", city="Dhaka", location="Uttara", rating=4.4, price_per_night=4000, room_types="Suite, Family", amenities="WiFi, Pool, Spa", address="101 Airport Road", image_url="default.jpg", is_available=True),

        # Khulna
        Hotel(name="Tiger Garden Khulna", city="Khulna", location="Shibbari", rating=4.0, price_per_night=1600, room_types="Standard, Deluxe", amenities="WiFi, Restaurant", address="123 Shibbari More", image_url="default.jpg", is_available=True),
        Hotel(name="Sundarban View", city="Khulna", location="Boyra", rating=3.9, price_per_night=1300, room_types="Single, Double", amenities="WiFi, Parking", address="456 Boyra Main Road", image_url="default.jpg", is_available=True),
        Hotel(name="Royal Khulna", city="Khulna", location="KDA Avenue", rating=4.2, price_per_night=2200, room_types="Deluxe, Suite", amenities="WiFi, Pool, Gym", address="789 KDA Avenue", image_url="default.jpg", is_available=True),
        Hotel(name="Riverfront Inn", city="Khulna", location="Rupsha", rating=3.7, price_per_night=800, room_types="Standard", amenities="WiFi, Breakfast", address="101 Rupsha Ghat", image_url="default.jpg", is_available=False),

        # Gazipur
        Hotel(name="Green Escape Gazipur", city="Gazipur", location="Tongi", rating=3.8, price_per_night=1000, room_types="Standard, Double", amenities="WiFi, Parking", address="123 Tongi Industrial Area", image_url="default.jpg", is_available=True),
        Hotel(name="Forest Retreat", city="Gazipur", location="Mawna", rating=4.1, price_per_night=1800, room_types="Deluxe, Suite", amenities="WiFi, Pool, Restaurant", address="456 Mawna Chowrasta", image_url="default.jpg", is_available=True),
        Hotel(name="Safari Lodge", city="Gazipur", location="Sreepur", rating=3.9, price_per_night=1400, room_types="Single, Family", amenities="WiFi, Breakfast", address="789 Sreepur Road", image_url="default.jpg", is_available=True),
        Hotel(name="Eco Haven", city="Gazipur", location="Kapasia", rating=4.0, price_per_night=2000, room_types="Deluxe, Cottage", amenities="WiFi, Nature Trails", address="101 Kapasia Village", image_url="default.jpg", is_available=True),

        # Jessore
        Hotel(name="Jashore Palace", city="Jessore", location="Rail Road", rating=4.0, price_per_night=1500, room_types="Standard, Deluxe", amenities="WiFi, Breakfast", address="123 Rail Road", image_url="default.jpg", is_available=True),
        Hotel(name="Moonlight Inn", city="Jessore", location="Chanchra", rating=3.7, price_per_night=900, room_types="Single, Double", amenities="WiFi, Parking", address="456 Chanchra Bazar", image_url="default.jpg", is_available=True),
        Hotel(name="Heritage Jessore", city="Jessore", location="Muralidaha", rating=4.2, price_per_night=2100, room_types="Deluxe, Suite", amenities="WiFi, Pool, Gym", address="789 Muralidaha Road", image_url="default.jpg", is_available=True),
        Hotel(name="City Comfort", city="Jessore", location="Barinagar", rating=3.8, price_per_night=1100, room_types="Standard", amenities="WiFi, Restaurant", address="101 Barinagar", image_url="default.jpg", is_available=False),

        # Savar
        Hotel(name="Savar Serenity", city="Savar", location="EPZ Area", rating=3.9, price_per_night=1300, room_types="Standard, Double", amenities="WiFi, Breakfast", address="123 EPZ Road", image_url="default.jpg", is_available=True),
        Hotel(name="Green Valley Savar", city="Savar", location="Nobinagar", rating=4.1, price_per_night=1900, room_types="Deluxe, Suite", amenities="WiFi, Pool, Restaurant", address="456 Nobinagar", image_url="default.jpg", is_available=True),
        Hotel(name="Urban Escape", city="Savar", location="Bazar Road", rating=3.8, price_per_night=1000, room_types="Single, Family", amenities="WiFi, Parking", address="789 Bazar Road", image_url="default.jpg", is_available=True),
        Hotel(name="Lakeside Inn", city="Savar", location="Jahangirnagar", rating=4.0, price_per_night=1700, room_types="Deluxe, Cottage", amenities="WiFi, Lake View", address="101 Lake Road", image_url="default.jpg", is_available=True),

        # Sylhet
        Hotel(name="BlueMoon Sylhet", city="Sylhet", location="Zindabazar", rating=3.9, price_per_night=3000, room_types="Single, Double", amenities="WiFi, Breakfast, Parking", address="789 Zindabazar Street", image_url="default.jpg", is_available=True),
        Hotel(name="Tea Garden Resort", city="Sylhet", location="Sreemangal", rating=4.4, price_per_night=3500, room_types="Deluxe, Suite", amenities="WiFi, Pool, Spa", address="123 Tea Estate Road", image_url="default.jpg", is_available=True),
        Hotel(name="Valley View Sylhet", city="Sylhet", location="Jaintapur", rating=4.0, price_per_night=2000, room_types="Standard, Family", amenities="WiFi, Restaurant", address="456 Jaintapur Hills", image_url="default.jpg", is_available=True),
        Hotel(name="Riverside Retreat", city="Sylhet", location="Surma River", rating=4.2, price_per_night=2800, room_types="Deluxe, Cottage", amenities="WiFi, River View, Breakfast", address="101 Surma Bank", image_url="default.jpg", is_available=True),
    ]
    db.session.add_all(sample_hotels)
    db.session.commit()

with app.app_context():
    init_hotels()

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['checkin'] = request.form['checkin']
        session['checkout'] = request.form['checkout']
        session['adults'] = request.form['adults']
        session['children'] = request.form['children']
        return redirect(url_for('search_hotels'))
    return render_template("home.html")

@app.route('/search')
def search_hotels():
    hotels = Hotel.query.all()
    city_order = ['Barishal', 'Chattagram', 'Dhaka', 'Khulna', 'Gazipur', 'Jessore', 'Savar', 'Sylhet']
    hotels.sort(key=lambda h: city_order.index(h.city) if h.city in city_order else 999)
    return render_template('search.html', hotels=hotels)

@app.route('/book_hotel/<int:hotel_id>', methods=['POST'])
@login_required
def book_hotel(hotel_id):
    checkin = request.form.get('checkin')
    checkout = request.form.get('checkout')
    try:
        checkin_date = datetime.strptime(checkin, '%Y-%m-%d')
        checkout_date = datetime.strptime(checkout, '%Y-%m-%d')
    except (ValueError, TypeError):
        flash("Invalid or missing date", "danger")
        return redirect(url_for('search_hotels'))
    
    hotel = Hotel.query.get_or_404(hotel_id)
    nights = (checkout_date - checkin_date).days
    total_price = hotel.price_per_night * nights
    
    reservation = Reservation(
        user_id=current_user.id,
        hotel_id=hotel_id,
        check_in_date=checkin_date,
        check_out_date=checkout_date,
        total_price=total_price
    )
    booking = Booking(
        user_id=current_user.id,
        hotel_id=hotel_id,
        checkin=checkin_date,
        checkout=checkout_date
    )
    db.session.add(reservation)
    db.session.add(booking)
    db.session.commit()
    flash("Booking successful! Proceed to payment.", "success")
    return redirect(url_for('payment', room_type='Hotel Room'))

@app.route('/my_bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    return render_template('my_bookings.html', bookings=bookings, reservations=reservations)

@app.route('/cancel/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id == current_user.id:
        booking.status = 'Cancelled'
        db.session.commit()
        flash("Booking cancelled successfully", "success")
    return redirect(url_for('my_bookings'))

@app.route('/reservation/<int:reservation_id>/cancel')
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id == current_user.id and reservation.status not in ['Completed', 'Cancelled']:
        reservation.status = 'Cancelled'
        db.session.commit()
        flash("Reservation cancelled successfully", "success")
    else:
        flash("Cannot cancel this reservation", "danger")
    return redirect(url_for('my_bookings'))

@app.route('/reservation/<int:reservation_id>/modify', methods=['GET', 'POST'])
@login_required
def modify_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id:
        flash("You don't have permission to modify this reservation", "danger")
        return redirect(url_for('my_bookings'))
    if reservation.status in ['Completed', 'Cancelled']:
        flash("This reservation cannot be modified", "warning")
        return redirect(url_for('my_bookings'))
    
    if request.method == 'POST':
        new_check_in = datetime.strptime(request.form.get('check_in'), '%Y-%m-%d')
        new_check_out = datetime.strptime(request.form.get('check_out'), '%Y-%m-%d')
        nights = (new_check_out - new_check_in).days
        new_total = reservation.hotel.price_per_night * nights
        reservation.check_in_date = new_check_in
        reservation.check_out_date = new_check_out
        reservation.total_price = new_total
        db.session.commit()
        flash("Reservation modified successfully", "success")
        return redirect(url_for('my_bookings'))
    
    return render_template('modify_reservation.html', reservation=reservation)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')

       
        existing_user_email = User.query.filter_by(email=email).first()
        existing_user_phone = User.query.filter_by(phone=phone).first()

        if existing_user_email:
            flash("Email is already registered.", "danger")
            return redirect(url_for('register'))

        if existing_user_phone:
            flash("Phone number is already registered.", "danger")
            return redirect(url_for('register'))

        
        new_user = User(name=name, email=email, password=password, phone=phone)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully!", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            session['user_id'] = user.id
            session['user_points'] = user.points
            flash("Logged in successfully!", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid email or password.", "danger")
    return render_template('home.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    session.pop('user_points', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(current_user.id)
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', user=user, bookings=bookings, reservations=reservations)

@app.route('/update', methods=['GET', 'POST'])
@login_required
def update():
    user = User.query.get(current_user.id)
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.password = request.form.get('password')
        user.phone = request.form.get('phone')
        db.session.commit()
        flash("Information updated successfully!", "success")
        return redirect(url_for('dashboard'))
    return render_template('update.html', user=user)

@app.route("/delete", methods=["GET", "POST"])
def delete():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and user.password == password and user.id == session.get("user_id"):
        
            PackingChecklist.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            session.pop("user_id", None)
            session.pop("user_points", None)
            flash("Account deleted successfully!", "success")
            return redirect("/")
        else:
            flash("Invalid email or password.", "danger")

    return render_template("delete.html")
@app.route('/rooms', methods=['GET', 'POST'])
@login_required
def rooms():
    if request.method == 'POST':
        room_type = request.form.get('room_type')
        max_price = request.form.get('max_price')
        filtered_rooms = [
            {"type": room, "price": price, "available": available}
            for room, (price, available) in room_data.items()
            if (room_type in room or not room_type) and (price <= int(max_price) if max_price else True)
        ]
        return render_template('rooms.html', rooms=filtered_rooms)

    rooms_list = [
        {"type": room, "price": price, "available": available}
        for room, (price, available) in room_data.items()
    ]
    return render_template('rooms.html', rooms=rooms_list)

@app.route('/book', methods=['POST'])
@login_required
def book_room():
    room_type = request.form.get('room_type')
    discounted_price = request.form.get('discounted_price')

    if not room_type or room_type not in room_data:
        flash("Invalid room type.", "danger")
        return redirect('/rooms')

    if room_data[room_type][1] <= 0:
        flash("No rooms available.", "danger")
        return redirect('/rooms')

    user = User.query.get(current_user.id)
    points_earned = {'Standard Room': 3, 'Deluxe Room': 6, 'Suite': 9}
    user.points += points_earned.get(room_type, 0)
    session['user_points'] = user.points
    db.session.commit()

    session['room_type'] = room_type
    if discounted_price:
        session['discounted_price'] = discounted_price

    flash(f"Proceed to payment for {room_type}", "info")
    return redirect(url_for('payment', room_type=room_type))

@app.route('/payment')
@login_required
def payment():
    room_type = request.args.get('room_type')
    return render_template('payment.html', room_type=room_type)

@app.route('/payment_success', methods=['POST'])
@login_required
def payment_success():
    room_type = session.get('room_type')
    payment_method = request.form.get('payment_method')
    discounted_price = session.get('discounted_price')
    
    if not room_type or room_type not in room_data:
        flash("Invalid room type.", "danger")
        return redirect(url_for('rooms'))
    
    if room_data[room_type][1] <= 0:
        flash("No rooms available.", "danger")
        return redirect(url_for('rooms'))
    
    if payment_method == 'online_banking':
        if not all([request.form.get('card_number'), request.form.get('expiry_date'), request.form.get('cvv')]):
            flash("All online banking fields are required.", "danger")
            return redirect(url_for('payment', room_type=room_type))
    elif payment_method == 'mobile_banking':
        if not all([request.form.get('mobile_service'), request.form.get('account_number'), request.form.get('pin')]):
            flash("All mobile banking fields are required.", "danger")
            return redirect(url_for('payment', room_type=room_type))
    else:
        flash("Invalid payment method.", "danger")
        return redirect(url_for('payment', room_type=room_type))
    
    
    room_data[room_type] = (room_data[room_type][0], room_data[room_type][1] - 1)
    
    
    if discounted_price:
        original_price = room_data[room_type][0]
        discount_percent = get_discount_percentage(session.get('user_points', 0))
        flash(f"Payment for {room_type} successful! Saved ${original_price - int(discounted_price)} ({discount_percent}% off)!", "success")
    else:
        flash(f"Payment for {room_type} successful! Remaining: {room_data[room_type][1]}", "success")
    
    session['feedback_room'] = room_type
    return redirect(url_for('thank_you'))

@app.route('/payment_failure', methods=['POST'])
@login_required
def payment_failure():
    return render_template('payment_failure.html')

@app.route('/thank_you')
@login_required
def thank_you():
    room_type = session.get('feedback_room')
    if not room_type:
        flash("No booking information available.", "warning")
        return redirect(url_for('rooms'))
    return render_template('thank_you.html', room_type=room_type)

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        room_type = request.form.get('room_type')
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        feedback_type = request.form.get('feedback_type')
        feedback_details = request.form.get('feedback_details')
        priority = request.form.get('priority')
        
        if not room_type or not rating:
            flash("Room type and rating are required.", "danger")
            return redirect(url_for('feedback'))
        
        new_feedback = Feedback(
            room_type=room_type,
            rating=int(rating),
            comment=comment,
            feedback_type=feedback_type,
            feedback_details=feedback_details,
            priority=priority
        )
        db.session.add(new_feedback)
        db.session.commit()
        session.pop('feedback_room', None)
        flash("Thank you for your feedback!", "success")
        return redirect(url_for('dashboard'))
    
    room_type = request.args.get('room_type') or session.get('feedback_room')
    room_types = list(room_data.keys())
    return render_template('feedback.html', room_types=room_types, room_type=room_type)

@app.route('/feedbacks')
@login_required
def feedbacks():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    room_types = list(room_data.keys())
    return render_template('feedbacks.html', feedbacks=feedbacks, room_types=room_types)

@app.route('/faq')
def faq():
    try:
        category = request.args.get('category')
        search_query = request.args.get('search')

        
        if FAQ.query.count() == 0:
            sample_faqs = [
                FAQ(question="How do I cancel a booking?", answer="Go to 'My Reservations' page, select your booking, and click 'Cancel'.", category="Booking"),
                FAQ(question="Can I change my check-in date?", answer="Yes, modify up to 24 hours before arrival.", category="Booking"),
                FAQ(question="What payment methods do you accept?", answer="Credit cards, PayPal, bank transfers.", category="Payments"),
                FAQ(question="Why was my card declined?", answer="Check funds or details.", category="Payments"),
                FAQ(question="How do I reset my password?", answer="Use 'Forgot Password' link.", category="Account"),
                FAQ(question="How do I delete my account?", answer="Go to profile settings.", category="Account"),
                FAQ(question="How do I earn reward points?", answer="Earn 3-9 points per booking.", category="Loyalty Points"),
                FAQ(question="Do points expire?", answer="No, points never expire.", category="Loyalty Points"),
                FAQ(question="What is your refund policy?", answer="Full refunds 24 hours before check-in.", category="Policies"),
                FAQ(question="Are pets allowed?", answer="Yes, with fees.", category="Policies"),
                FAQ(question="Why no confirmation email?", answer="Check spam or contact support.", category="Technical Issues"),
                FAQ(question="Site not loading?", answer="Clear cache or contact support.", category="Technical Issues")
            ]
            db.session.add_all(sample_faqs)
            db.session.commit()
            print("Sample FAQs inserted successfully")

        # Filter FAQs by category or search query
        faqs = FAQ.query.filter_by(category=category).all() if category else FAQ.query.all()
        if search_query:
            faqs = [faq for faq in faqs if search_query.lower() in faq.question.lower() or search_query.lower() in faq.answer.lower()]

        # Sort FAQs and extract categories
        faqs.sort(key=lambda x: (x.category, x.question))
        categories = sorted(set(faq.category for faq in FAQ.query.all()))

        print(f"Rendering FAQ page: {len(faqs)} FAQs, {len(categories)} categories")
        return render_template('faq.html', faqs=faqs, categories=categories, selected_category=category, search_query=search_query)
    except Exception as e:
        print(f"Error in FAQ route: {str(e)}")
        flash("An error occurred while loading the FAQ page. Please try again later.", "danger")
        return render_template('faq.html', faqs=[], categories=[], selected_category=None, search_query=None)

@app.route('/faq/<int:faq_id>/view')
def faq_view(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    faq.view_count += 1
    db.session.commit()
    return jsonify({'success': True})

@app.route('/faq/<int:faq_id>/feedback', methods=['POST'])
@login_required
def faq_feedback(faq_id):
    feedback_type = request.form.get('feedback_type')
    if feedback_type not in ['helpful', 'not_helpful']:
        return jsonify({'success': False, 'message': 'Invalid feedback type'}), 400
    return redirect(url_for('feedback'))

@app.route('/compare')
def compare_hotels():
    hotels = Hotel.query.all()
    return render_template('compare.html', hotels=hotels)

@app.route('/add_to_compare/<int:hotel_id>')
@login_required
def add_to_compare(hotel_id):
    if 'compare_list' not in session:
        session['compare_list'] = []
    if len(session['compare_list']) < 3 and hotel_id not in session['compare_list']:
        session['compare_list'].append(hotel_id)
        session.modified = True
        flash('Hotel added to comparison', 'success')
    elif len(session['compare_list']) >= 3:
        flash('You can only compare up to 3 hotels', 'warning')
    return redirect(url_for('compare_hotels'))

@app.route('/remove_from_compare/<int:hotel_id>')
@login_required
def remove_from_compare(hotel_id):
    if 'compare_list' in session and hotel_id in session['compare_list']:
        session['compare_list'].remove(hotel_id)
        session.modified = True
        flash('Hotel removed from comparison', 'success')
    return redirect(url_for('compare_hotels'))

@app.route('/clear_compare')
@login_required
def clear_compare():
    session.pop('compare_list', None)
    flash('Comparison cleared', 'success')
    return redirect(url_for('compare_hotels'))

@app.route('/packing-checklist', methods=['GET', 'POST'])
@login_required
def packing_checklist():
    if request.method == 'POST':
        destination = request.form.get('destination')
        trip_type = request.form.get('trip_type')
        duration = int(request.form.get('duration'))
        season = request.form.get('season')
        checklist_items = generate_checklist(destination, trip_type, duration, season)
        new_checklist = PackingChecklist(
            user_id=current_user.id,
            destination=destination,
            trip_type=trip_type,
            duration=duration,
            season=season,
            items=json.dumps(checklist_items)
        )
        db.session.add(new_checklist)
        db.session.commit()
        return render_template('checklist.html', checklist=checklist_items, destination=destination, trip_type=trip_type, duration=duration, season=season)
    return render_template('packing_checklist.html')

@app.route('/checklist/<int:checklist_id>')
@login_required
def view_checklist(checklist_id):
    checklist = PackingChecklist.query.get_or_404(checklist_id)
    if checklist.user_id != current_user.id:
        flash('You don't have permission to view this checklist', 'danger')
        return redirect(url_for('packing_checklist'))
    return render_template('checklist.html', checklist=json.loads(checklist.items), destination=checklist.destination, trip_type=checklist.trip_type, duration=checklist.duration, season=checklist.season)

@app.route('/checklist/<int:checklist_id>/complete', methods=['POST'])
@login_required
def complete_checklist(checklist_id):
    checklist = PackingChecklist.query.get_or_404(checklist_id)
    if checklist.user_id != current_user.id:
        flash('You don't have permission to update this checklist', 'danger')
        return redirect(url_for('packing_checklist'))
    checklist.is_completed = True
    db.session.commit()
    flash('Checklist marked as completed!', 'success')
    return redirect(url_for('view_checklist', checklist_id=checklist_id))

def generate_checklist(destination, trip_type, duration, season):
    checklist = [
        'Passport/ID', 'Travel documents', 'Money/Credit cards', 'Phone charger', 'Medications', 'Toiletries', 'First aid kit'
    ]
    if destination.lower() == 'cox\'s bazar':
        checklist.extend(['Sunscreen (SPF 50+)', 'Swimwear', 'Beach towel', 'Flip-flops', 'Beach bag', 'Sunglasses', 'Hat'])
    elif destination.lower() == 'sreemangal':
        checklist.extend(['Bug spray', 'Comfortable hiking shoes', 'Water bottle', 'Rain jacket', 'Binoculars', 'Camera'])
    elif destination.lower() == 'sylhet':
        checklist.extend(['Umbrella', 'Waterproof jacket', 'Comfortable walking shoes', 'Camera', 'Power bank'])
    if trip_type.lower() == 'business':
        checklist.extend(['Business attire', 'Laptop', 'Notebook', 'Business cards', 'Formal shoes'])
    elif trip_type.lower() == 'beach':
        checklist.extend(['Beach umbrella', 'Beach mat', 'Snorkeling gear', 'Beach games'])
    elif trip_type.lower() == 'mountain':
        checklist.extend(['Hiking boots', 'Warm layers', 'Trekking poles', 'Headlamp', 'Thermal wear'])
    if season.lower() == 'summer':
        checklist.extend(['Light clothing', 'Sunscreen', 'Sunglasses', 'Hat', 'Summer shoes'])
    elif season.lower() == 'winter':
        checklist.extend(['Warm clothing', 'Winter coat', 'Gloves', 'Scarf', 'Thermal wear'])
    elif season.lower() == 'monsoon':
        checklist.extend(['Raincoat', 'Umbrella', 'Waterproof shoes', 'Quick-dry clothes'])
    if duration > 7:
        checklist.extend(['Laundry supplies', 'Extra clothes', 'Travel-size toiletries'])
    return checklist


HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_API_KEY = "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"

@app.route('/chatbot-api', methods=['POST'])
def chatbot_api():
    user_input = request.json.get('message')
    headers = {'Authorization': f'Bearer {HF_API_KEY}'}
    payload = {'inputs': f'User: {user_input}\nAssistant:'}
    response = requests.post(HF_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        ai_reply = response.json()[0]['generated_text'].split('Assistant:')[-1].strip()
        return jsonify({'reply': ai_reply})
    return jsonify({'reply': 'Chatbot unavailable.'}), 503

@app.route('/chatbot-ui')
def chatbot_ui():
    return render_template('chatbot.html')

# Admin Routes
def admin_required(f):
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/admin')
@admin_required
def admin_dashboard():
    hotels = Hotel.query.all()
    return render_template('admin_dashboard.html', hotels=hotels)

@app.route('/admin/add', methods=['GET', 'POST'])
@admin_required
def add_hotel():
    if request.method == 'POST':
        image = request.files.get('image')
        filename = secure_filename(image.filename) if image else 'default.jpg'
        if image:
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_hotel = Hotel(
            name=request.form['name'],
            city=request.form['city'],
            location=request.form['location'],
            rating=float(request.form['rating']),
            price_per_night=float(request.form['price']),
            room_types=request.form['room_types'],
            amenities=request.form['amenities'],
            address=request.form['address'],
            image_url=filename,
            is_available=request.form.get('is_available') == 'on'
        )
        db.session.add(new_hotel)
        db.session.commit()
        flash('Hotel added successfully!', 'success')
        return redirect(url_for('admin'))
    return render_template('add_hotel.html')

@app.route('/admin/edit/<int:hotel_id>', methods=['GET', 'POST'])
@admin_required
def edit_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    if request.method == 'POST':
        hotel.name = request.form['name']
        hotel.city = request.form['city']
        hotel.location = request.form['location']
        hotel.rating = float(request.form['rating'])
        hotel.price_per_night = float(request.form['price'])
        hotel.room_types = request.form['room_types']
        hotel.amenities = request.form['amenities']
        hotel.address = request.form['address']
        hotel.is_available = request.form.get('is_available') == 'on'
        image = request.files.get('image')
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            hotel.image_url = filename
        db.session.commit()
        flash('Hotel updated successfully!', 'success')
        return redirect(url_for('admin'))
    return render_template('edit_hotel.html', hotel=hotel)

@app.route('/admin/delete/<int:hotel_id>', methods=['POST'])
@admin_required
def delete_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    db.session.delete(hotel)
    db.session.commit()
    flash('Hotel deleted successfully!', 'success')
    return redirect(url_for('admin'))

# Define the database path
DB_PATH = 'hotel_management.db'

# --- Initialize Database on Startup , create connections ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create transactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hotel_name TEXT,
        booking_date TEXT,
        amount_paid REAL,
        payment_status TEXT,
        package_number TEXT,
        package_type TEXT
    )
    ''')

    # Create reviews table (with username support)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        username TEXT,
        review_text TEXT,
        FOREIGN KEY (transaction_id) REFERENCES transactions (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# --- DB Connection ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Transaction History Page ---
@app.route('/transactions')  # Changed from '/' to '/transactions'
@login_required  # Added login requirement
def transaction_history():
    conn = get_db_connection()
    transactions = conn.execute('SELECT * FROM transactions').fetchall()
    conn.close()
    return render_template('transaction_history.html', transactions=transactions)

# --- Review Page ---
@app.route('/review/<int:transaction_id>', methods=['GET', 'POST'])
@login_required  # Added login requirement
def review(transaction_id):
    conn = get_db_connection()
    username = None

    if request.method == 'POST':
        username = request.form['username']
        review_text = request.form['review_text']
        if username.strip() and review_text.strip():
            conn.execute(
                'INSERT INTO reviews (transaction_id, username, review_text) VALUES (?, ?, ?)',
                (transaction_id, username, review_text)
            )
            conn.commit()
        return redirect(f"/review/{transaction_id}?username={username}")

    username = request.args.get('username')

    all_reviews = conn.execute(
        'SELECT review_text FROM reviews WHERE transaction_id = ?',
        (transaction_id,)
    ).fetchall()

    user_reviews = []
    if username:
        user_reviews = conn.execute(
            'SELECT review_text FROM reviews WHERE transaction_id = ? AND username = ?',
            (transaction_id, username)
        ).fetchall()

    conn.close()
    return render_template('review.html', all_reviews=all_reviews, user_reviews=user_reviews)

# --- Search Transactions ---
@app.route('/search_transactions')  # Changed from '/search' to '/search_transactions'
@login_required  # Added login requirement
def search_transactions():
    query = request.args.get('query', '')
    conn = get_db_connection()
    transactions = conn.execute(
        "SELECT * FROM transactions WHERE hotel_name LIKE ? OR package_type LIKE ?",
        ('%' + query + '%', '%' + query + '%')
    ).fetchall()
    conn.close()
    return render_template('transaction_history.html', transactions=transactions)

# Run the Flask app
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True)

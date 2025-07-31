from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    user_type = db.Column(db.String(20), nullable=False)  # client, delivery_person
    
    # Client specific fields
    preferred_payment_method = db.Column(db.String(50), nullable=True)
    
    # Delivery person specific fields
    vehicle_type = db.Column(db.String(50), nullable=True)  # motorcycle, car
    vehicle_model = db.Column(db.String(100), nullable=True)
    vehicle_plate = db.Column(db.String(20), nullable=True)
    vehicle_color = db.Column(db.String(50), nullable=True)
    license_number = db.Column(db.String(50), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    
    # Ratings and stats
    average_rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    total_deliveries = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'user_type': self.user_type,
            'preferred_payment_method': self.preferred_payment_method,
            'vehicle_type': self.vehicle_type,
            'vehicle_model': self.vehicle_model,
            'vehicle_plate': self.vehicle_plate,
            'vehicle_color': self.vehicle_color,
            'license_number': self.license_number,
            'is_verified': self.is_verified,
            'is_online': self.is_online,
            'current_lat': self.current_lat,
            'current_lng': self.current_lng,
            'average_rating': self.average_rating,
            'total_ratings': self.total_ratings,
            'total_deliveries': self.total_deliveries,
            'total_earnings': self.total_earnings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None
        }


from datetime import datetime
from . import db

class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Pickup and delivery addresses
    pickup_address = db.Column(db.String(255), nullable=False)
    pickup_lat = db.Column(db.Float, nullable=True)
    pickup_lng = db.Column(db.Float, nullable=True)
    
    delivery_address = db.Column(db.String(255), nullable=False)
    delivery_lat = db.Column(db.Float, nullable=True)
    delivery_lng = db.Column(db.Float, nullable=True)
    
    # Item details
    item_type = db.Column(db.String(50), nullable=False)  # documento, objeto_pequeno, encomenda_leve
    item_description = db.Column(db.Text, nullable=True)
    
    # Pricing and timing
    estimated_price = db.Column(db.Float, nullable=False)
    final_price = db.Column(db.Float, nullable=True)
    estimated_time = db.Column(db.Integer, nullable=False)  # in minutes
    
    # Status tracking
    status = db.Column(db.String(50), nullable=False, default='pending')  
    # pending, accepted, picked_up, in_transit, delivered, cancelled
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    # Payment
    payment_method = db.Column(db.String(50), nullable=False)  # pix, card, wallet
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    
    # Ratings
    client_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    delivery_person_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    client_comment = db.Column(db.Text, nullable=True)
    delivery_person_comment = db.Column(db.Text, nullable=True)
    
    # Proof of delivery
    proof_photo_url = db.Column(db.String(255), nullable=True)
    signature_data = db.Column(db.Text, nullable=True)
    
    # Relationships
    client = db.relationship('User', foreign_keys=[client_id], backref='client_deliveries')
    delivery_person = db.relationship('User', foreign_keys=[delivery_person_id], backref='delivery_person_deliveries')
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'delivery_person_id': self.delivery_person_id,
            'pickup_address': self.pickup_address,
            'pickup_lat': self.pickup_lat,
            'pickup_lng': self.pickup_lng,
            'delivery_address': self.delivery_address,
            'delivery_lat': self.delivery_lat,
            'delivery_lng': self.delivery_lng,
            'item_type': self.item_type,
            'item_description': self.item_description,
            'estimated_price': self.estimated_price,
            'final_price': self.final_price,
            'estimated_time': self.estimated_time,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
            'picked_up_at': self.picked_up_at.isoformat() if self.picked_up_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'client_rating': self.client_rating,
            'delivery_person_rating': self.delivery_person_rating,
            'client_comment': self.client_comment,
            'delivery_person_comment': self.delivery_person_comment,
            'proof_photo_url': self.proof_photo_url,
            'signature_data': self.signature_data
        }


from datetime import datetime
from . import db

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), nullable=False, default='text')  # text, predefined, system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    delivery = db.relationship('Delivery', backref='chat_messages')
    sender = db.relationship('User', backref='sent_messages')
    
    def to_dict(self):
        return {
            'id': self.id,
            'delivery_id': self.delivery_id,
            'sender_id': self.sender_id,
            'message': self.message,
            'message_type': self.message_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'sender_name': self.sender.name if self.sender else None
        }


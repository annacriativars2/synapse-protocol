from flask import Blueprint, request, jsonify
from src.models.chat import db, Chat
from src.models.delivery import Delivery
from src.models.user import User
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

# Predefined quick messages
QUICK_MESSAGES = [
    "Estou a caminho da retirada",
    "Cheguei no local de retirada",
    "Item coletado, a caminho da entrega",
    "Chegando no local de entrega",
    "Entrega realizada com sucesso",
    "Não encontrei o endereço",
    "Trânsito intenso, atraso de alguns minutos",
    "Pode deixar na portaria?",
    "Preciso falar com você",
    "Obrigado!"
]

@chat_bp.route('/chat/quick-messages', methods=['GET'])
def get_quick_messages():
    return jsonify({
        'success': True,
        'messages': QUICK_MESSAGES
    }), 200

@chat_bp.route('/chat/<int:delivery_id>/messages', methods=['GET'])
def get_chat_messages(delivery_id):
    try:
        # Verify delivery exists
        delivery = Delivery.query.get_or_404(delivery_id)
        
        messages = Chat.query.filter_by(delivery_id=delivery_id).order_by(Chat.created_at.asc()).all()
        
        return jsonify({
            'success': True,
            'messages': [message.to_dict() for message in messages]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@chat_bp.route('/chat/<int:delivery_id>/send', methods=['POST'])
def send_message(delivery_id):
    try:
        data = request.get_json()
        
        # Verify delivery exists
        delivery = Delivery.query.get_or_404(delivery_id)
        
        # Verify sender is part of this delivery
        sender_id = data['sender_id']
        if sender_id not in [delivery.client_id, delivery.delivery_person_id]:
            return jsonify({
                'success': False,
                'error': 'Usuário não autorizado para este chat'
            }), 403
        
        message = Chat(
            delivery_id=delivery_id,
            sender_id=sender_id,
            message=data['message'],
            message_type=data.get('message_type', 'text')
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@chat_bp.route('/chat/<int:delivery_id>/mark-read', methods=['POST'])
def mark_messages_read(delivery_id):
    try:
        data = request.get_json()
        user_id = data['user_id']
        
        # Mark all messages in this delivery as read by this user
        # (except messages sent by the user themselves)
        messages = Chat.query.filter(
            Chat.delivery_id == delivery_id,
            Chat.sender_id != user_id,
            Chat.read_at.is_(None)
        ).all()
        
        for message in messages:
            message.read_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(messages)} mensagens marcadas como lidas'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@chat_bp.route('/chat/<int:delivery_id>/unread-count/<int:user_id>', methods=['GET'])
def get_unread_count(delivery_id, user_id):
    try:
        # Count unread messages for this user in this delivery
        count = Chat.query.filter(
            Chat.delivery_id == delivery_id,
            Chat.sender_id != user_id,
            Chat.read_at.is_(None)
        ).count()
        
        return jsonify({
            'success': True,
            'unread_count': count
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


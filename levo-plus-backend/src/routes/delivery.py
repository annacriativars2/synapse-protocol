from flask import Blueprint, request, jsonify
from src.models.delivery import db, Delivery
from src.models.user import User
from datetime import datetime
import random

delivery_bp = Blueprint('delivery', __name__)

@delivery_bp.route('/deliveries', methods=['POST'])
def create_delivery():
    try:
        data = request.get_json()
        
        # Calculate estimated price based on distance and item type
        base_price = 8.0
        item_multipliers = {
            'documento': 1.0,
            'objeto_pequeno': 1.2,
            'encomenda_leve': 1.5
        }
        
        estimated_price = base_price * item_multipliers.get(data.get('item_type', 'documento'), 1.0)
        estimated_time = random.randint(15, 45)  # Random time between 15-45 minutes
        
        delivery = Delivery(
            client_id=data['client_id'],
            pickup_address=data['pickup_address'],
            pickup_lat=data.get('pickup_lat'),
            pickup_lng=data.get('pickup_lng'),
            delivery_address=data['delivery_address'],
            delivery_lat=data.get('delivery_lat'),
            delivery_lng=data.get('delivery_lng'),
            item_type=data['item_type'],
            item_description=data.get('item_description', ''),
            estimated_price=estimated_price,
            estimated_time=estimated_time,
            payment_method=data['payment_method'],
            status='pending'
        )
        
        db.session.add(delivery)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'delivery': delivery.to_dict(),
            'message': 'Entrega criada com sucesso'
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@delivery_bp.route('/deliveries/available', methods=['GET'])
def get_available_deliveries():
    try:
        # Get deliveries that are pending (not yet accepted)
        deliveries = Delivery.query.filter_by(status='pending').all()
        
        return jsonify({
            'success': True,
            'deliveries': [delivery.to_dict() for delivery in deliveries]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@delivery_bp.route('/deliveries/<int:delivery_id>/accept', methods=['POST'])
def accept_delivery(delivery_id):
    try:
        data = request.get_json()
        delivery_person_id = data['delivery_person_id']
        
        delivery = Delivery.query.get_or_404(delivery_id)
        
        if delivery.status != 'pending':
            return jsonify({
                'success': False,
                'error': 'Esta entrega não está mais disponível'
            }), 400
        
        delivery.delivery_person_id = delivery_person_id
        delivery.status = 'accepted'
        delivery.accepted_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'delivery': delivery.to_dict(),
            'message': 'Entrega aceita com sucesso'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@delivery_bp.route('/deliveries/<int:delivery_id>/pickup', methods=['POST'])
def confirm_pickup(delivery_id):
    try:
        delivery = Delivery.query.get_or_404(delivery_id)
        
        if delivery.status != 'accepted':
            return jsonify({
                'success': False,
                'error': 'Entrega não pode ser coletada neste momento'
            }), 400
        
        delivery.status = 'picked_up'
        delivery.picked_up_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'delivery': delivery.to_dict(),
            'message': 'Coleta confirmada com sucesso'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@delivery_bp.route('/deliveries/<int:delivery_id>/deliver', methods=['POST'])
def confirm_delivery(delivery_id):
    try:
        data = request.get_json()
        
        delivery = Delivery.query.get_or_404(delivery_id)
        
        if delivery.status != 'picked_up':
            return jsonify({
                'success': False,
                'error': 'Entrega não pode ser finalizada neste momento'
            }), 400
        
        delivery.status = 'delivered'
        delivery.delivered_at = datetime.utcnow()
        delivery.final_price = delivery.estimated_price
        delivery.payment_status = 'completed'
        
        # Update delivery person stats
        delivery_person = User.query.get(delivery.delivery_person_id)
        if delivery_person:
            delivery_person.total_deliveries += 1
            delivery_person.total_earnings += delivery.final_price * 0.8  # 80% for delivery person
        
        if data.get('proof_photo_url'):
            delivery.proof_photo_url = data['proof_photo_url']
        
        if data.get('signature_data'):
            delivery.signature_data = data['signature_data']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'delivery': delivery.to_dict(),
            'message': 'Entrega finalizada com sucesso'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@delivery_bp.route('/deliveries/<int:delivery_id>', methods=['GET'])
def get_delivery(delivery_id):
    try:
        delivery = Delivery.query.get_or_404(delivery_id)
        
        return jsonify({
            'success': True,
            'delivery': delivery.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@delivery_bp.route('/deliveries/user/<int:user_id>', methods=['GET'])
def get_user_deliveries(user_id):
    try:
        user_type = request.args.get('user_type', 'client')
        
        if user_type == 'client':
            deliveries = Delivery.query.filter_by(client_id=user_id).order_by(Delivery.created_at.desc()).all()
        else:
            deliveries = Delivery.query.filter_by(delivery_person_id=user_id).order_by(Delivery.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'deliveries': [delivery.to_dict() for delivery in deliveries]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@delivery_bp.route('/deliveries/<int:delivery_id>/rate', methods=['POST'])
def rate_delivery(delivery_id):
    try:
        data = request.get_json()
        
        delivery = Delivery.query.get_or_404(delivery_id)
        user_type = data['user_type']
        rating = data['rating']
        comment = data.get('comment', '')
        
        if user_type == 'client':
            delivery.client_rating = rating
            delivery.client_comment = comment
            
            # Update delivery person average rating
            delivery_person = User.query.get(delivery.delivery_person_id)
            if delivery_person:
                total_ratings = delivery_person.total_ratings
                current_avg = delivery_person.average_rating
                new_avg = ((current_avg * total_ratings) + rating) / (total_ratings + 1)
                delivery_person.average_rating = round(new_avg, 1)
                delivery_person.total_ratings += 1
                
        else:  # delivery_person
            delivery.delivery_person_rating = rating
            delivery.delivery_person_comment = comment
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Avaliação registrada com sucesso'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


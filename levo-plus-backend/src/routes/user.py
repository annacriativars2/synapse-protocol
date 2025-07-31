from flask import Blueprint, jsonify, request
from src.models.user import User, db
from datetime import datetime

user_bp = Blueprint('user', __name__)

@user_bp.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            user.last_active = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'message': 'Login realizado com sucesso'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Email ou senha incorretos'
            }), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@user_bp.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'Email já cadastrado'
            }), 400
        
        user = User(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone'),
            user_type=data['user_type'],
            preferred_payment_method=data.get('preferred_payment_method'),
            vehicle_type=data.get('vehicle_type'),
            vehicle_model=data.get('vehicle_model'),
            vehicle_plate=data.get('vehicle_plate'),
            vehicle_color=data.get('vehicle_color'),
            license_number=data.get('license_number')
        )
        
        user.set_password(data['password'])
        
        # Auto-verify clients, delivery persons need manual verification
        if data['user_type'] == 'client':
            user.is_verified = True
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': 'Usuário criado com sucesso'
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Update allowed fields
        if 'name' in data:
            user.name = data['name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'preferred_payment_method' in data:
            user.preferred_payment_method = data['preferred_payment_method']
        if 'vehicle_type' in data:
            user.vehicle_type = data['vehicle_type']
        if 'vehicle_model' in data:
            user.vehicle_model = data['vehicle_model']
        if 'vehicle_plate' in data:
            user.vehicle_plate = data['vehicle_plate']
        if 'vehicle_color' in data:
            user.vehicle_color = data['vehicle_color']
        if 'license_number' in data:
            user.license_number = data['license_number']
        if 'is_online' in data:
            user.is_online = data['is_online']
        if 'current_lat' in data:
            user.current_lat = data['current_lat']
        if 'current_lng' in data:
            user.current_lng = data['current_lng']
        
        user.last_active = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': 'Usuário atualizado com sucesso'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return '', 204

@user_bp.route('/delivery-persons/online', methods=['GET'])
def get_online_delivery_persons():
    try:
        delivery_persons = User.query.filter_by(
            user_type='delivery_person',
            is_online=True,
            is_verified=True
        ).all()
        
        return jsonify({
            'success': True,
            'delivery_persons': [dp.to_dict() for dp in delivery_persons]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


"""
Authentication routes — register, login, profile for all user roles.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from app import db
from app.models import Patient, Doctor, HospitalAdmin, SuperAdmin
from app.utils import hash_password, check_password

auth_bp = Blueprint('auth', __name__)


# Mapping of role → model
ROLE_MODELS = {
    'patient': Patient,
    'doctor': Doctor,
    'hospital_admin': HospitalAdmin,
    'super_admin': SuperAdmin,
}


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new patient account."""
    data = request.get_json() or {}
    required = ['name', 'email', 'password']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    if Patient.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    dob = data.get('date_of_birth')
    if isinstance(dob, str) and dob:
        try:
            from datetime import date
            dob = date.fromisoformat(dob)
        except Exception:
            dob = None

    patient = Patient(
        name=data['name'],
        email=data['email'],
        password_hash=hash_password(data['password']),
        phone=data.get('phone'),
        date_of_birth=dob,
        gender=data.get('gender'),
        blood_group=data.get('blood_group'),
        address=data.get('address'),
        emergency_contact=data.get('emergency_contact'),
    )
    db.session.add(patient)
    db.session.commit()


    token = create_access_token(identity={'id': patient.id, 'role': 'patient', 'email': patient.email})
    refresh = create_refresh_token(identity={'id': patient.id, 'role': 'patient', 'email': patient.email})

    return jsonify({
        'message': 'Registration successful',
        'access_token': token,
        'refresh_token': refresh,
        'user': patient.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Unified login for all roles."""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'patient')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    Model = ROLE_MODELS.get(role)
    if not Model:
        return jsonify({'error': 'Invalid role'}), 400

    user = Model.query.filter_by(email=email).first()
    if not user or not check_password(password, user.password_hash):
        return jsonify({'error': 'Invalid credentials'}), 401

    identity = {'id': user.id, 'role': role, 'email': user.email}

    # Attach hospital_id for hospital-scoped roles
    if role in ('doctor', 'hospital_admin'):
        identity['hospital_id'] = user.hospital_id

    token = create_access_token(identity=identity)
    refresh = create_refresh_token(identity=identity)

    return jsonify({
        'access_token': token,
        'refresh_token': refresh,
        'user': user.to_dict(),
        'role': role
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    identity = get_jwt_identity()
    token = create_access_token(identity=identity)
    return jsonify({'access_token': token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Get current user profile."""
    identity = get_jwt_identity()
    Model = ROLE_MODELS.get(identity['role'])
    user = Model.query.get(identity['id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict(), 'role': identity['role']}), 200

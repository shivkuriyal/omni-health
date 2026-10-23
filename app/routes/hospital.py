"""
Hospital Admin routes — manage doctors, branding, billing.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models import Hospital, Doctor, HospitalAdmin, BillingInvoice, MedicalRecord, Patient
from app.utils import role_required, hash_password

hospital_bp = Blueprint('hospital', __name__)


@hospital_bp.route('/profile', methods=['GET'])
@role_required('hospital_admin')
def get_profile():
    identity = get_jwt_identity()
    hospital = Hospital.query.get_or_404(identity['hospital_id'])
    return jsonify({'hospital': hospital.to_dict()}), 200


@hospital_bp.route('/branding', methods=['PUT'])
@role_required('hospital_admin')
def update_branding():
    identity = get_jwt_identity()
    hospital = Hospital.query.get_or_404(identity['hospital_id'])
    data = request.get_json() or {}
    for key in ('name', 'logo_url', 'accent_color', 'tagline'):
        if key in data:
            setattr(hospital, key, data[key])
    db.session.commit()
    return jsonify({'hospital': hospital.to_dict()}), 200


# ---------------------------------------------------------------------------
#  Doctor Management
# ---------------------------------------------------------------------------
@hospital_bp.route('/doctors', methods=['GET'])
@role_required('hospital_admin')
def list_doctors():
    identity = get_jwt_identity()
    doctors = Doctor.query.filter_by(hospital_id=identity['hospital_id']).all()
    return jsonify({'doctors': [d.to_dict() for d in doctors]}), 200


@hospital_bp.route('/doctors', methods=['POST'])
@role_required('hospital_admin')
def add_doctor():
    identity = get_jwt_identity()
    data = request.get_json() or {}
    required = ['name', 'email', 'password', 'specialization']
    for f in required:
        if f not in data:
            return jsonify({'error': f'Missing: {f}'}), 400

    if Doctor.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    doctor = Doctor(
        hospital_id=identity['hospital_id'],
        name=data['name'],
        email=data['email'],
        password_hash=hash_password(data['password']),
        specialization=data['specialization'],
        license_number=data.get('license_number'),
        phone=data.get('phone'),
    )
    db.session.add(doctor)
    db.session.commit()
    return jsonify({'doctor': doctor.to_dict()}), 201


@hospital_bp.route('/doctors/<doctor_id>', methods=['DELETE'])
@role_required('hospital_admin')
def remove_doctor(doctor_id):
    identity = get_jwt_identity()
    doctor = Doctor.query.filter_by(
        id=doctor_id, hospital_id=identity['hospital_id']
    ).first_or_404()
    doctor.is_active = False
    db.session.commit()
    return jsonify({'message': 'Doctor deactivated'}), 200


# ---------------------------------------------------------------------------
#  Billing
# ---------------------------------------------------------------------------
@hospital_bp.route('/billing', methods=['GET'])
@role_required('hospital_admin')
def billing_info():
    identity = get_jwt_identity()
    hospital = Hospital.query.get_or_404(identity['hospital_id'])
    invoices = BillingInvoice.query.filter_by(
        hospital_id=identity['hospital_id']
    ).order_by(BillingInvoice.created_at.desc()).all()
    return jsonify({
        'subscription': {
            'plan': hospital.plan.to_dict() if hospital.plan else None,
            'status': hospital.subscription_status,
            'start': str(hospital.subscription_start) if hospital.subscription_start else None,
            'end': str(hospital.subscription_end) if hospital.subscription_end else None,
        },
        'invoices': [i.to_dict() for i in invoices]
    }), 200


# ---------------------------------------------------------------------------
#  Hospital Analytics
# ---------------------------------------------------------------------------
@hospital_bp.route('/analytics', methods=['GET'])
@role_required('hospital_admin')
def hospital_analytics():
    identity = get_jwt_identity()
    hid = identity['hospital_id']
    return jsonify({
        'total_doctors': Doctor.query.filter_by(hospital_id=hid, is_active=True).count(),
        'total_records': MedicalRecord.query.filter_by(hospital_id=hid).count(),
    }), 200


@hospital_bp.route('/records', methods=['GET'])
@role_required('hospital_admin')
def hospital_records():
    """List recent records created at this hospital."""
    identity = get_jwt_identity()
    records = MedicalRecord.query.filter_by(
        hospital_id=identity['hospital_id']
    ).order_by(MedicalRecord.record_date.desc()).limit(50).all()
    return jsonify({'records': [r.to_dict() for r in records]}), 200


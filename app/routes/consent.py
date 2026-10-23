"""
Consent routes — request, verify OTP, QR-based consent flow.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta

from app import db
from app.models import ConsentRequest, Patient, Doctor
from app.utils import (
    role_required, generate_otp, verify_otp,
    generate_qr_token, log_audit
)

consent_bp = Blueprint('consent', __name__)


@consent_bp.route('/request', methods=['POST'])
@role_required('doctor')
def request_consent():
    """Doctor requests consent to view a patient's records."""
    identity = get_jwt_identity()
    data = request.get_json() or {}

    patient_id = data.get('patient_id')
    if not patient_id:
        # Try finding patient by email or phone
        patient = None
        if data.get('patient_email'):
            patient = Patient.query.filter_by(email=data['patient_email']).first()
        elif data.get('patient_phone'):
            patient = Patient.query.filter_by(phone=data['patient_phone']).first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        patient_id = patient.id
    else:
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404

    consent_type = data.get('consent_type', 'otp')

    consent = ConsentRequest(
        patient_id=patient_id,
        doctor_id=identity['id'],
        hospital_id=identity.get('hospital_id'),
        consent_type=consent_type,
        status='pending',
    )

    if consent_type == 'qr':
        consent.qr_token = generate_qr_token()
    else:
        otp = generate_otp(consent.id)
        # In production, send OTP via SMS/email here
        # For demo, we return it in the response
        consent.otp_hash = otp  # In production, hash this

    db.session.add(consent)
    db.session.commit()

    response = {
        'consent_id': consent.id,
        'consent_type': consent_type,
        'patient_name': patient.name,
        'status': 'pending',
    }

    if consent_type == 'qr':
        response['qr_token'] = consent.qr_token
    else:
        response['otp'] = otp  # Only for demo — remove in production

    log_audit(identity['id'], 'doctor', 'request_consent', 'consent', consent.id)

    return jsonify(response), 201


@consent_bp.route('/verify', methods=['POST'])
def verify_consent():
    """Patient verifies OTP or QR token to grant consent."""
    data = request.get_json() or {}
    consent_id = data.get('consent_id')
    consent = ConsentRequest.query.get(consent_id)

    if not consent:
        return jsonify({'error': 'Consent request not found'}), 404

    if consent.status != 'pending':
        return jsonify({'error': f'Consent already {consent.status}'}), 400

    # Verify based on type
    if consent.consent_type == 'otp':
        otp = data.get('otp')
        if not otp:
            return jsonify({'error': 'OTP required'}), 400
        # Check in-memory store or compare with hash
        if not verify_otp(consent_id, otp) and consent.otp_hash != otp:
            return jsonify({'error': 'Invalid or expired OTP'}), 401
    elif consent.consent_type == 'qr':
        qr_token = data.get('qr_token')
        if not qr_token or qr_token != consent.qr_token:
            return jsonify({'error': 'Invalid QR token'}), 401

    # Grant consent for 30 minutes
    now = datetime.now(timezone.utc)
    consent.status = 'granted'
    consent.granted_at = now
    consent.expires_at = now + timedelta(minutes=30)
    db.session.commit()

    log_audit(consent.patient_id, 'patient', 'grant_consent', 'consent', consent.id)

    return jsonify({
        'message': 'Consent granted',
        'consent_id': consent.id,
        'patient_id': consent.patient_id,
        'expires_at': str(consent.expires_at),
        'doctor': consent.doctor.to_dict() if consent.doctor else None,
    }), 200



@consent_bp.route('/active', methods=['GET'])
@jwt_required()
def active_consents():
    """List active (granted, non-expired) consents for the current user."""
    identity = get_jwt_identity()
    now = datetime.now(timezone.utc)

    if identity['role'] == 'patient':
        consents = ConsentRequest.query.filter(
            ConsentRequest.patient_id == identity['id'],
            ConsentRequest.status == 'granted',
            ConsentRequest.expires_at > now,
        ).all()
    elif identity['role'] == 'doctor':
        consents = ConsentRequest.query.filter(
            ConsentRequest.doctor_id == identity['id'],
            ConsentRequest.status == 'granted',
            ConsentRequest.expires_at > now,
        ).all()
    else:
        consents = []

    return jsonify({'consents': [c.to_dict() for c in consents]}), 200

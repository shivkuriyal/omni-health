"""
Doctor routes — view patient timelines, add records, AI summary.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, date

from app import db
from app.models import (
    Doctor, Patient, MedicalRecord, ConsentRequest,
    Allergy, MedicalDocument
)
from app.utils import role_required, log_audit

doctor_bp = Blueprint('doctor', __name__)



def _check_consent(doctor_id, patient_id):
    """Return True if the doctor has active consent for the patient."""
    consent = ConsentRequest.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id,
        status='granted'
    ).first()
    if not consent:
        return False
    if consent.expires_at and consent.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        consent.status = 'expired'
        db.session.commit()
        return False
    return True


@doctor_bp.route('/patients/<patient_id>/timeline', methods=['GET'])
@role_required('doctor')
def patient_timeline(patient_id):
    """Get chronological timeline of patient records (requires consent)."""
    identity = get_jwt_identity()

    if not _check_consent(identity['id'], patient_id):
        return jsonify({'error': 'Active consent required to view patient records'}), 403

    patient = Patient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(MedicalRecord.record_date.desc()).all()
    allergies = Allergy.query.filter_by(patient_id=patient_id).all()

    log_audit(identity['id'], 'doctor', 'view_timeline', 'patient', patient_id)

    return jsonify({
        'patient': patient.to_dict(),
        'allergies': [a.to_dict() for a in allergies],
        'timeline': [r.to_dict() for r in records],
        'total_records': len(records),
    }), 200


@doctor_bp.route('/patients/<patient_id>/records', methods=['POST'])
@role_required('doctor')
def add_record(patient_id):
    """Add a new diagnosis/prescription for a patient."""
    identity = get_jwt_identity()

    if not _check_consent(identity['id'], patient_id):
        return jsonify({'error': 'Active consent required'}), 403

    data = request.get_json() or {}
    required = ['record_type', 'title', 'record_date']
    for f in required:
        if f not in data:
            return jsonify({'error': f'Missing: {f}'}), 400

    rec_date = data.get('record_date')
    if isinstance(rec_date, str):
        try:
            rec_date = date.fromisoformat(rec_date)
        except Exception:
            rec_date = date.today()
    elif not rec_date:
        rec_date = date.today()

    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=identity['id'],
        hospital_id=identity.get('hospital_id'),
        record_type=data['record_type'],
        title=data['title'],
        description=data.get('description'),
        diagnosis=data.get('diagnosis'),
        prescription=data.get('prescription'),
        lab_results=data.get('lab_results'),
        vitals=data.get('vitals'),
        record_date=rec_date,
        severity=data.get('severity', 'low'),
    )
    db.session.add(record)
    db.session.commit()


    log_audit(identity['id'], 'doctor', 'add_record', 'medical_record', record.id)

    return jsonify({'record': record.to_dict()}), 201


@doctor_bp.route('/patients/<patient_id>/records/<record_id>', methods=['GET'])
@role_required('doctor')
def get_record(patient_id, record_id):
    """View a specific medical record."""
    identity = get_jwt_identity()
    if not _check_consent(identity['id'], patient_id):
        return jsonify({'error': 'Active consent required'}), 403

    record = MedicalRecord.query.filter_by(
        id=record_id, patient_id=patient_id
    ).first_or_404()
    return jsonify({'record': record.to_dict()}), 200


@doctor_bp.route('/patients/<patient_id>/ai-summary', methods=['POST'])
@role_required('doctor')
def ai_summary(patient_id):
    """Generate an AI clinical summary for the patient (mock)."""
    identity = get_jwt_identity()
    if not _check_consent(identity['id'], patient_id):
        return jsonify({'error': 'Active consent required'}), 403

    patient = Patient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(MedicalRecord.record_date.desc()).all()

    # Build a mock AI summary from existing records
    conditions = set()
    medications = set()
    surgeries = []
    for r in records:
        if r.record_type == 'diagnosis' and r.diagnosis:
            conditions.add(r.diagnosis[:80])
        if r.record_type == 'prescription' and r.prescription:
            medications.add(r.prescription[:80])
        if r.record_type == 'surgery':
            surgeries.append(r.title)

    summary_points = []
    if patient.blood_group:
        summary_points.append(f"Blood Group: {patient.blood_group}")
    if conditions:
        summary_points.append(f"Key conditions: {', '.join(list(conditions)[:3])}")
    if medications:
        summary_points.append(f"Current medications: {', '.join(list(medications)[:3])}")
    if surgeries:
        summary_points.append(f"Surgical history: {', '.join(surgeries[:2])}")
    summary_points.append(f"Total records on file: {len(records)}")

    summary = '\n'.join(f"• {s}" for s in summary_points[:5])

    return jsonify({
        'patient_id': patient_id,
        'summary': summary,
        'bullet_count': len(summary_points),
    }), 200


@doctor_bp.route('/profile', methods=['GET'])
@role_required('doctor')
def doctor_profile():
    """Get the logged-in doctor's profile."""
    identity = get_jwt_identity()
    doctor = Doctor.query.get_or_404(identity['id'])
    return jsonify({'doctor': doctor.to_dict()}), 200

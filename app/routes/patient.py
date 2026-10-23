"""
Patient routes — profile, records, documents, allergies, family.
"""

import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import date

from app import db
from app.models import (
    Patient, MedicalRecord, MedicalDocument,
    Allergy, FamilyGroup, ConsentRequest
)
from app.utils import role_required, hash_password, log_audit

patient_bp = Blueprint('patient', __name__)


# ---------------------------------------------------------------------------
#  Profile
# ---------------------------------------------------------------------------
@patient_bp.route('/profile', methods=['GET'])
@role_required('patient')
def get_profile():
    identity = get_jwt_identity()
    patient = Patient.query.get_or_404(identity['id'])
    return jsonify({'patient': patient.to_dict()}), 200


@patient_bp.route('/profile', methods=['PUT'])
@role_required('patient')
def update_profile():
    identity = get_jwt_identity()
    patient = Patient.query.get_or_404(identity['id'])
    data = request.get_json() or {}
    for key in ('name', 'phone', 'gender', 'blood_group',
                'address', 'emergency_contact', 'avatar_url'):
        if key in data:
            setattr(patient, key, data[key])
    if 'date_of_birth' in data and data['date_of_birth']:
        try:
            patient.date_of_birth = date.fromisoformat(data['date_of_birth'])
        except Exception:
            pass
    db.session.commit()
    return jsonify({'patient': patient.to_dict()}), 200



# ---------------------------------------------------------------------------
#  Medical Records
# ---------------------------------------------------------------------------
@patient_bp.route('/records', methods=['GET'])
@role_required('patient')
def list_records():
    identity = get_jwt_identity()
    records = MedicalRecord.query.filter_by(
        patient_id=identity['id']
    ).order_by(MedicalRecord.record_date.desc()).all()
    return jsonify({'records': [r.to_dict() for r in records]}), 200


@patient_bp.route('/records', methods=['POST'])
@role_required('patient')
def upload_record():
    """Patient uploads a historical medical record."""
    identity = get_jwt_identity()
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
        patient_id=identity['id'],
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
    return jsonify({'record': record.to_dict()}), 201


# ---------------------------------------------------------------------------
#  Documents
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@patient_bp.route('/documents', methods=['POST'])
@role_required('patient')
def upload_document():
    identity = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '' or not _allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], identity['id'])
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    doc = MedicalDocument(
        patient_id=identity['id'],
        medical_record_id=request.form.get('record_id'),
        file_name=filename,
        file_url=filepath,
        file_type=filename.rsplit('.', 1)[1].lower(),
        file_size_bytes=os.path.getsize(filepath),
    )
    db.session.add(doc)
    db.session.commit()

    return jsonify({'document': doc.to_dict()}), 201


# ---------------------------------------------------------------------------
#  Allergies
# ---------------------------------------------------------------------------
@patient_bp.route('/allergies', methods=['GET'])
@role_required('patient')
def list_allergies():
    identity = get_jwt_identity()
    allergies = Allergy.query.filter_by(patient_id=identity['id']).all()
    return jsonify({'allergies': [a.to_dict() for a in allergies]}), 200


@patient_bp.route('/allergies', methods=['POST'])
@role_required('patient')
def add_allergy():
    identity = get_jwt_identity()
    data = request.get_json() or {}
    if not data.get('allergen'):
        return jsonify({'error': 'Allergen name required'}), 400

    allergy = Allergy(
        patient_id=identity['id'],
        allergen=data['allergen'],
        severity=data.get('severity', 'moderate'),
        reaction=data.get('reaction'),
    )
    db.session.add(allergy)
    db.session.commit()
    return jsonify({'allergy': allergy.to_dict()}), 201


# ---------------------------------------------------------------------------
#  Family Group
# ---------------------------------------------------------------------------
@patient_bp.route('/family', methods=['GET'])
@role_required('patient')
def get_family():
    identity = get_jwt_identity()
    patient = Patient.query.get_or_404(identity['id'])
    if patient.family_group:
        return jsonify({'family': patient.family_group.to_dict()}), 200
    return jsonify({'family': None}), 200


@patient_bp.route('/family', methods=['POST'])
@role_required('patient')
def create_family():
    identity = get_jwt_identity()
    data = request.get_json() or {}

    group = FamilyGroup(
        primary_patient_id=identity['id'],
        group_name=data.get('group_name', 'My Family'),
    )
    db.session.add(group)
    db.session.flush()

    patient = Patient.query.get(identity['id'])
    patient.family_group_id = group.id
    db.session.commit()

    return jsonify({'family': group.to_dict()}), 201


# ---------------------------------------------------------------------------
#  Consent Management (Patient side)
# ---------------------------------------------------------------------------
@patient_bp.route('/consents', methods=['GET'])
@role_required('patient')
def list_consents():
    identity = get_jwt_identity()
    consents = ConsentRequest.query.filter_by(
        patient_id=identity['id']
    ).order_by(ConsentRequest.created_at.desc()).all()
    return jsonify({'consents': [c.to_dict() for c in consents]}), 200


@patient_bp.route('/consents/<consent_id>', methods=['DELETE'])
@role_required('patient')
def revoke_consent(consent_id):
    identity = get_jwt_identity()
    consent = ConsentRequest.query.filter_by(
        id=consent_id, patient_id=identity['id']
    ).first_or_404()
    consent.status = 'revoked'
    db.session.commit()
    log_audit(identity['id'], 'patient', 'revoke_consent', 'consent', consent_id)
    return jsonify({'message': 'Consent revoked'}), 200


@patient_bp.route('/family/members', methods=['POST'])
@role_required('patient')
def add_family_member():
    """Add a dependent to the patient's family group."""
    identity = get_jwt_identity()
    patient = Patient.query.get_or_404(identity['id'])
    data = request.get_json() or {}

    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    # Ensure family group exists
    if not patient.family_group_id:
        group = FamilyGroup(
            primary_patient_id=patient.id,
            group_name=f"{patient.name}'s Family Group"
        )
        db.session.add(group)
        db.session.flush()
        patient.family_group_id = group.id

    dummy_hash = hash_password('dependent123')
    unique_email = f"dep_{patient.id[:8]}_{int(date.today().strftime('%Y%m%d'))}_{data['name'].lower().replace(' ', '')}@omnihealth.local"

    dob = data.get('date_of_birth')
    if isinstance(dob, str) and dob:
        try:
            dob = date.fromisoformat(dob)
        except Exception:
            dob = None
    elif not isinstance(dob, date):
        dob = None

    dep = Patient(
        name=data['name'],
        email=unique_email,
        phone=data.get('phone', patient.phone),
        password_hash=dummy_hash,
        date_of_birth=dob,
        gender=data.get('gender'),
        blood_group=data.get('blood_group'),
        emergency_contact=f"{patient.name} ({patient.phone or 'Parent/Guardian'})",
        family_group_id=patient.family_group_id
    )
    db.session.add(dep)
    db.session.commit()


    return jsonify({'member': dep.to_dict(), 'message': 'Family member added'}), 201


@patient_bp.route('/allergies/<allergy_id>', methods=['DELETE'])
@role_required('patient')
def delete_allergy(allergy_id):
    identity = get_jwt_identity()
    allergy = Allergy.query.filter_by(id=allergy_id, patient_id=identity['id']).first_or_404()
    db.session.delete(allergy)
    db.session.commit()
    return jsonify({'message': 'Allergy removed'}), 200


@patient_bp.route('/records/<record_id>', methods=['DELETE'])
@role_required('patient')
def delete_record(record_id):
    identity = get_jwt_identity()
    record = MedicalRecord.query.filter_by(id=record_id, patient_id=identity['id']).first_or_404()
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'Record deleted'}), 200


@patient_bp.route('/audit-logs', methods=['GET'])
@role_required('patient')
def patient_audit_logs():
    """Get audit trail of who accessed the patient's records."""
    from app.models import AuditLog
    identity = get_jwt_identity()
    logs = AuditLog.query.filter(
        (AuditLog.user_id == identity['id']) |
        ((AuditLog.resource_type == 'patient') & (AuditLog.resource_id == identity['id'])) |
        ((AuditLog.resource_type == 'consent') & (AuditLog.user_id == identity['id']))
    ).order_by(AuditLog.created_at.desc()).limit(50).all()
    return jsonify({'audit_logs': [l.to_dict() for l in logs]}), 200


@patient_bp.route('/qr-code', methods=['GET'])
@role_required('patient')
def patient_qr():
    """Generate a high-res QR code for the patient's Universal Health ID."""
    import io, base64, qrcode
    identity = get_jwt_identity()
    patient = Patient.query.get_or_404(identity['id'])

    qr_payload = {
        'id': patient.id,
        'name': patient.name,
        'email': patient.email,
        'blood_group': patient.blood_group,
        'type': 'omnihealth_patient_id'
    }

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(f"omnihealth://patient/{patient.id}?email={patient.email}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    data_uri = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

    return jsonify({
        'qr_image': data_uri,
        'patient_id': patient.id,
        'universal_id': f"UHID-{patient.id[:8].upper()}"
    }), 200


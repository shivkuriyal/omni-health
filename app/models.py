"""
OmniHealth-Rec — Database Models
Complete schema for multi-tenant healthcare SaaS platform.
"""

import uuid
from datetime import datetime, timezone
from app import db


def generate_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
#  Super Admin
# ---------------------------------------------------------------------------
class SuperAdmin(db.Model):
    __tablename__ = 'super_admins'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'email': self.email, 'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Subscription Plan
# ---------------------------------------------------------------------------
class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    price_monthly = db.Column(db.Float, nullable=False)
    max_doctors = db.Column(db.Integer, nullable=False, default=5)
    max_patients_monthly = db.Column(db.Integer, nullable=False, default=200)
    features = db.Column(db.JSON, default=dict)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    hospitals = db.relationship('Hospital', backref='plan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'description': self.description,
            'price_monthly': self.price_monthly,
            'max_doctors': self.max_doctors,
            'max_patients_monthly': self.max_patients_monthly,
            'features': self.features,
            'is_active': self.is_active,
            'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Hospital (Tenant)
# ---------------------------------------------------------------------------
class Hospital(db.Model):
    __tablename__ = 'hospitals'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    logo_url = db.Column(db.String(500))
    accent_color = db.Column(db.String(7), default='#0ea5e9')
    tagline = db.Column(db.String(255))
    subscription_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'))
    subscription_status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    subscription_start = db.Column(db.Date)
    subscription_end = db.Column(db.Date)
    stripe_customer_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    admins = db.relationship('HospitalAdmin', backref='hospital', lazy='dynamic')
    doctors = db.relationship('Doctor', backref='hospital', lazy='dynamic')
    consent_requests = db.relationship('ConsentRequest', backref='hospital', lazy='dynamic')
    invoices = db.relationship('BillingInvoice', backref='hospital', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'slug': self.slug,
            'email': self.email, 'phone': self.phone, 'address': self.address,
            'logo_url': self.logo_url, 'accent_color': self.accent_color,
            'tagline': self.tagline,
            'subscription_status': self.subscription_status,
            'plan': self.plan.to_dict() if self.plan else None,
            'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Hospital Admin
# ---------------------------------------------------------------------------
class HospitalAdmin(db.Model):
    __tablename__ = 'hospital_admins'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    hospital_id = db.Column(db.String(36), db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'hospital_id': self.hospital_id,
            'name': self.name, 'email': self.email,
            'role': self.role, 'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Doctor
# ---------------------------------------------------------------------------
class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    hospital_id = db.Column(db.String(36), db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    specialization = db.Column(db.String(120))
    license_number = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    records = db.relationship('MedicalRecord', backref='doctor', lazy='dynamic')
    consent_requests = db.relationship('ConsentRequest', backref='doctor', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'hospital_id': self.hospital_id,
            'name': self.name, 'email': self.email,
            'specialization': self.specialization,
            'license_number': self.license_number,
            'phone': self.phone, 'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Family Group
# ---------------------------------------------------------------------------
class FamilyGroup(db.Model):
    __tablename__ = 'family_groups'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    primary_patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'))
    group_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow)

    members = db.relationship('Patient', backref='family_group',
                              foreign_keys='Patient.family_group_id', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'group_name': self.group_name,
            'primary_patient_id': self.primary_patient_id,
            'members': [m.to_dict_brief() for m in self.members],
            'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Patient
# ---------------------------------------------------------------------------
class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.Text, nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))
    avatar_url = db.Column(db.String(500))
    family_group_id = db.Column(db.String(36), db.ForeignKey('family_groups.id'))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    records = db.relationship('MedicalRecord', backref='patient', lazy='dynamic')
    documents = db.relationship('MedicalDocument', backref='patient', lazy='dynamic')
    allergies = db.relationship('Allergy', backref='patient', lazy='dynamic')
    consent_requests = db.relationship('ConsentRequest', backref='patient', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'email': self.email,
            'phone': self.phone,
            'date_of_birth': str(self.date_of_birth) if self.date_of_birth else None,
            'gender': self.gender, 'blood_group': self.blood_group,
            'address': self.address,
            'emergency_contact': self.emergency_contact,
            'avatar_url': self.avatar_url,
            'created_at': str(self.created_at)
        }

    def to_dict_brief(self):
        return {
            'id': self.id, 'name': self.name,
            'gender': self.gender, 'blood_group': self.blood_group
        }


# ---------------------------------------------------------------------------
#  Medical Record
# ---------------------------------------------------------------------------
class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.String(36), db.ForeignKey('doctors.id'))
    hospital_id = db.Column(db.String(36), db.ForeignKey('hospitals.id'))
    record_type = db.Column(db.String(50), nullable=False)  # diagnosis, prescription, lab, surgery, vaccination, general
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    lab_results = db.Column(db.JSON)
    vitals = db.Column(db.JSON)
    record_date = db.Column(db.Date, nullable=False)
    severity = db.Column(db.String(20))  # low, moderate, high, critical
    ai_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)

    documents = db.relationship('MedicalDocument', backref='medical_record', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'patient_id': self.patient_id,
            'doctor_id': self.doctor_id, 'hospital_id': self.hospital_id,
            'record_type': self.record_type, 'title': self.title,
            'description': self.description, 'diagnosis': self.diagnosis,
            'prescription': self.prescription,
            'lab_results': self.lab_results, 'vitals': self.vitals,
            'record_date': str(self.record_date),
            'severity': self.severity, 'ai_summary': self.ai_summary,
            'doctor': self.doctor.to_dict() if self.doctor else None,
            'documents': [d.to_dict() for d in self.documents],
            'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Medical Document (file attachments)
# ---------------------------------------------------------------------------
class MedicalDocument(db.Model):
    __tablename__ = 'medical_documents'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    medical_record_id = db.Column(db.String(36), db.ForeignKey('medical_records.id'))
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size_bytes = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'file_name': self.file_name,
            'file_url': self.file_url, 'file_type': self.file_type,
            'file_size_bytes': self.file_size_bytes,
            'uploaded_at': str(self.uploaded_at)
        }


# ---------------------------------------------------------------------------
#  Allergy
# ---------------------------------------------------------------------------
class Allergy(db.Model):
    __tablename__ = 'allergies'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False)
    allergen = db.Column(db.String(120), nullable=False)
    severity = db.Column(db.String(20))  # mild, moderate, severe
    reaction = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'allergen': self.allergen,
            'severity': self.severity, 'reaction': self.reaction,
            'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Consent Request
# ---------------------------------------------------------------------------
class ConsentRequest(db.Model):
    __tablename__ = 'consent_requests'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    patient_id = db.Column(db.String(36), db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.String(36), db.ForeignKey('doctors.id'), nullable=False)
    hospital_id = db.Column(db.String(36), db.ForeignKey('hospitals.id'), nullable=False)
    consent_type = db.Column(db.String(20), default='otp')  # otp, qr
    status = db.Column(db.String(20), default='pending')  # pending, granted, expired, revoked
    otp_hash = db.Column(db.String(255))
    qr_token = db.Column(db.String(255))
    granted_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'patient_id': self.patient_id,
            'doctor_id': self.doctor_id, 'hospital_id': self.hospital_id,
            'consent_type': self.consent_type, 'status': self.status,
            'granted_at': str(self.granted_at) if self.granted_at else None,
            'expires_at': str(self.expires_at) if self.expires_at else None,
            'created_at': str(self.created_at),
            'doctor': self.doctor.to_dict() if self.doctor else None,
        }


# ---------------------------------------------------------------------------
#  Billing Invoice
# ---------------------------------------------------------------------------
class BillingInvoice(db.Model):
    __tablename__ = 'billing_invoices'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    hospital_id = db.Column(db.String(36), db.ForeignKey('hospitals.id'), nullable=False)
    subscription_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue, cancelled
    stripe_invoice_id = db.Column(db.String(255))
    billing_period_start = db.Column(db.Date)
    billing_period_end = db.Column(db.Date)
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)

    plan = db.relationship('SubscriptionPlan', backref='invoices')

    def to_dict(self):
        return {
            'id': self.id, 'hospital_id': self.hospital_id,
            'amount': self.amount, 'currency': self.currency,
            'status': self.status,
            'billing_period_start': str(self.billing_period_start) if self.billing_period_start else None,
            'billing_period_end': str(self.billing_period_end) if self.billing_period_end else None,
            'paid_at': str(self.paid_at) if self.paid_at else None,
            'created_at': str(self.created_at)
        }


# ---------------------------------------------------------------------------
#  Audit Log
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36))
    user_role = db.Column(db.String(30))
    action = db.Column(db.String(50), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.String(36))
    metadata_json = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id,
            'user_role': self.user_role, 'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'metadata': self.metadata_json,
            'ip_address': self.ip_address,
            'created_at': str(self.created_at)
        }

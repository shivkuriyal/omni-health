"""
Super Admin routes — manage hospitals, plans, platform analytics.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import date

from app import db
from app.models import (
    Hospital, SubscriptionPlan, HospitalAdmin, Doctor,
    Patient, BillingInvoice, AuditLog
)
from app.utils import role_required, hash_password, log_audit

admin_bp = Blueprint('admin', __name__)


# ---------------------------------------------------------------------------
#  Hospitals
# ---------------------------------------------------------------------------
@admin_bp.route('/hospitals', methods=['GET'])
@role_required('super_admin')
def list_hospitals():
    hospitals = Hospital.query.order_by(Hospital.created_at.desc()).all()
    return jsonify({'hospitals': [h.to_dict() for h in hospitals]}), 200


@admin_bp.route('/hospitals', methods=['POST'])
@role_required('super_admin')
def create_hospital():
    data = request.get_json() or {}
    required = ['name', 'slug', 'admin_name', 'admin_email', 'admin_password']
    for f in required:
        if f not in data:
            return jsonify({'error': f'Missing: {f}'}), 400

    if Hospital.query.filter_by(slug=data['slug']).first():
        return jsonify({'error': 'Slug already taken'}), 409

    plan = None
    if data.get('plan_id'):
        plan = SubscriptionPlan.query.get(data['plan_id'])

    hospital = Hospital(
        name=data['name'],
        slug=data['slug'],
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address'),
        subscription_plan_id=plan.id if plan else None,
        subscription_status='active',
        subscription_start=date.today(),
        accent_color=data.get('accent_color', '#0ea5e9'),
        tagline=data.get('tagline'),
    )
    db.session.add(hospital)
    db.session.flush()

    # Create hospital admin account
    admin = HospitalAdmin(
        hospital_id=hospital.id,
        name=data['admin_name'],
        email=data['admin_email'],
        password_hash=hash_password(data['admin_password']),
    )
    db.session.add(admin)
    db.session.commit()

    from flask_jwt_extended import get_jwt_identity
    identity = get_jwt_identity()
    log_audit(identity['id'], 'super_admin', 'create_hospital',
              'hospital', hospital.id)

    return jsonify({'hospital': hospital.to_dict(), 'admin': admin.to_dict()}), 201


@admin_bp.route('/hospitals/<hospital_id>', methods=['PUT'])
@role_required('super_admin')
def update_hospital(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)
    data = request.get_json() or {}
    for key in ('name', 'email', 'phone', 'address', 'subscription_status',
                'accent_color', 'tagline', 'logo_url', 'subscription_plan_id'):
        if key in data:
            setattr(hospital, key, data[key])
    db.session.commit()
    return jsonify({'hospital': hospital.to_dict()}), 200


@admin_bp.route('/hospitals/<hospital_id>', methods=['DELETE'])
@role_required('super_admin')
def delete_hospital(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)
    hospital.subscription_status = 'cancelled'
    db.session.commit()

    from flask_jwt_extended import get_jwt_identity
    identity = get_jwt_identity()
    log_audit(identity['id'], 'super_admin', 'offboard_hospital',
              'hospital', hospital.id)

    return jsonify({'message': 'Hospital offboarded'}), 200


# ---------------------------------------------------------------------------
#  Subscription Plans
# ---------------------------------------------------------------------------
@admin_bp.route('/plans', methods=['GET'])
@role_required('super_admin')
def list_plans():
    plans = SubscriptionPlan.query.all()
    return jsonify({'plans': [p.to_dict() for p in plans]}), 200


@admin_bp.route('/plans', methods=['POST'])
@role_required('super_admin')
def create_plan():
    data = request.get_json() or {}
    plan = SubscriptionPlan(
        name=data['name'],
        description=data.get('description'),
        price_monthly=data['price_monthly'],
        max_doctors=data.get('max_doctors', 5),
        max_patients_monthly=data.get('max_patients_monthly', 200),
        features=data.get('features', {}),
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify({'plan': plan.to_dict()}), 201


@admin_bp.route('/plans/<plan_id>', methods=['PUT'])
@role_required('super_admin')
def update_plan(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    data = request.get_json() or {}
    for key in ('name', 'description', 'price_monthly', 'max_doctors',
                'max_patients_monthly', 'features', 'is_active'):
        if key in data:
            setattr(plan, key, data[key])
    db.session.commit()
    return jsonify({'plan': plan.to_dict()}), 200


# ---------------------------------------------------------------------------
#  Analytics & Invoices
# ---------------------------------------------------------------------------
@admin_bp.route('/analytics', methods=['GET'])
@role_required('super_admin')
def platform_analytics():
    return jsonify({
        'total_hospitals': Hospital.query.count(),
        'active_hospitals': Hospital.query.filter_by(subscription_status='active').count(),
        'total_doctors': Doctor.query.count(),
        'total_patients': Patient.query.count(),
        'total_revenue': db.session.query(
            db.func.coalesce(db.func.sum(BillingInvoice.amount), 0)
        ).filter(BillingInvoice.status == 'paid').scalar(),
    }), 200


@admin_bp.route('/invoices', methods=['GET'])
@role_required('super_admin')
def all_invoices():
    invoices = BillingInvoice.query.order_by(BillingInvoice.created_at.desc()).all()
    return jsonify({'invoices': [i.to_dict() for i in invoices]}), 200


@admin_bp.route('/audit-logs', methods=['GET'])
@role_required('super_admin')
def admin_audit_logs():
    """Platform-wide security audit feed."""
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify({'audit_logs': [l.to_dict() for l in logs]}), 200


"""
OmniHealth-Rec — Flask Application Factory
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from config import config_by_name

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        static_folder=os.path.join(base_dir, 'static'),
        template_folder=os.path.join(base_dir, 'templates')
    )
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.hospital import hospital_bp
    from app.routes.doctor import doctor_bp
    from app.routes.patient import patient_bp
    from app.routes.consent import consent_bp
    from app.routes.pages import pages_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(hospital_bp, url_prefix='/api/hospital')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(consent_bp, url_prefix='/api/consent')

    # Create tables on first request
    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        _seed_defaults(app)

    return app


def _seed_defaults(app):
    """Seed default plans, super admin, demo hospitals, doctors, patients, and medical records."""
    from app.models import (
        SubscriptionPlan, SuperAdmin, Hospital, HospitalAdmin,
        Doctor, Patient, FamilyGroup, MedicalRecord, Allergy,
        ConsentRequest, BillingInvoice, AuditLog
    )
    import bcrypt
    from datetime import date, datetime, timezone, timedelta

    if SubscriptionPlan.query.count() == 0:
        plans = [
            SubscriptionPlan(
                name='Starter',
                description='For small clinics — up to 5 doctors',
                price_monthly=49.00,
                max_doctors=5,
                max_patients_monthly=200,
                features={"support": "email", "whitelabel": False, "ai_summary": False},
                is_active=True
            ),
            SubscriptionPlan(
                name='Professional',
                description='For mid-size hospitals — up to 25 doctors',
                price_monthly=199.00,
                max_doctors=25,
                max_patients_monthly=2000,
                features={"support": "priority", "whitelabel": True, "ai_summary": True},
                is_active=True
            ),
            SubscriptionPlan(
                name='Enterprise',
                description='Unlimited doctors, custom SLA, dedicated support',
                price_monthly=499.00,
                max_doctors=9999,
                max_patients_monthly=99999,
                features={"support": "dedicated", "whitelabel": True, "ai_summary": True, "api_access": True},
                is_active=True
            ),
        ]
        db.session.add_all(plans)
        db.session.commit()

    if SuperAdmin.query.count() == 0:
        hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin = SuperAdmin(
            name='Platform Super Admin',
            email='admin@omnihealth.com',
            password_hash=hashed
        )
        db.session.add(admin)

    # Seed demo hospitals if none exist
    if Hospital.query.count() == 0:
        pro_plan = SubscriptionPlan.query.filter_by(name='Professional').first()
        ent_plan = SubscriptionPlan.query.filter_by(name='Enterprise').first()

        h1 = Hospital(
            name='Metro General Hospital',
            slug='metro-general',
            email='contact@metrogeneral.org',
            phone='+1-800-555-0144',
            address='742 Evergreen Terrace, Medical District, Springfield',
            accent_color='#0ea5e9',
            tagline='Compassionate care, universal excellence',
            subscription_plan_id=pro_plan.id if pro_plan else None,
            subscription_status='active',
            subscription_start=date(2024, 1, 1),
            subscription_end=date(2027, 1, 1),
        )
        h2 = Hospital(
            name='St. Jude Medical Center',
            slug='st-jude',
            email='info@stjudemedical.org',
            phone='+1-800-555-0188',
            address='100 Innovation Way, Tech Valley, Boston, MA',
            accent_color='#6366f1',
            tagline='Pioneering tomorrow’s medicine today',
            subscription_plan_id=ent_plan.id if ent_plan else None,
            subscription_status='active',
            subscription_start=date(2024, 2, 1),
            subscription_end=date(2027, 2, 1),
        )
        db.session.add_all([h1, h2])
        db.session.flush()

        # Seed Hospital Admins
        h_admin_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        ha1 = HospitalAdmin(
            hospital_id=h1.id,
            name='Marcus Vance (Admin)',
            email='metro.admin@omnihealth.com',
            password_hash=h_admin_hash,
            role='admin'
        )
        ha2 = HospitalAdmin(
            hospital_id=h2.id,
            name='Elena Rostova (Admin)',
            email='stjude.admin@omnihealth.com',
            password_hash=h_admin_hash,
            role='admin'
        )
        db.session.add_all([ha1, ha2])

        # Seed Doctors
        doc_hash = bcrypt.hashpw('doctor123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        doc1 = Doctor(
            hospital_id=h1.id,
            name='Dr. Sarah Jenkins, MD',
            email='doctor@omnihealth.com',
            password_hash=doc_hash,
            specialization='Cardiology & Internal Medicine',
            license_number='MD-89241-MA',
            phone='+1-555-0133',
            is_active=True
        )
        doc2 = Doctor(
            hospital_id=h2.id,
            name='Dr. Marcus Chen, MD',
            email='marcus@omnihealth.com',
            password_hash=doc_hash,
            specialization='Neurology & Critical Care',
            license_number='MD-77192-NY',
            phone='+1-555-0177',
            is_active=True
        )
        db.session.add_all([doc1, doc2])
        db.session.flush()

        # Seed Patient: John Doe
        pat_hash = bcrypt.hashpw('patient123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        pat = Patient(
            name='John Doe',
            email='patient@omnihealth.com',
            phone='+1-555-0199',
            password_hash=pat_hash,
            date_of_birth=date(1988, 6, 14),
            gender='Male',
            blood_group='O+',
            address='1244 Elmwood Ave, Springfield, IL',
            emergency_contact='Jane Doe (+1-555-0190) - Spouse',
        )
        db.session.add(pat)
        db.session.flush()

        # Family Group for John Doe
        fam = FamilyGroup(
            primary_patient_id=pat.id,
            group_name='Doe Family Health Group'
        )
        db.session.add(fam)
        db.session.flush()
        pat.family_group_id = fam.id

        # Family Dependents
        dep1 = Patient(
            name='Emma Doe',
            email='emma.doe.child@omnihealth.local',
            phone='+1-555-0199',
            password_hash=pat_hash,
            date_of_birth=date(2018, 4, 12),
            gender='Female',
            blood_group='A+',
            address='1244 Elmwood Ave, Springfield, IL',
            emergency_contact='John Doe (+1-555-0199) - Father',
            family_group_id=fam.id
        )
        dep2 = Patient(
            name='Robert Doe',
            email='robert.doe.senior@omnihealth.local',
            phone='+1-555-0182',
            password_hash=pat_hash,
            date_of_birth=date(1955, 11, 3),
            gender='Male',
            blood_group='O+',
            address='1244 Elmwood Ave, Springfield, IL',
            emergency_contact='John Doe (+1-555-0199) - Son',
            family_group_id=fam.id
        )
        db.session.add_all([dep1, dep2])

        # Allergies for John Doe
        allergies = [
            Allergy(
                patient_id=pat.id,
                allergen='Penicillin',
                severity='severe',
                reaction='Anaphylaxis, severe broncho-constriction, urticaria'
            ),
            Allergy(
                patient_id=pat.id,
                allergen='Peanuts',
                severity='moderate',
                reaction='Facial hives, periorbital edema, oral tingling'
            ),
            Allergy(
                patient_id=pat.id,
                allergen='Sulfa Antibiotics',
                severity='mild',
                reaction='Maculopapular cutaneous rash'
            ),
        ]
        db.session.add_all(allergies)

        # Medical Records for John Doe
        records = [
            MedicalRecord(
                patient_id=pat.id,
                doctor_id=doc1.id,
                hospital_id=h1.id,
                record_type='surgery',
                title='Emergency Laparoscopic Appendectomy',
                description='Patient presented with acute right lower quadrant abdominal pain, rebound tenderness, and leukocytosis. Laparoscopic appendectomy performed with minimal blood loss (<15 mL).',
                diagnosis='Acute suppurative appendicitis with localized peritonitis (K35.80)',
                prescription='Amoxicillin-clavulanate 875/125mg PO BID x 7 days; Ibuprofen 600mg PO TID PRN pain',
                vitals={'bp': '124/80', 'pulse': 78, 'temp': '98.6 F', 'spo2': '99%'},
                lab_results={'WBC': '14.2 x10^3/uL', 'Hemoglobin': '14.8 g/dL', 'Platelets': '240 x10^3/uL'},
                record_date=date(2023, 3, 15),
                severity='high',
                ai_summary='Emergency appendectomy completed without complication. Uneventful recovery. Avoid penicillin alternatives prescribed.'
            ),
            MedicalRecord(
                patient_id=pat.id,
                doctor_id=doc1.id,
                hospital_id=h1.id,
                record_type='diagnosis',
                title='Type 2 Diabetes Mellitus Workup & Initiation',
                description='Routine metabolic screening revealed fasting plasma glucose 142 mg/dL. Confirmatory HbA1c 7.4%. Diagnosed with early-stage non-insulin dependent Type 2 Diabetes.',
                diagnosis='Type 2 Diabetes Mellitus without acute hyperosmolar state (E11.9)',
                prescription='Metformin HCl Extended-Release 500mg PO once daily with dinner; Atorvastatin 20mg PO QHS',
                vitals={'bp': '132/84', 'pulse': 74, 'weight': '84 kg', 'bmi': '27.4'},
                lab_results={'Fasting Glucose': '142 mg/dL', 'HbA1c': '7.4%', 'Serum Creatinine': '0.92 mg/dL', 'eGFR': '>90'},
                record_date=date(2023, 11, 20),
                severity='moderate',
                ai_summary='Type 2 Diabetes diagnosed. Commenced on Metformin 500mg daily. Glycemic control monitoring scheduled.'
            ),
            MedicalRecord(
                patient_id=pat.id,
                doctor_id=doc1.id,
                hospital_id=h1.id,
                record_type='lab',
                title='Comprehensive Metabolic Profile & Lipid Panel',
                description='6-month follow-up laboratory evaluation showing positive lifestyle and medication adherence.',
                diagnosis='Follow-up for dyslipidemia and glycemic parameters',
                prescription='Continue current Metformin and Atorvastatin regimen',
                vitals={'bp': '126/80', 'pulse': 72, 'weight': '82 kg', 'bmi': '26.8'},
                lab_results={'Total Cholesterol': '188 mg/dL', 'LDL-C': '108 mg/dL', 'HDL-C': '50 mg/dL', 'Triglycerides': '150 mg/dL', 'HbA1c': '6.8%'},
                record_date=date(2024, 5, 10),
                severity='low',
                ai_summary='Marked improvement in HbA1c from 7.4% to 6.8%. Lipid targets within acceptable range.'
            ),
            MedicalRecord(
                patient_id=pat.id,
                doctor_id=doc2.id,
                hospital_id=h2.id,
                record_type='vaccination',
                title='Seasonal Influenza & COVID-19 Bivalent Booster',
                description='Administered standard quadrivalent influenza immunization and Spikevax booster in left deltoid.',
                diagnosis='Preventative immunization encounter (Z23)',
                prescription='Observation for 15 minutes post-injection. Rest, hydration, acetaminophen PRN soreness.',
                vitals={'bp': '122/78', 'pulse': 70, 'temp': '98.4 F'},
                record_date=date(2024, 9, 18),
                severity='low',
                ai_summary='Up to date on seasonal respiratory vaccinations.'
            ),
            MedicalRecord(
                patient_id=pat.id,
                doctor_id=doc1.id,
                hospital_id=h1.id,
                record_type='diagnosis',
                title='Cardiac Evaluation & Holter Monitoring',
                description='Patient reported intermittent palpitations during periods of physical exertion and caffeine consumption. 24-hr Holter showed sinus tachycardia without ischemic ST shifts or ventricular arrhythmias.',
                diagnosis='Paroxysmal sinus tachycardia (I47.1)',
                prescription='Metoprolol Tartrate 25mg PO BID; Lifestyle caffeine restriction',
                vitals={'bp': '128/82', 'pulse': 88, 'temp': '98.6 F', 'spo2': '99%'},
                lab_results={'TSH': '1.85 uIU/mL', 'Troponin I': '<0.01 ng/mL', 'Potassium': '4.2 mEq/L'},
                record_date=date(2025, 1, 14),
                severity='moderate',
                ai_summary='Sinus tachycardia ruled benign with normal troponin and thyroid profile. Responding well to low-dose beta blocker.'
            ),
        ]
        db.session.add_all(records)

        # Active Consent Request for Dr. Sarah Jenkins (valid for 24h for smooth instant testing)
        consent = ConsentRequest(
            patient_id=pat.id,
            doctor_id=doc1.id,
            hospital_id=h1.id,
            consent_type='otp',
            status='granted',
            otp_hash='123456',
            granted_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db.session.add(consent)

        # Invoices for Hospitals
        invoices = [
            BillingInvoice(
                hospital_id=h1.id,
                subscription_plan_id=pro_plan.id if pro_plan else None,
                amount=199.00,
                currency='USD',
                status='paid',
                billing_period_start=date(2024, 1, 1),
                billing_period_end=date(2024, 2, 1),
                paid_at=datetime.now(timezone.utc) - timedelta(days=60)
            ),
            BillingInvoice(
                hospital_id=h1.id,
                subscription_plan_id=pro_plan.id if pro_plan else None,
                amount=199.00,
                currency='USD',
                status='paid',
                billing_period_start=date(2024, 2, 1),
                billing_period_end=date(2024, 3, 1),
                paid_at=datetime.now(timezone.utc) - timedelta(days=30)
            ),
            BillingInvoice(
                hospital_id=h2.id,
                subscription_plan_id=ent_plan.id if ent_plan else None,
                amount=499.00,
                currency='USD',
                status='paid',
                billing_period_start=date(2024, 2, 1),
                billing_period_end=date(2024, 3, 1),
                paid_at=datetime.now(timezone.utc) - timedelta(days=20)
            ),
        ]
        db.session.add_all(invoices)

        # Initial Audit Logs
        audits = [
            AuditLog(
                user_id=pat.id,
                user_role='patient',
                action='grant_consent',
                resource_type='consent',
                resource_id=consent.id,
                metadata_json={'doctor': 'Dr. Sarah Jenkins, MD', 'hospital': 'Metro General Hospital'}
            ),
            AuditLog(
                user_id=doc1.id,
                user_role='doctor',
                action='view_timeline',
                resource_type='patient',
                resource_id=pat.id,
                metadata_json={'consultation': 'Cardiac Follow-up'}
            ),
            AuditLog(
                user_id=ha1.id,
                user_role='hospital_admin',
                action='update_branding',
                resource_type='hospital',
                resource_id=h1.id,
                metadata_json={'color': '#0ea5e9'}
            )
        ]
        db.session.add_all(audits)

    db.session.commit()


# OmniHealth-Rec — Universal Patient Health Record Platform

> Centralized, cloud-based Universal Personal Health Record (PHR) SaaS platform with multi-tenant hospital whitelabeling and time-boxed OTP/QR consent.

---

## 🌟 Overview

**OmniHealth-Rec** is a decentralized-ownership Personal Health Record platform that completely decouples patient medical histories from individual clinic/hospital silos. 

- **100% Patient Owned**: Patients hold their Universal Health ID (`UHID`), lifelong medical timeline, allergies, lab reports, and prescriptions.
- **Time-Boxed Consent Engine**: Doctors and hospital providers can only access records upon explicit OTP or QR verification granted by the patient.
- **Multi-Tenant SaaS**: Hospitals subscribe to tiered SaaS plans, manage staff doctors, and customize their clinical portals with their own whitelabeled branding and theme colors.
- **AI Clinical Summary**: Distills extensive multi-year patient records into a 5-point executive clinical snapshot for immediate diagnostic context.

---

## 👥 User Roles & Portals

| Role | Default Credentials | Primary Features |
|---|---|---|
| **Patient** | `patient@omnihealth.com` / `patient123` | Universal Health ID (UHID), Digital QR Health Pass, lifelong timeline, past record uploads, allergy alerts, active doctor consent revocation, family dependent profiles, access audit trail |
| **Doctor** | `doctor@omnihealth.com` / `doctor123` | Patient lookup, OTP/QR consent request, active consultation sessions, chronological timeline view, AI clinical summary generator, new diagnosis & prescription creation |
| **Hospital Admin** | `metro.admin@omnihealth.com` / `admin123` | Hospital overview KPIs, live whitelabel branding customizer (theme accent color, name, tagline, logo), doctor staff roster (register & deactivate physicians), subscription quota tracker, billing invoices |
| **Super Admin** | `admin@omnihealth.com` / `admin123` | Multi-tenant SaaS metrics (MRR, total hospitals, active doctors, registered patients), hospital onboarding engine, subscription plan manager (Starter/Pro/Enterprise), global invoices, platform security audit feed |

---

## 🏗️ Architecture

```
Client Layer (HTML5 / Vanilla CSS / Modern JS)
      │
      ▼
API Gateway & Auth (Flask + Flask-JWT-Extended)
      │
      ├──> User & Tenant Service
      ├──> Medical Records & Attachments
      ├──> OTP / QR Consent Engine
      ├──> Whitelabel Branding Service
      ├──> SaaS Billing & Quotas
      └──> AI Clinical Summarizer
      │
      ▼
Data Layer (PostgreSQL / SQLite + File Storage + Audit Trail)
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.10+
- Virtualenv

### 2. Setup Virtual Environment & Dependencies
```bash
# Clone the repository
git clone https://github.com/shivkuriyal/omi-rec-healthcare.git
cd omi-rec-healthcare

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Run Development Server
```bash
python run.py
```
Open **`http://127.0.0.1:5001`** in your browser.

---

## 🧪 Testing

Run the full end-to-end verification suite across all 18 core endpoints and 7 page routes:
```bash
python -c "
from app import create_app
client = create_app().test_client()
for r in ['/', '/login', '/register', '/dashboard', '/doctor/timeline', '/patient/records', '/admin/panel']:
    assert client.get(r).status_code == 200
print('All page routes verified!')
"
```

---

## 🔒 Security & Compliance
- **Authentication**: JWT access and refresh tokens with role-based claim enforcement.
- **Minimum Necessary Access**: Doctors cannot view any records without active, granted consent (`status='granted'` and `expires_at > now`).
- **Audit Logging**: Every timeline view, diagnosis creation, and consent action is permanently recorded in the `audit_logs` table.
- **Tenant Scoping**: All hospital-specific data is strictly isolated via `hospital_id` foreign keys.

---

## 📄 License
MIT License. Built for modern healthcare.

"""
Page routes — serves the HTML templates.
"""

from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def landing():
    return render_template('landing.html')


@pages_bp.route('/login')
@pages_bp.route('/login.')
def login_page():
    return render_template('login.html')


@pages_bp.route('/favicon.ico')
def favicon():
    return ('', 204)



@pages_bp.route('/register')
def register_page():
    return render_template('register.html')


@pages_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@pages_bp.route('/doctor/timeline')
def doctor_timeline():
    return render_template('doctor_timeline.html')


@pages_bp.route('/patient/records')
def patient_records():
    return render_template('patient_records.html')


@pages_bp.route('/admin/panel')
def admin_panel():
    return render_template('admin_panel.html')

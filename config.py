import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

IS_VERCEL = bool(os.environ.get('VERCEL'))
DATA_DIR = '/tmp' if IS_VERCEL else BASE_DIR

def _get_database_uri():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    if IS_VERCEL:
        return 'sqlite:////tmp/omnihealth.db'
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'omnihealth.db')}"

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod-omnihealth-32-bytes')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret-omnihealth-platform-key-32-bytes')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    JWT_VERIFY_SUB = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(DATA_DIR, 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _get_database_uri()


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _get_database_uri()


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

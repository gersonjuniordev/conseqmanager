import os
from datetime import timedelta

class Config:
    # Configurações base
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-muito-secreta'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
    
    # Configurações de pasta
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, 'uploads')
    COMPANY_UPLOADS = os.path.join(UPLOAD_FOLDER, 'companies')
    ADMIN_UPLOADS = os.path.join(UPLOAD_FOLDER, 'admin')
    
    # Configurações de upload
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Banco de dados
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Se o DATABASE_URL começar com postgres://, substituir por postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    
    # Adicionar configuração para fotos de perfil
    PROFILE_UPLOADS = os.path.join(UPLOAD_FOLDER, 'profiles')
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
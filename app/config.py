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
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'app.db')
    
    # Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    
    # Adicionar configuração para fotos de perfil
    PROFILE_UPLOADS = os.path.join(UPLOAD_FOLDER, 'profiles')
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    @staticmethod
    def init_app(app):
        # Criar diretórios necessários
        directories = [
            app.instance_path,
            app.config['UPLOAD_FOLDER'],
            app.config['COMPANY_UPLOADS'],
            app.config['ADMIN_UPLOADS'],
            app.config['PROFILE_UPLOADS']
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, mode=0o755, exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
class ProductionConfig(Config):
    # Usar variáveis de ambiente em produção
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Configurar logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        file_handler = RotatingFileHandler(
            'logs/conseqmanager.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('ConseqManager startup')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

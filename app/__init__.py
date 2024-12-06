from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, 
                template_folder='../templates', 
                static_folder='../static')
    
    app.config.from_object(Config)
    
    # Garantir que as pastas existam
    @app.before_first_request
    def create_upload_folders():
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['COMPANY_UPLOADS'], exist_ok=True)
        os.makedirs(app.config['ADMIN_UPLOADS'], exist_ok=True)
        os.makedirs(app.config['PROFILE_UPLOADS'], exist_ok=True)
    
    db.init_app(app)
    
    from app.routes import main
    app.register_blueprint(main)
    
    from app.admin_routes import admin
    app.register_blueprint(admin)
    
    from app.cli import create_user_command
    app.cli.add_command(create_user_command)
    
    return app

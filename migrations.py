from app import create_app, db
from app.models import User, Company, CompanyUser, Document

def upgrade_database():
    app = create_app()
    
    with app.app_context():
        # Remover todas as tabelas existentes
        db.drop_all()
        
        # Recriar todas as tabelas
        db.create_all()
        
        print("Banco de dados recriado com sucesso!")

if __name__ == '__main__':
    upgrade_database()
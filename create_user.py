from app import create_app, db
from app.models import User

def create_initial_user():
    app = create_app()
    
    with app.app_context():
        # Verificar se o usuário já existe
        existing_user = User.query.filter_by(username='admin').first()
        if existing_user:
            print("Usuário 'admin' já existe!")
            return
            
        # Criar novo usuário
        user = User(username='admin', is_admin=True)
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        print("Usuário inicial criado com sucesso!")

if __name__ == '__main__':
    create_initial_user() 
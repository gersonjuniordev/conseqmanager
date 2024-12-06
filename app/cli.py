import click
from flask.cli import with_appcontext
from app import db
from app.models import User

@click.command('create-user')
@click.argument('username')
@click.argument('password')
@with_appcontext
def create_user_command(username, password):
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Usuário {username} criado com sucesso!') 
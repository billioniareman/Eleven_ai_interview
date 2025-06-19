from flask import Flask
from .models import db
from .routes import bp as invite_bp


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///invite_send.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'invite_supersourcing_2025'
    db.init_app(app)
    app.register_blueprint(invite_bp)
    return app

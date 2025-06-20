from flask import Flask
from .models import invite_collection
from .routes import bp as invite_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = 'invite_supersourcing_2025'
    app.register_blueprint(invite_bp)
    return app

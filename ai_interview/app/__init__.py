# app/__init__.py
# ...existing code...
from flask import Flask
from flask_socketio import SocketIO
from config import Config

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    socketio.init_app(app)
    
    from app.routes import main
    app.register_blueprint(main)
    
    return app

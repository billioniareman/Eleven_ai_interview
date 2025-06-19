from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=False, host='0.0.0.0', port=8000, use_reloader=False)
import subprocess
import sys
from invite_send import create_app
from invite_send.models import db

app = create_app()

if __name__ == '__main__':
    # Start ai_interview/run.py as a subprocess
    ai_interview_process = subprocess.Popen([sys.executable, 'ai_interview/run.py'])
    try:
        with app.app_context():
            db.create_all()
        app.run(host='0.0.0.0', debug=True)
    finally:
        ai_interview_process.terminate()

import subprocess
import sys
from invite_send import create_app

app = create_app()

if __name__ == '__main__':
    # Start ai_interview/run.py as a subprocess
    ai_interview_process = subprocess.Popen([sys.executable, 'ai_interview/run.py'])
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    finally:
        ai_interview_process.terminate()

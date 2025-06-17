from flask import Blueprint, render_template, request, jsonify, current_app, abort
from app.interview_agent import InterviewAgent
from flask_socketio import emit
from app import socketio
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

main = Blueprint('main', __name__)
interview_agent = None

# Connect to invite_send DB for token validation
INVITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../instance/invite_send.db'))
engine = create_engine(f'sqlite:///{INVITE_DB_PATH}')
Session = sessionmaker(bind=engine)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/interview/<token>')
def interview(token):
    # Validate token from invite_send
    session = Session()
    result = session.execute(text("SELECT * FROM invite WHERE token = :token"), {'token': token}).fetchone()
    if not result:
        abort(404, 'Invalid or expired interview link.')
    
    expires_at = result[5]  # expires_at is at index 5
    is_used = result[6]     # is_used is at index 6
    form_data = result[3]   # form_data is at index 3
    
    if is_used or datetime.utcnow() > datetime.fromisoformat(expires_at):
        abort(403, 'Interview link expired or already used.')
    
    # Get candidate info - parse JSON string if it exists
    candidate_info = json.loads(form_data) if form_data else {}
    # Use parsed resume data if available
    resume_data = candidate_info.get('parsed_resume', candidate_info)
    
    # Start interview session (context)
    global interview_agent
    interview_agent = InterviewAgent()
    interview_context = interview_agent.create_context(resume_data)
    interview_agent.start_session(interview_context)
    return render_template('interview.html', candidate=candidate_info)

def _process_interview_completion(interview_data):
    """
    Internal function to handle interview completion tasks
    - Stores evaluation
    - Updates invite system database
    - Sends notifications if needed
    - Archives interview data
    """
    try:
        # Get conversation ID and token for reference
        conversation_id = interview_data.get('conversation_id')
        token = interview_data.get('token')
        
        # Store interview data and evaluation
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"interview_records/{conversation_id}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(interview_data, f, indent=2)
            
        # Update invite system database with interview results
        session = Session()
        try:
            # Update the invite record with interview results and mark as used
            session.execute(
                text("""
                    UPDATE invite 
                    SET interview_completed = 1,
                        interview_results = :results,
                        completed_at = :completed_at,
                        is_used = 1
                    WHERE token = :token
                """),
                {
                    'token': token,
                    'results': json.dumps(interview_data),
                    'completed_at': datetime.utcnow().isoformat()
                }
            )
            session.commit()
        except Exception as db_error:
            current_app.logger.error(f"Database update error: {str(db_error)}")
        finally:
            session.close()
            
        # Could add notification logic here
        # For example, notify HR system or send email to recruiter
        
        current_app.logger.info(f"Interview {conversation_id} completed and processed")
        
    except Exception as e:
        current_app.logger.error(f"Error processing interview completion: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection and process interview completion"""
    global interview_agent
    if interview_agent:
        try:
            # End session and get complete interview data with evaluation
            interview_data = interview_agent.end_session()
            
            # Process interview completion in the backend
            _process_interview_completion(interview_data)
            
            # Clear the interview agent
            interview_agent = None
            
            emit('interview_ended', {
                'status': 'completed',
                'message': 'Thank you for completing the interview'
            })
            
        except Exception as e:
            current_app.logger.error(f"Error during interview completion: {str(e)}")
            emit('interview_ended', {
                'status': 'error',
                'message': 'Interview ended with errors'
            })

@socketio.on('pause_interview')
def handle_pause():
    """Handle interview pause"""
    global interview_agent
    if interview_agent and interview_agent.conversation:
        interview_agent.conversation.pause_session()
        emit('interview_paused', {'status': 'paused'})

@socketio.on('resume_interview')
def handle_resume():
    """Handle interview resume"""
    global interview_agent
    if interview_agent and interview_agent.conversation:
        interview_agent.conversation.resume_session()
        emit('interview_resumed', {'status': 'resumed'})

@main.route('/save_code', methods=['POST'])
def save_code():
    data = request.get_json()
    code = data.get('code', '')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'saved_code_{timestamp}.txt'
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        return jsonify({'status': 'success', 'message': f'Code saved as {filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

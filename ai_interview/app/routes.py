from flask import Blueprint, render_template, request, jsonify, current_app
from app.interview_agent import InterviewAgent
from app.resume_parser import ResumeParser
from flask_socketio import emit
from app import socketio
import json
from datetime import datetime

main = Blueprint('main', __name__)
interview_agent = None

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/interview')
def interview():
    return render_template('interview.html')

@main.route('/upload_resume', methods=['POST'])
def upload_resume():
    global interview_agent
    
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file uploaded'}), 400
    
    resume_file = request.files['resume']
    if resume_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Initialize parser and agent
        resume_parser = ResumeParser()
        interview_agent = InterviewAgent()
        
        # Parse resume
        resume_data = resume_parser.parse(resume_file)
        
        # Initialize interview context
        interview_context = interview_agent.create_context(resume_data)
        
        # Start the interview session
        success = interview_agent.start_session(interview_context)
        
        if not success:
            return jsonify({'error': 'Failed to start interview session'}), 500
        
        return jsonify({
            'status': 'success',
            'message': 'Interview session started'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _process_interview_completion(interview_data):
    """
    Internal function to handle interview completion tasks
    - Stores evaluation
    - Sends notifications if needed
    - Archives interview data
    """
    try:
        # Get conversation ID for reference
        conversation_id = interview_data.get('conversation_id')
        
        # Store interview data and evaluation
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"interview_records/{conversation_id}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(interview_data, f, indent=2)
            
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

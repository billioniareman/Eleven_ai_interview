from flask import Blueprint, render_template, request, jsonify, current_app, abort
from app.interview_agent import InterviewAgent
from flask_socketio import emit
from app import socketio
import json
from datetime import datetime
import os
from pymongo import MongoClient
from bson.objectid import ObjectId

main = Blueprint('main', __name__)
interview_agent = None

# MongoDB connection for invite validation
MONGO_URI = "mongodb+srv://admin:4sZf4uIsrlO6GCoV@staging-cluster.olgilw6.mongodb.net/user_management"
client = MongoClient(MONGO_URI)
db = client["interivew"]
invite_collection = db["Invite"]

def is_invite_valid(invite_doc):
    return (
        not invite_doc.get("is_used", False)
        and datetime.utcnow() < invite_doc["expires_at"]
    )

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/interview/<token>')
def interview(token):
    # Validate token from MongoDB
    invite = invite_collection.find_one({"token": token})
    if not invite:
        abort(404, 'Invalid or expired interview link.')
    expires_at = invite["expires_at"]
    is_used = invite.get("is_used", False)
    form_data = invite.get("form_data")
    if is_used or datetime.utcnow() > expires_at:
        abort(403, 'Interview link expired or already used.')
    candidate_info = json.loads(form_data) if form_data else {}
    global interview_agent
    interview_agent = InterviewAgent()
    interview_context = interview_agent.create_context(candidate_info)
    interview_agent.start_session(interview_context)
    return render_template('interview.html', candidate=candidate_info)

def _process_interview_completion(interview_data):
    try:
        conversation_id = interview_data.get('conversation_id')
        token = interview_data.get('token')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"interview_records/{conversation_id}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(interview_data, f, indent=2)
        # Update invite in MongoDB
        invite_collection.update_one(
            {"token": token},
            {"$set": {
                "interview_completed": True,
                "interview_results": json.dumps(interview_data),
                "completed_at": datetime.utcnow(),
                "is_used": True
            }}
        )
        current_app.logger.info(f"Interview {conversation_id} completed and processed")
    except Exception as e:
        current_app.logger.error(f"Error processing interview completion: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    global interview_agent
    if interview_agent:
        try:
            interview_data = interview_agent.end_session()
            _process_interview_completion(interview_data)
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
    global interview_agent
    if interview_agent and interview_agent.conversation:
        interview_agent.conversation.pause_session()
        emit('interview_paused', {'status': 'paused'})

@socketio.on('resume_interview')
def handle_resume():
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

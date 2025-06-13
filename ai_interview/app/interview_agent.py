from elevenlabs import ElevenLabs
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
from flask import current_app
import json
from datetime import datetime

class InterviewAgent:
    def __init__(self):
        self.client = ElevenLabs(api_key=current_app.config['ELEVENLABS_API_KEY'])
        self.conversation = None
        self.interview_data = {
            "timestamp": "",
            "candidate_info": {},
            "conversation_history": [],
            "evaluation": {}
        }
    
    def create_context(self, resume_data):
        """Create interview context based on resume data"""
        experience = resume_data.get('experience', [])
        skills = resume_data.get('skills', [])
        
        context = {
            "candidate_experience": experience,
            "technical_skills": skills,
            "interview_stage": "initial",
            "questions_asked": []
        }
        
        self.interview_data["candidate_info"] = resume_data
        self.interview_data["timestamp"] = datetime.now().isoformat()
        
        return context

    def store_conversation(self, speaker, text):
        """Store conversation entries"""
        self.interview_data["conversation_history"].append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })

    def evaluate_interview(self):
        """Evaluate the interview based on collected data"""
        # Initialize evaluation structure
        evaluation = {
            "resume_validation": {
                "experience_verified": False,
                "skills_verified": False,
                "discrepancies": []
            },
            "technical_assessment": {
                "proficiency_level": "",
                "strengths": [],
                "areas_for_improvement": []
            },
            "communication_assessment": {
                "pronunciation_clarity": "",
                "response_quality": "",
                "articulation": ""
            },
            "overall_score": 0
        }
        
        self.interview_data["evaluation"] = evaluation
        return evaluation

    def start_session(self, context):
        """Start a new interview session"""
        try:
            self.conversation = Conversation(
                self.client,
                current_app.config['AGENT_ID'],
                requires_auth=True,
                audio_interface=DefaultAudioInterface(),
                
                # Enhanced callbacks to store conversation
                callback_agent_response=lambda response: self.store_conversation("agent", response),
                callback_user_transcript=lambda transcript: self.store_conversation("candidate", transcript),
            )
            
            self.conversation.start_session()
            return True
            
        except Exception as e:
            print(f"Error starting session: {e}")
            return False

    def end_session(self):
        """End the interview session and generate evaluation"""
        if self.conversation:
            conversation_id = self.conversation.end_session()
            self.interview_data["conversation_id"] = conversation_id
            self.evaluate_interview()
            
            # Save interview data to file
            with open(f"interview_{conversation_id}.json", "w") as f:
                json.dump(self.interview_data, f, indent=2)
            
            return self.interview_data

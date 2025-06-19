from elevenlabs import ElevenLabs
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
from flask import current_app
import json
from datetime import datetime
import threading
import time

class InterviewAgent:
    def __init__(self):
        self.client = ElevenLabs(api_key=current_app.config['ELEVENLABS_API_KEY'])
        self.agent_id = current_app.config['AGENT_ID']
        self.conversation = None
        self.interview_data = {
            "timestamp": "",
            "candidate_info": {},
            "conversation_history": [],
            "evaluation": {}
        }
        # Initialize tools
        self.job_description = None
        self.interview_framework = None
        self.scoring_system = {
            "technical_score": 0,
            "communication_score": 0,
            "total_questions_asked": 0,
            "correct_responses": 0
        }
        self.time_tracker = {
            "start_time": None,
            "end_time": None,
            "duration": 0,
            "max_duration": 600  # 10 minutes in seconds
        }
        self.interview_active = False

    def create_context(self, resume_data):
        """Create interview context based on parsed resume data"""
        context = {
            "professional_summary": resume_data.get('professional_summary', []),
            "candidate_information": resume_data.get('candidate_information', {}),
            "education": resume_data.get('education', []),
            "candidate_experience": resume_data.get('professional_experience', []),
            "technical_skills": resume_data.get('skills', []),
            "certifications": resume_data.get('certifications', []),
            "projects": resume_data.get('relevant_projects', []),
            "links": resume_data.get('important_link', []),
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

    def track_time(self):
        """Monitor interview duration and end if exceeds 30 minutes"""
        while self.interview_active:
            if not self.time_tracker["start_time"]:
                continue
            current_time = datetime.now()
            duration = (current_time - self.time_tracker["start_time"]).seconds
            if duration >= self.time_tracker["max_duration"]:
                print("Interview duration exceeded 10 minutes. Ending session...")
                self.end_session()
                break
            time.sleep(10)  # Check every 10 seconds

    def start_session(self, context):
        """Start a new interview session"""
        try:
            self.conversation = Conversation(
                client=self.client,
                agent_id=self.agent_id,
                requires_auth=True,
                audio_interface=DefaultAudioInterface(),
                callback_agent_response=lambda response: self.store_conversation("agent", response),
                callback_user_transcript=lambda transcript: self.store_conversation("candidate", transcript)
            )
            # Initialize timing
            self.time_tracker["start_time"] = datetime.now()
            self.interview_active = True
            # Start time tracking in separate thread
            timer_thread = threading.Thread(target=self.track_time)
            timer_thread.daemon = True
            timer_thread.start()
            # Start the conversation
            self.conversation.start_session()
            return True
        except Exception as e:
            print(f"Error starting session: {e}")
            return False

    def evaluate_interview(self):
        """Evaluate the interview based on collected data"""
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
            "overall_score": 0,
            "duration": self.time_tracker["duration"]
        }
        self.interview_data["evaluation"] = evaluation
        return evaluation

    def end_session(self):
        """End the interview session and generate evaluation"""
        if self.conversation:
            try:
                self.interview_active = False
                self.time_tracker["end_time"] = datetime.now()
                self.time_tracker["duration"] = (self.time_tracker["end_time"] - self.time_tracker["start_time"]).seconds
                conversation_id = self.conversation.end_session()
                self.interview_data["conversation_id"] = conversation_id
                # Generate final evaluation
                self.evaluate_interview()
                # Save interview data
                filename = f"Interview_{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, "w") as f:
                    json.dump(self.interview_data, f, indent=2)
                return self.interview_data
            except Exception as e:
                print(f"Error ending session: {e}")
                return None

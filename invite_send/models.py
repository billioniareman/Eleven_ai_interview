from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask import Flask

db = SQLAlchemy()

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    form_data = db.Column(db.Text)  # JSON string of form data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    interview_completed = db.Column(db.Boolean, default=False)
    interview_results = db.Column(db.Text)  # JSON string of interview results
    completed_at = db.Column(db.DateTime)

    def is_valid(self):
        return not self.is_used and datetime.utcnow() < self.expires_at

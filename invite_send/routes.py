from flask import Blueprint, request, render_template_string, redirect, url_for, flash
from .models import db, Invite
from .email_utils import send_email
from datetime import datetime, timedelta
import secrets

bp = Blueprint('invite', __name__)

INVITE_FORM_HTML = '''
<form method="post" enctype="multipart/form-data">
    Name: <input type="text" name="name" required><br>
    Phone: <input type="text" name="phone" required><br>
    Resume: <input type="file" name="resume" accept=".pdf,.doc,.docx" required><br>
    Select Interview Time: <input type="datetime-local" name="interview_time" required><br>
    <input type="submit" value="Submit">
</form>
'''

UPLOAD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Upload Candidates File</title>
</head>
<body>
    <h2>Upload CSV or JSON File</h2>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv,.json" required>
        <input type="submit" value="Upload">
    </form>
    {% if message %}<p>{{ message }}</p>{% endif %}
</body>
</html>
'''

@bp.route('/send_invite', methods=['POST'])
def send_invite():
    email = request.form['email']
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    invite = Invite(email=email, token=token, expires_at=expires_at)
    db.session.add(invite)
    db.session.commit()
    link = url_for('invite.fill_form', token=token, _external=True)
    send_email(email, 'Interview Invite', f'Click <a href="{link}">here</a> to fill your details.')
    return 'Invite sent.'

@bp.route('/fill_form/<token>', methods=['GET', 'POST'])
def fill_form(token):
    invite = Invite.query.filter_by(token=token).first_or_404()
    if not invite.is_valid():
        return 'Link expired or already used.'
    if request.method == 'POST':
        form_data = request.form.to_dict()
        # Save resume file
        resume_file = request.files.get('resume')
        resume_filename = None
        if resume_file:
            import os
            uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            resume_filename = f"{token}_{resume_file.filename}"
            resume_path = os.path.join(uploads_dir, resume_filename)
            resume_file.save(resume_path)
            form_data['resume_path'] = resume_path
        # Save interview time and set link expiry
        interview_time = form_data.get('interview_time')
        if interview_time:
            from datetime import datetime, timedelta
            # Parse the selected time and set expiry to 30 min after
            start_time = datetime.fromisoformat(interview_time)
            invite.expires_at = start_time + timedelta(minutes=30)
            form_data['interview_time'] = interview_time
        invite.form_data = form_data
        invite.is_used = True
        db.session.commit()
        interview_token = secrets.token_urlsafe(32)
        interview_link = url_for('invite.interview', token=interview_token, _external=True)
        send_email(invite.email, 'Interview Link', f'Your interview link: <a href="{interview_link}">{interview_link}</a>')
        return 'Form submitted. Check your email for the interview link.'
    return render_template_string(INVITE_FORM_HTML)

@bp.route('/interview/<token>')
def interview(token):
    # Token validation logic here (for demo, just show a message)
    return 'Welcome to your interview!'

@bp.route('/upload_candidates', methods=['GET', 'POST'])
def upload_candidates():
    message = None
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            message = 'No file uploaded.'
        else:
            filename = file.filename.lower()
            emails_sent = 0
            if filename.endswith('.json'):
                try:
                    import json
                    candidates = json.load(file)
                    for candidate in candidates:
                        email = candidate.get('email')
                        if email:
                            # Send invite to each candidate email
                            token = secrets.token_urlsafe(32)
                            expires_at = datetime.utcnow() + timedelta(hours=24)
                            invite = Invite(email=email, token=token, expires_at=expires_at)
                            db.session.add(invite)
                            db.session.commit()
                            link = url_for('invite.fill_form', token=token, _external=True)
                            send_email(email, 'Interview Invite', f'Click <a href="{link}">here</a> to fill your details.')
                            emails_sent += 1
                    message = f"Successfully uploaded {len(candidates)} candidates from JSON. Sent {emails_sent} invites."
                except Exception as e:
                    message = f"Error reading JSON: {e}"
            elif filename.endswith('.csv'):
                try:
                    import csv
                    import io
                    reader = csv.DictReader(io.StringIO(file.read().decode('utf-8')))
                    candidates = list(reader)
                    for candidate in candidates:
                        email = candidate.get('email')
                        if email:
                            token = secrets.token_urlsafe(32)
                            expires_at = datetime.utcnow() + timedelta(hours=24)
                            invite = Invite(email=email, token=token, expires_at=expires_at)
                            db.session.add(invite)
                            db.session.commit()
                            link = url_for('invite.fill_form', token=token, _external=True)
                            send_email(email, 'Interview Invite', f'Click <a href="{link}">here</a> to fill your details.')
                            emails_sent += 1
                    message = f"Successfully uploaded {len(candidates)} candidates from CSV. Sent {emails_sent} invites."
                except Exception as e:
                    message = f"Error reading CSV: {e}"
            else:
                message = 'Unsupported file type.'
    return render_template_string(UPLOAD_HTML, message=message)

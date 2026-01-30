from flask import Blueprint, request, render_template_string, redirect, url_for, flash
from .models import invite_collection, is_invite_valid
from .email_utils import send_email
from datetime import datetime, timedelta
import secrets
from bson.objectid import ObjectId
import json
from pymongo.errors import PyMongoError
import logging
import os
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

bp = Blueprint('invite', __name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "eleven_ai")


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

PENDING_INVITES_FILE = os.path.join(os.path.dirname(__file__), 'pending_invites.json')

def _store_pending_invite(invite_doc):
    try:
        if os.path.exists(PENDING_INVITES_FILE):
            with open(PENDING_INVITES_FILE, 'r', encoding='utf-8') as f:
                pending = json.load(f)
        else:
            pending = []
    except Exception:
        pending = []
    pending.append(invite_doc)
    with open(PENDING_INVITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, default=str, indent=2)

# safe DB helpers to avoid AttributeError when invite_collection is None
def safe_insert(invite_doc):
    """
    Try to insert into Mongo; on failure or if DB unavailable, store to pending file.
    Returns True if inserted to DB, False otherwise.
    """
    if invite_collection is None:
        logging.warning("MongoDB not available — storing invite to pending file.")
        _store_pending_invite(invite_doc)
        return False
    try:
        invite_collection.insert_one(invite_doc)
        return True
    except Exception:
        # catch PyMongoError, AttributeError, or any other unexpected error
        logging.exception("DB insert failed or invite_collection invalid, storing pending invite")
        _store_pending_invite(invite_doc)
        return False

def safe_find_one(filter):
    if invite_collection is None:
        logging.warning("MongoDB not available — cannot find invite in DB.")
        return None
    try:
        return invite_collection.find_one(filter)
    except Exception:
        logging.exception("DB read failed or invite_collection invalid")
        return None

def safe_update_one(filter, update, fallback_doc=None):
    """
    Try to update in DB; on failure store fallback_doc (or filter+update) to pending.
    Returns True on success, False otherwise.
    """
    if invite_collection is None:
        logging.warning("MongoDB not available — storing update to pending file.")
        if fallback_doc:
            _store_pending_invite(fallback_doc)
        else:
            _store_pending_invite({"filter": filter, "update": update})
        return False
    try:
        invite_collection.update_one(filter, update)
        return True
    except Exception:
        logging.exception("DB update failed or invite_collection invalid, storing pending update")
        if fallback_doc:
            _store_pending_invite(fallback_doc)
        else:
            _store_pending_invite({"filter": filter, "update": update})
        return False

# The `invite_collection` is provided by `invite_send.models` and is
# already created (or set to None) in a guarded way. Avoid creating a
# second MongoClient here to prevent duplicate connection attempts at
# import time — use the imported `invite_collection` from `models.py`.

@bp.route('/', methods=['GET', 'POST'])
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
                    candidates = json.load(file)
                    for candidate in candidates:
                        email = candidate.get('email')
                        if email:
                            token = secrets.token_urlsafe(32)
                            expires_at = datetime.utcnow() + timedelta(hours=24)
                            invite_doc = {
                                "email": email,
                                "token": token,
                                "expires_at": expires_at,
                                "is_used": False,
                                "interview_completed": False,
                                "created_at": datetime.utcnow(),
                                "form_data": None,
                                "interview_results": None,
                                "completed_at": None
                            }
                            inserted = safe_insert(invite_doc)
                            if inserted:
                                link = url_for('invite.fill_form', token=token, _external=True)
                                send_email(email, 'Interview Invite', f'Click <a href="{link}">here</a> to fill your details.')
                                emails_sent += 1
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
                            invite_doc = {
                                "email": email,
                                "token": token,
                                "expires_at": expires_at,
                                "is_used": False,
                                "interview_completed": False,
                                "created_at": datetime.utcnow(),
                                "form_data": None,
                                "interview_results": None,
                                "completed_at": None
                            }
                            inserted = safe_insert(invite_doc)
                            if inserted:
                                link = url_for('invite.fill_form', token=token, _external=True)
                                send_email(email, 'Interview Invite', f'Click <a href="{link}">here</a> to fill your details.')
                                emails_sent += 1
                except Exception as e:
                    message = f"Error reading CSV: {e}"
            else:
                message = 'Unsupported file type.'
    return render_template_string(UPLOAD_HTML, message=message)

@bp.route('/send_invite', methods=['POST'])
def send_invite():
    email = request.form['email']
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    invite_doc = {
        "email": email,
        "token": token,
        "expires_at": expires_at,
        "is_used": False,
        "interview_completed": False,
        "created_at": datetime.utcnow(),
        "form_data": None,
        "interview_results": None,
        "completed_at": None
    }
    inserted = safe_insert(invite_doc)
    if inserted:
        link = url_for('invite.fill_form', token=token, _external=True)
        send_email(email, 'Interview Invite', f'Click <a href="{link}">here</a> to fill your details.')
        return 'Invite sent.'
    else:
        return 'DB unavailable, invite stored pending.'

@bp.route('/fill_form/<token>', methods=['GET', 'POST'])
def fill_form(token):
    invite = safe_find_one({"token": token})
    if not invite or not is_invite_valid(invite):
        return 'Link expired or already used.'
    if request.method == 'POST':
        form_data = request.form.to_dict()
        resume_file = request.files.get('resume')
        resume_filename = None
        parsed_resume_data = {}
        if resume_file:
            import os
            import requests
            import base64
            uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            resume_filename = f"{token}_{resume_file.filename}"
            resume_path = os.path.join(uploads_dir, resume_filename)
            resume_file.save(resume_path)
            form_data['resume_path'] = resume_path

            # Upload to S3 via API
            upload_api_url = "https://dev-api.supersourcing.com/user-management-service/api/v2/engineers/file-upload-to-google-cloud?type=doc"
            headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NTAxMzczOTUsInVzZXJfaWQiOiI2M2M3ZjMxODNhM2FjMjUwOGI2NTQ5NjgiLCJlbWFpbCI6ImFkbWluQGFkbWluLmNvbSIsInVzZXJfbmFtZSI6InJhaHVsIHNpbmdoIiwiZGVwYXJ0bWVudF9pZCI6MjQsImRlcGFydG1lbnRfc2x1Z19uYW1lIjoiQWRtaW4iLCJkZXBhcnRtZW50X25hbWUiOiJhZG1pbiIsImRlcGFydG1lbnRfZ3JhZGVfaWQiOjEwOSwicHJvZmlsZV9waWMiOiJodHRwczovL3N0b3JhZ2UuZ29vZ2xlYXBpcy5jb20vc3VwZXJzb3VyY2luZy1pbWctZGV2Lzc5NGJkOWFlLTljNjgtNGQ5NS1iY2I0LTA1MDQ0Y2I0ZWU0ZC5qcGciLCJtb2JpbGVfbnVtYmVyIjoiKzkxOTcxMzAwOTgyOCIsImxldmVsIjoidG9wIiwiZXhwIjoxNzUwNjU1Nzk1LCJ0b2tlbl9leHBpcmVfYXQiOiIyMDI1LTA2LTIzIDA1OjE2OjM1In0.qXEZGEIGoHzUgQ6fYjbEZpYZ3ar7VQOwkmbBiWXCtwQ"}
            files = {'file': (resume_file.filename, open(resume_path, 'rb'))}
            upload_response = requests.post(upload_api_url, headers=headers, files=files)
            upload_json = upload_response.json()
            if upload_response.status_code == 200 and upload_json.get('success'):
                uploaded_url = upload_json.get('data', {}).get('signedUrl')
                if not uploaded_url:
                    print("Upload API response missing 'signedUrl':", upload_json)
                    return "Resume upload failed: No URL returned from API.", 500
                # Parse resume using parsing API
                encoded_url = base64.b64encode(uploaded_url.encode()).decode()
                parse_api_url = f"https://staging-api.supersourcing.com/user-management-service/api/v1/engineers/get-resume-data-resume-parser/{encoded_url}"
                parse_headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NTAxMzczOTUsInVzZXJfaWQiOiI2M2M3ZjMxODNhM2FjMjUwOGI2NTQ5NjgiLCJlbWFpbCI6ImFkbWluQGFkbWluLmNvbSIsInVzZXJfbmFtZSI6InJhaHVsIHNpbmdoIiwiZGVwYXJ0bWVudF9pZCI6MjQsImRlcGFydG1lbnRfc2x1Z19uYW1lIjoiQWRtaW4iLCJkZXBhcnRtZW50X25hbWUiOiJhZG1pbiIsImRlcGFydG1lbnRfZ3JhZGVfaWQiOjEwOSwicHJvZmlsZV9waWMiOiJodHRwczovL3N0b3JhZ2UuZ29vZ2xlYXBpcy5jb20vc3VwZXJzb3VyY2luZy1pbWctZGV2Lzc5NGJkOWFlLTljNjgtNGQ5NS1iY2I0LTA1MDQ0Y2I0ZWU0ZC5qcGciLCJtb2JpbGVfbnVtYmVyIjoiKzkxOTcxMzAwOTgyOCIsImxldmVsIjoidG9wIiwiZXhwIjoxNzUwNjU1Nzk1LCJ0b2tlbl9leHBpcmVfYXQiOiIyMDI1LTA2LTIzIDA1OjE2OjM1In0.qXEZGEIGoHzUgQ6fYjbEZpYZ3ar7VQOwkmbBiWXCtwQ"}
                parse_response = requests.get(parse_api_url, headers=parse_headers)
                if parse_response.status_code == 200 and parse_response.json().get('success'):
                    parsed_resume_data = parse_response.json()['data']
                    form_data['parsed_resume'] = parsed_resume_data
            else:
                print("Upload API error:", upload_json)
                return f"Resume upload failed: {upload_json.get('message', 'Unknown error')}", 500
        # Save interview time and set link expiry
        interview_time = form_data.get('interview_time')
        if interview_time:
            start_time = datetime.fromisoformat(interview_time)
            invite['expires_at'] = start_time + timedelta(minutes=30)
            form_data['interview_time'] = interview_time
        # Merge parsed resume data into form_data for later use
        invite['form_data'] = json.dumps(form_data)
        # attempt DB update; on failure store pending with full invite doc
        updated = safe_update_one({"_id": invite["_id"]}, {"$set": {"form_data": invite['form_data'], "expires_at": invite['expires_at']}}, fallback_doc=invite)
        if not updated:
            # already stored by safe_update_one; inform user conservatively
            return 'Form submitted but DB currently unavailable. We will process it shortly.'
        interview_link = url_for('invite.interview', token=token, _external=True)
        send_email(invite['email'], 'Interview Link', f'Your interview link: <a href="{interview_link}">Here</a>')
        return 'Form submitted. Check your email for the interview link.'
    return render_template_string(INVITE_FORM_HTML)

@bp.route('/interview/<token>')
def interview(token):
    # Redirect to the AI interview app with the token
    ai_interview_url = f"http://127.0.0.1:8000/interview/{token}"
    return redirect(ai_interview_url)

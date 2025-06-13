import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import os


def send_email(to_email, subject, html_content):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = 'rampra9981@gmail.com'
    smtp_password = 'otfbxsttumrmozdx'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email
    part = MIMEText(html_content, 'html')
    msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())

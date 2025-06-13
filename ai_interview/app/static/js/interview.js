// interview.js
// ...existing code...
document.addEventListener('DOMContentLoaded', function() {
    // Handle resume upload
    const resumeForm = document.getElementById('resumeForm');
    if (resumeForm) {
        resumeForm.addEventListener('submit', handleResumeUpload);
    }

    // Initialize interview if on interview page
    if (window.location.pathname === '/interview') {
        initializeInterview();
    }
});

async function handleResumeUpload(e) {
    e.preventDefault();
    
    const formData = new FormData();
    const resumeFile = document.getElementById('resumeFile').files[0];
    formData.append('resume', resumeFile);
    
    try {
        const response = await fetch('/upload_resume', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Store interview context in sessionStorage
            sessionStorage.setItem('interviewContext', JSON.stringify(data.context));
            // Redirect to interview page
            window.location.href = '/interview';
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error uploading resume');
    }
}

function initializeInterview() {
    const context = JSON.parse(sessionStorage.getItem('interviewContext'));
    if (!context) {
        window.location.href = '/';
        return;
    }
    
    // Initialize ElevenLabs widget
    const widget = document.querySelector('elevenlabs-convai');
    if (widget) {
        widget.addEventListener('ready', () => {
            updateStatus('Connected');
        });
        
        widget.addEventListener('message', (event) => {
            const message = event.detail;
            updateQuestionCount();
            // Handle interview progress
        });
    }
}

function updateStatus(status) {
    const statusElement = document.getElementById('currentStatus');
    if (statusElement) {
        statusElement.textContent = status;
    }
}

function updateQuestionCount() {
    const countElement = document.getElementById('questionCount');
    if (countElement) {
        const currentCount = parseInt(countElement.textContent);
        countElement.textContent = currentCount + 1;
    }
}

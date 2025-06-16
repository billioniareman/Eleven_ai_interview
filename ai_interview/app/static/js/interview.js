// interview.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize interview if on interview page
    if (window.location.pathname.startsWith('/interview/')) {
        initializeInterview();
    }
});

function initializeInterview() {
    // Interview context is now handled server-side after token validation
    // You may fetch candidate info if needed via AJAX
    
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

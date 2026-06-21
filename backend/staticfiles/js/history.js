// History.js - History page interactions
function viewAnalysis(event, analysisId) {
    if (event) event.preventDefault();
    window.location.href = `/functionalities/?id=${analysisId}`;
}

function deleteHistory(event, historyId) {
    event.preventDefault();
    event.stopPropagation();

    if (confirm('Are you sure you want to delete this analysis?')) {
        fetch(`/api/history/${historyId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove the item from the page
                const historyItem = event.target.closest('.history-item');
                if (historyItem) {
                    historyItem.style.opacity = '0';
                    historyItem.style.transition = 'opacity 0.3s ease';
                    setTimeout(() => historyItem.remove(), 300);
                }
                showMessage('Analysis deleted successfully', 'success');
            } else {
                showMessage('Error deleting analysis', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('Network error', 'error');
        });
    }
}

function toggleStar(event, analysisId) {
    event.preventDefault();
    event.stopPropagation();

    fetch(`/api/analysis/${analysisId}/star/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const starBtn = event.target;
            starBtn.textContent = data.is_starred ? '⭐' : '☆';
        }
    })
    .catch(error => console.error('Error:', error));
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `${type}-message`;
    messageDiv.textContent = message;
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    if (type === 'success') {
        messageDiv.style.background = '#dcfce7';
        messageDiv.style.color = '#16a34a';
        messageDiv.style.border = '1px solid #86efac';
    } else {
        messageDiv.style.background = '#fee2e2';
        messageDiv.style.color = '#dc2626';
        messageDiv.style.border = '1px solid #fca5a5';
    }

    document.body.appendChild(messageDiv);
    
    setTimeout(() => messageDiv.remove(), 3000);
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

// Initialize event listeners on page load
document.addEventListener('DOMContentLoaded', function() {
    // History items click handler
    const historyItems = document.querySelectorAll('.history-item');
    historyItems.forEach(item => {
        item.addEventListener('click', function(e) {
            if (!e.target.closest('.star-btn') && !e.target.closest('.btn-delete')) {
                const analysisId = this.querySelector('.btn-view')?.onclick?.toString().match(/\d+/)[0];
                if (analysisId) {
                    window.location.href = `/functionalities/?id=${analysisId}`;
                }
            }
        });
    });
});

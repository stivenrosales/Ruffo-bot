/**
 * Ruffo Chat - Frontend JavaScript
 * Mobile-first chat interface
 */

// State
let threadId = null;
let isLoading = false;

// DOM Elements
const messagesContainer = document.getElementById('messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const loadingOverlay = document.getElementById('loading');

/**
 * Initialize the chat
 */
function init() {
    // Form submit handler
    chatForm.addEventListener('submit', handleSubmit);

    // Enter key handler (for desktop)
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    });

    // Focus input on load
    messageInput.focus();

    // Scroll to bottom
    scrollToBottom();

    console.log('🐕 Ruffo Chat initialized!');
}

/**
 * Handle form submission
 */
async function handleSubmit(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message || isLoading) return;

    // Clear input
    messageInput.value = '';

    // Add user message
    addMessage(message, 'user');

    // Send to API
    await sendMessage(message);
}

/**
 * Send message to API
 */
async function sendMessage(message) {
    setLoading(true);

    // Show typing indicator
    const typingEl = showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                thread_id: threadId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Save thread ID for conversation continuity
        threadId = data.thread_id;

        // Remove typing indicator
        removeTypingIndicator(typingEl);

        // Add Ruffo's response
        addMessage(data.response, 'ruffo');

    } catch (error) {
        console.error('Error sending message:', error);

        // Remove typing indicator
        removeTypingIndicator(typingEl);

        // Show error message
        addMessage('🐕 ¡Guau! Tuve un problema técnico. ¿Puedes intentar de nuevo?', 'ruffo');
    } finally {
        setLoading(false);
        messageInput.focus();
    }
}

/**
 * Add a message to the chat
 */
function addMessage(text, sender) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${sender}`;

    const avatar = sender === 'ruffo' ? '🐕' : '👤';

    // Simple text with line breaks converted to <br>
    const formattedText = escapeHtml(text).replace(/\n/g, '<br>');

    messageEl.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-bubble">${formattedText}</div>
    `;

    messagesContainer.appendChild(messageEl);
    scrollToBottom();
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const typingEl = document.createElement('div');
    typingEl.className = 'message ruffo typing';
    typingEl.innerHTML = `
        <div class="message-avatar">🐕</div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(typingEl);
    scrollToBottom();
    return typingEl;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(el) {
    if (el && el.parentNode) {
        el.parentNode.removeChild(el);
    }
}

/**
 * Set loading state
 */
function setLoading(loading) {
    isLoading = loading;
    sendButton.disabled = loading;
    messageInput.disabled = loading;

    if (loading) {
        sendButton.innerHTML = '<div class="loading-spinner" style="width:20px;height:20px;border-width:2px;"></div>';
    } else {
        sendButton.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
    }
}

/**
 * Scroll to bottom of messages
 */
function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Clear chat history (for debugging)
 */
function clearChat() {
    threadId = null;
    messagesContainer.innerHTML = `
        <div class="message ruffo">
            <div class="message-avatar">🐕</div>
            <div class="message-bubble">
                <p>¡Guau, guau! 🐾 Soy Ruffo, el perro más rockero de Animalicha 🤘</p>
                <p>¿En qué te puedo ayudar hoy, humano-amigo?</p>
            </div>
        </div>
    `;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);

// Expose clearChat for debugging
window.clearChat = clearChat;

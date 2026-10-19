/**
 * AskGuruGranthSahib — Frontend Logic
 * Handles chat interactions, API calls, and UI state.
 */

// --- API Configuration ---
const API_BASE = window.location.origin;

// --- DOM Elements ---
const chatMessages = document.getElementById('chatMessages');
const welcomeContainer = document.getElementById('welcomeContainer');
const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');
const statsText = document.getElementById('statsText');
const statsDot = document.querySelector('.stats-dot');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const particlesContainer = document.getElementById('particles');

// --- State ---
let isLoading = false;
let messageCount = 0;

// --- Initialize ---
document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initTextarea();
    fetchStats();
});

// --- Background Particles ---
function initParticles() {
    const count = 25;
    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.animationDuration = `${8 + Math.random() * 12}s`;
        particle.style.animationDelay = `${Math.random() * 10}s`;
        particle.style.width = `${2 + Math.random() * 3}px`;
        particle.style.height = particle.style.width;
        particle.style.opacity = `${0.1 + Math.random() * 0.2}`;
        particlesContainer.appendChild(particle);
    }
}

// --- Auto-resize Textarea ---
function initTextarea() {
    questionInput.addEventListener('input', () => {
        // Auto-resize
        questionInput.style.height = 'auto';
        questionInput.style.height = Math.min(questionInput.scrollHeight, 150) + 'px';

        // Enable/disable send button
        sendBtn.disabled = !questionInput.value.trim() || isLoading;
    });

    // Send on Enter (Shift+Enter for new line)
    questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                sendQuestion();
            }
        }
    });
}

// --- Fetch Stats ---
async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const data = await res.json();

        if (data.status === 'ready') {
            statsText.textContent = `Ready • ${data.total_chunks.toLocaleString()} passages indexed`;
            statsDot.classList.add('ready');
        } else {
            statsText.textContent = 'Knowledge base not loaded';
        }
    } catch {
        statsText.textContent = 'Server offline';
    }
}

// --- Send Question ---
async function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question || isLoading) return;

    // Hide welcome screen
    if (welcomeContainer) {
        welcomeContainer.style.display = 'none';
    }

    // Add user message
    addMessage('user', question);

    // Clear input
    questionInput.value = '';
    questionInput.style.height = 'auto';
    sendBtn.disabled = true;
    isLoading = true;

    // Show typing indicator
    const typingEl = addTypingIndicator();

    try {
        const res = await fetch(`${API_BASE}/api/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server error (${res.status})`);
        }

        const data = await res.json();

        // Remove typing indicator
        typingEl.remove();

        // Add assistant message
        addMessage('assistant', data.answer, data.sources);

    } catch (error) {
        typingEl.remove();
        addMessage('assistant', null, null, error.message);
    } finally {
        isLoading = false;
        sendBtn.disabled = !questionInput.value.trim();
    }
}

// --- Add Message to Chat ---
function addMessage(role, text, sources = null, error = null) {
    messageCount++;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;

    const avatar = role === 'user' ? '🙏' : '☬';
    const sender = role === 'user' ? 'You' : 'AskGuruGranthSahib';

    let bodyContent = '';

    if (error) {
        bodyContent = `
            <div class="error-message">
                <span>⚠️</span>
                <span>${escapeHtml(error)}</span>
            </div>
        `;
    } else {
        bodyContent = formatMarkdown(text);
    }

    // Build sources HTML
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        const chips = sources.map((s, i) => `
            <span class="source-chip" onclick="toggleSource(${messageCount}, ${i})">
                <span class="chip-icon">📖</span>
                Ang ${s.ang}
            </span>
        `).join('');

        const details = sources.map((s, i) => `
            <div class="source-detail" id="source-${messageCount}-${i}">
                <strong>Ang ${s.ang}:</strong> ${escapeHtml(s.text)}
            </div>
        `).join('');

        sourcesHtml = `
            <div class="sources-container">
                <div class="sources-title">📑 Referenced Angs</div>
                ${chips}
                ${details}
            </div>
        `;
    }

    messageEl.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${sender}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-body">
                ${bodyContent}
                ${sourcesHtml}
            </div>
        </div>
    `;

    chatMessages.appendChild(messageEl);
    scrollToBottom();
}

// --- Typing Indicator ---
function addTypingIndicator() {
    const el = document.createElement('div');
    el.className = 'message assistant';
    el.innerHTML = `
        <div class="message-avatar">☬</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">AskGuruGranthSahib</span>
                <span class="message-time">thinking...</span>
            </div>
            <div class="message-body">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(el);
    scrollToBottom();
    return el;
}

// --- Toggle Source Detail ---
function toggleSource(msgId, sourceIdx) {
    const el = document.getElementById(`source-${msgId}-${sourceIdx}`);
    if (el) {
        el.classList.toggle('expanded');
    }
}

// --- Format Markdown-ish text to HTML ---
function formatMarkdown(text) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph
    html = `<p>${html}</p>`;

    return html;
}

// --- HTML Escaping ---
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- Scroll to Bottom ---
function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

// --- Ask Suggestion ---
function askSuggestion(btn) {
    questionInput.value = btn.textContent.trim();
    questionInput.style.height = 'auto';
    questionInput.style.height = Math.min(questionInput.scrollHeight, 150) + 'px';
    sendBtn.disabled = false;
    questionInput.focus();

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        toggleSidebar();
    }

    // Auto-send
    sendQuestion();
}

// --- Reset Conversation ---
async function resetConversation() {
    try {
        await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
    } catch {
        // Silent fail — conversation still resets locally
    }

    // Clear chat
    chatMessages.innerHTML = '';
    messageCount = 0;

    // Re-show welcome
    const welcomeHtml = `
        <div class="welcome-container" id="welcomeContainer">
            <div class="welcome-icon-wrapper">
                <div class="welcome-icon">☬</div>
                <div class="welcome-glow"></div>
            </div>
            <h2 class="welcome-title">Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh</h2>
            <p class="welcome-subtitle">
                Ask me anything about Sri Guru Granth Sahib Ji. I will search through the sacred text
                and share wisdom grounded in Gurbani, with references to specific Angs.
            </p>
            <div class="welcome-divider">
                <span>ੴ</span>
            </div>
        </div>
    `;
    chatMessages.innerHTML = welcomeHtml;
}

// --- Toggle Sidebar (Mobile) ---
function toggleSidebar() {
    sidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('open');
}

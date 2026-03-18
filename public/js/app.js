/* ============================================================
   Love-Matcher App
   ============================================================ */

const API_URL = 'https://love-matcher.com';
let authToken = null;
let currentUser = null;
let matchPollInterval = null;
let currentTopicId = null;
let matchTopicId = null;

// Conversation topic categories shown in the sidebar checklist
const TOPIC_GROUPS = [
    { key: 'identity',    label: 'Who You Are',        dims: ['gender', 'seeking_gender', 'age', 'location', 'education', 'career'] },
    { key: 'values',      label: 'Values & Worldview',  dims: ['religion', 'politics', 'vision', 'finances'] },
    { key: 'family',      label: 'Family & Future',     dims: ['family_origin', 'children'] },
    { key: 'connection',  label: 'How You Connect',     dims: ['communication', 'conflict', 'affection', 'humor'] },
    { key: 'daily_life',  label: 'Daily Life',          dims: ['domestic', 'cleanliness', 'food', 'time', 'technology'] },
    { key: 'wellbeing',   label: 'Well-being',          dims: ['health', 'mental_health', 'social_energy', 'substances'] },
    { key: 'interests',   label: 'Interests',           dims: ['hobbies', 'travel', 'culture', 'pets'] },
    { key: 'partnership', label: 'Partnership Style',   dims: ['independence', 'decisions'] },
];

const ALL_DIMS = TOPIC_GROUPS.flatMap(g => g.dims);

/* ============================================================
   INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
    checkAutoLogin();
    setupChatInputKeydown();
});

async function checkAutoLogin() {
    const token = localStorage.getItem('authToken');
    const user  = localStorage.getItem('currentUser');
    if (!token || !user) return;

    try {
        authToken   = token;
        currentUser = JSON.parse(user);
    } catch {
        localStorage.removeItem('authToken');
        localStorage.removeItem('currentUser');
        return;
    }

    try {
        // Validate token with the server; apiFetch handles 401 → clears session + shows landing
        const res = await apiFetch(`${API_URL}/profile`);
        if (!res.ok) return;

        try {
            const profile = await res.json();
            currentUser = { ...currentUser, ...profile };
        } catch { /* keep existing currentUser if parse fails */ }
    } catch {
        // Network unavailable — show app with cached credentials
    }

    showLoggedInNav();
    showView('dashboard');
}

function showLoggedInNav() {
    document.getElementById('mainNav').classList.add('active');
}

/* ============================================================
   VIEW MANAGEMENT
   ============================================================ */
const VIEWS = ['landingPage', 'dashboardView', 'chatView', 'matchView',
               'profileView', 'settingsView', 'privacyView', 'termsView'];

function showView(name) {
    // Clear any polling
    if (matchPollInterval) {
        clearInterval(matchPollInterval);
        matchPollInterval = null;
    }

    // Hide all
    VIEWS.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // Remove nav active states
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const map = {
        landing:   { el: 'landingPage',   nav: null },
        dashboard: { el: 'dashboardView', nav: 'navDashboard' },
        chat:      { el: 'chatView',      nav: 'navChat' },
        match:     { el: 'matchView',     nav: 'navMatch' },
        profile:   { el: 'profileView',   nav: 'navProfile' },
        settings:  { el: 'settingsView',  nav: null },
        privacy:   { el: 'privacyView',   nav: null },
        terms:     { el: 'termsView',     nav: null },
    };

    const entry = map[name];
    if (!entry) return;

    const el = document.getElementById(entry.el);
    if (el) el.style.display = 'block';
    if (entry.nav) {
        const navEl = document.getElementById(entry.nav);
        if (navEl) navEl.classList.add('active');
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Load data for the view
    if (name === 'dashboard') loadDashboard();
    if (name === 'chat')      loadChatHistory();
    if (name === 'match')     loadMatch();
    if (name === 'profile')   loadProfile();
    if (name === 'settings')  loadSettings();
}

/* ============================================================
   AUTH
   ============================================================ */
function switchTab(tab) {
    const panelSignup = document.getElementById('panelSignup');
    const panelLogin  = document.getElementById('panelLogin');
    const tabSignup   = document.getElementById('tabSignup');
    const tabLogin    = document.getElementById('tabLogin');

    if (tab === 'signup') {
        panelSignup.classList.add('active');
        panelLogin.classList.remove('active');
        tabSignup.classList.add('active');
        tabLogin.classList.remove('active');
    } else {
        panelLogin.classList.add('active');
        panelSignup.classList.remove('active');
        tabLogin.classList.add('active');
        tabSignup.classList.remove('active');
    }

    scrollToAuth();
}

function scrollToAuth() {
    const el = document.getElementById('authSection');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const email  = document.getElementById('signupEmail').value.trim();
    const age    = parseInt(document.getElementById('signupAge').value);
    const gender = document.getElementById('signupGender').value;

    let valid = true;
    if (!email || !email.includes('@')) { showError('signupEmailError', 'Enter a valid email'); valid = false; }
    if (!gender) { showError('signupGenderError', 'Select your gender'); valid = false; }
    if (!age || age < 18 || age > 120) { showError('signupAgeError', 'Age must be 18–120'); valid = false; }
    if (!valid) return;

    const btn = e.target.querySelector('button[type=submit]');
    setBtnLoading(btn, 'Creating account…');

    try {
        const res = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, age, gender })
        });
        const data = await res.json();

        if (res.ok) {
            authToken   = data.token;
            currentUser = data;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            showToast('Welcome to Love-Matcher!', 'success');
            showLoggedInNav();
            setTimeout(() => showView('dashboard'), 600);
        } else {
            showMsg('signupMessage', data.error || 'Signup failed', 'error');
        }
    } catch {
        showMsg('signupMessage', 'Connection error. Please try again.', 'error');
    } finally {
        resetBtn(btn, 'Create Account — It\'s Free');
    }
});

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const email = document.getElementById('loginEmail').value.trim();
    if (!email || !email.includes('@')) { showError('loginEmailError', 'Enter a valid email'); return; }

    const btn = e.target.querySelector('button[type=submit]');
    setBtnLoading(btn, 'Signing in…');

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();

        if (res.ok) {
            authToken   = data.token;
            currentUser = data;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            showToast('Welcome back!', 'success');
            showLoggedInNav();
            setTimeout(() => showView('dashboard'), 600);
        } else {
            showMsg('loginMessage', data.error || 'Sign in failed', 'error');
        }
    } catch {
        showMsg('loginMessage', 'Connection error. Please try again.', 'error');
    } finally {
        resetBtn(btn, 'Sign In');
    }
});

function logout() {
    authToken   = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    document.getElementById('mainNav').classList.remove('active');
    showView('landing');
    showToast('Signed out');
}

/* ============================================================
   DASHBOARD
   ============================================================ */
async function loadDashboard() {
    if (!authToken) return;

    try {
        const [profileRes, matchRes] = await Promise.all([
            fetch(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${authToken}` } }),
            fetch(`${API_URL}/match`,   { headers: { Authorization: `Bearer ${authToken}` } }),
        ]);

        const profile = await profileRes.json();
        const matchData = await matchRes.json();

        if (!profileRes.ok) return;

        // Update header greeting
        const name = profile.name || '';
        const header = document.getElementById('dashboardHeader');
        if (header) {
            header.innerHTML = `
                <h1>Good to see you${name ? ', ' + name.split(' ')[0] : ''}</h1>
                <p class="text-muted">Here's where things stand</p>
            `;
        }

        // Completeness
        const dims   = Object.keys(profile.dimensions || {}).length;
        const pct    = Math.round((dims / ALL_DIMS.length) * 100);
        const fill   = document.getElementById('completenessFill');
        const score  = document.getElementById('completenessScore');
        const sub    = document.getElementById('completenessSubtext');
        const action = document.getElementById('completenessAction');

        if (fill)  fill.style.width  = pct + '%';
        if (score) score.textContent = pct + '%';

        const eligible = dims >= 5;
        if (sub) {
            sub.textContent = eligible
                ? `You've covered ${dims} of ${ALL_DIMS.length} topics — you're in the matching pool!`
                : `Cover at least 5 topics to enter the matching pool (${dims}/${ALL_DIMS.length} so far)`;
        }
        if (action) {
            action.innerHTML = pct >= 100
                ? `<span style="color:var(--success); font-size:0.875rem;">✓ Profile complete</span>`
                : `<button class="btn btn-primary btn-sm" onclick="showView('chat')">Continue Conversation <i class="ph ph-arrow-right"></i></button>`;
        }

        // Stats
        setIfExists('dashConvos', profile.conversation_count || 0);
        setIfExists('dashDims',   dims);
        setIfExists('dashPhotos', (profile.photos || []).length);

        // Topics checklist
        renderTopicsChecklist(profile.dimensions || {}, 'topicsList', true);

        // Match card
        renderDashMatchCard(matchData, eligible);

    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function renderDashMatchCard(matchData, profileEligible) {
    const container = document.getElementById('dashMatchContent');
    if (!container) return;

    if (!profileEligible) {
        container.innerHTML = `
            <div class="match-gate-notice">
                <p>Complete at least 5 conversation topics to enter the matching pool.</p>
                <button class="btn btn-sm btn-primary" onclick="showView('chat')">Start Conversation</button>
            </div>`;
        return;
    }

    if (matchData.match) {
        const m = matchData.match;
        const score = m.match_score || 0;
        container.innerHTML = `
            <div style="text-align:center; padding:16px 0;">
                <div style="font-family:var(--font-serif); font-size:2.5rem; color:var(--slate);">${score}%</div>
                <div style="font-size:0.775rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--slate-muted); margin-bottom:12px;">Compatibility</div>
                <p style="font-size:0.875rem; color:var(--slate-muted); margin-bottom:14px;">You have a match waiting!</p>
                <button class="btn btn-primary btn-sm" onclick="showView('match')">View Your Match</button>
            </div>`;
        // Show match badge
        const badge = document.getElementById('matchBadge');
        if (badge) badge.classList.remove('hidden');
    } else {
        container.innerHTML = `
            <div style="text-align:center; padding:16px 0;">
                <p style="font-size:0.875rem; color:var(--slate-muted); margin-bottom:4px;">${matchData.message || 'No match yet — we\'re looking!'}</p>
                <p style="font-size:0.775rem; color:var(--slate-muted);">Check back soon.</p>
            </div>`;
    }
}

/* ============================================================
   TOPICS CHECKLIST (reusable)
   ============================================================ */
function renderTopicsChecklist(dimensions, containerId, clickable) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '';
    TOPIC_GROUPS.forEach(group => {
        const filled   = group.dims.filter(d => dimensions[d]).length;
        const total    = group.dims.length;
        const complete = filled === total;
        const partial  = filled > 0 && filled < total;

        if (containerId === 'chatTopicsList') {
            // compact per-topic list in chat panel
            group.dims.forEach(dim => {
                const done = !!dimensions[dim];
                html += `
                    <div class="chat-topic-item${done ? '' : ''}">
                        <div class="chat-topic-check${done ? ' done' : ''}">
                            ${done ? '✓' : ''}
                        </div>
                        <div class="chat-topic-text">
                            <div class="label">${formatDimLabel(dim)}</div>
                            <div class="sub">${group.label}</div>
                        </div>
                    </div>`;
            });
        } else {
            // grouped for dashboard
            const statusIcon = complete ? '✓' : partial ? '…' : '';
            html += `
                <div class="topic-item" ${clickable ? 'onclick="showView(\'chat\')"' : ''}>
                    <div class="topic-check${complete ? ' done' : partial ? ' active' : ''}">
                        ${statusIcon}
                    </div>
                    <div style="flex:1;">
                        <div class="topic-label">${group.label}</div>
                        <div class="topic-sub">${filled}/${total} topics covered</div>
                    </div>
                </div>`;
        }
    });

    container.innerHTML = html;
}

function formatDimLabel(dim) {
    const labels = {
        gender: 'Gender identity', seeking_gender: 'Looking for', age: 'Life stage / age',
        location: 'Location', education: 'Education', career: 'Career',
        religion: 'Religion / spirituality', politics: 'Political views', vision: '10-year vision',
        finances: 'Finances', family_origin: 'Family background', children: 'Children',
        communication: 'Communication style', conflict: 'Conflict resolution',
        affection: 'Affection & love language', humor: 'Humor',
        domestic: 'Domestic roles', cleanliness: 'Cleanliness', food: 'Food & cooking',
        time: 'Time management', technology: 'Tech & screen time',
        health: 'Physical health', mental_health: 'Mental health',
        social_energy: 'Social energy', substances: 'Alcohol / substances',
        hobbies: 'Hobbies', travel: 'Travel', culture: 'Art & culture', pets: 'Pets',
        independence: 'Independence vs togetherness', decisions: 'Decision-making',
    };
    return labels[dim] || dim.replace(/_/g, ' ');
}

/* ============================================================
   CHAT
   ============================================================ */
async function loadChatHistory() {
    if (!authToken) return;

    const messagesDiv = document.getElementById('chatMessages');
    messagesDiv.innerHTML = '';

    try {
        const [topicsRes, profileRes] = await Promise.all([
            apiFetch(`${API_URL}/topics`),
            apiFetch(`${API_URL}/profile`),
        ]);

        const topicsData  = await topicsRes.json();
        const profileData = await profileRes.json();

        // Render topics sidebar
        if (topicsRes.ok) {
            renderTopicsList(topicsData.topics || [], topicsData.active_topic_id);

            // Load active topic messages
            const activeId = topicsData.active_topic_id || (topicsData.topics && topicsData.topics[0] && topicsData.topics[0].topic_id);
            if (activeId) {
                currentTopicId = activeId;
                await loadTopicMessages(activeId);
            } else {
                // No topics yet - show welcome message
                appendMessage(
                    "Hi! I'm here to get to know you — through conversation, not forms. Let's start simply: what's your name, and whereabouts do you live?",
                    'ai'
                );
                updateChatHeader('Getting to Know You', 'active');
            }
        }

        // Update progress bar
        if (profileRes.ok) {
            const dims  = profileData.dimensions || {};
            const count = Object.keys(dims).length;
            const pct   = Math.round((count / ALL_DIMS.length) * 100);
            setIfExists('chatProgressFill',  null, el => el.style.width = pct + '%');
            setIfExists('chatProgressLabel', `${count} / ${ALL_DIMS.length}`);
        }

    } catch (err) {
        console.error('Chat load error:', err);
        appendMessage("Hi! I'm here to get to know you — through conversation, not forms. Let's start simply: what's your name, and whereabouts do you live?", 'ai');
    }
}

async function loadTopicMessages(topicId) {
    const messagesDiv = document.getElementById('chatMessages');
    messagesDiv.innerHTML = '';

    try {
        const res  = await apiFetch(`${API_URL}/topics/${topicId}`);
        const data = await res.json();

        if (res.ok) {
            currentTopicId = topicId;
            updateChatHeader(data.title, data.status);

            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    appendMessage(msg.user, 'user', msg.timestamp);
                    appendMessage(msg.ai, 'ai', msg.timestamp);
                });
            } else {
                appendMessage("I'm ready to explore this topic with you. What would you like to share?", 'ai');
            }
        }
    } catch (err) {
        console.error('Topic load error:', err);
    }
}

function updateChatHeader(topicTitle, status) {
    const header = document.querySelector('.chat-header-bar h2');
    const sub    = document.querySelector('.chat-header-bar .sub');
    if (header) header.textContent = topicTitle || 'Your Conversation';
    if (sub) {
        if (status === 'completed') {
            sub.innerHTML = '<span style="color:var(--success)">✓ Topic completed</span> · Chat with our matchmaking AI';
        } else {
            sub.textContent = 'Chat with our matchmaking AI to build your profile';
        }
    }
}

function renderTopicsList(topics, activeTopicId) {
    const container = document.getElementById('chatTopicsList');
    if (!container) return;

    let html = '';

    if (topics.length === 0) {
        html = `<div style="padding:12px; color:var(--slate-muted); font-size:0.8rem;">Your conversation topics will appear here as you chat.</div>`;
    } else {
        topics.forEach(topic => {
            const isActive  = topic.topic_id === activeTopicId && topic.status === 'active';
            const isDone    = topic.status === 'completed' || topic.status === 'archived';
            const msgCount  = topic.message_count || 0;

            html += `
                <div class="topic-thread-item ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}"
                     onclick="selectTopic('${topic.topic_id}')">
                    <div class="topic-thread-check ${isDone ? 'done' : isActive ? 'active' : ''}">
                        ${isDone ? '✓' : ''}
                    </div>
                    <div class="topic-thread-text">
                        <div class="topic-thread-title">${escapeHtml(topic.title)}</div>
                        <div class="topic-thread-meta">${msgCount} message${msgCount !== 1 ? 's' : ''}${isDone ? ' · done' : ''}</div>
                    </div>
                </div>`;
        });
    }

    // New topic button
    html += `
        <div style="padding:12px 8px; margin-top:4px;">
            <button class="btn btn-ghost btn-sm" style="width:100%; font-size:0.775rem;" onclick="startNewTopic()">
                + New Topic
            </button>
        </div>`;

    container.innerHTML = html;
}

async function selectTopic(topicId) {
    currentTopicId = topicId;

    // Update sidebar active state
    document.querySelectorAll('.topic-thread-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.topic-thread-item').forEach(el => {
        if (el.getAttribute('onclick') && el.getAttribute('onclick').includes(topicId)) {
            el.classList.add('active');
        }
    });

    await loadTopicMessages(topicId);
}

async function startNewTopic() {
    const title = prompt('What would you like to talk about?', 'New Conversation');
    if (!title) return;

    try {
        const res = await apiFetch(`${API_URL}/topics`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });

        if (res.ok) {
            const data = await res.json();
            currentTopicId = data.topic_id;
            showToast(`Started new topic: ${title}`, 'success');
            loadChatHistory();
        }
    } catch (err) {
        showToast('Could not create topic', 'error');
    }
}

async function fetchAndUpdateTopicsSidebar() {
    try {
        const res  = await apiFetch(`${API_URL}/topics`);
        const data = await res.json();
        if (res.ok) {
            renderTopicsList(data.topics || [], currentTopicId);
        }
    } catch {}
}

async function sendMessage() {
    const textarea = document.getElementById('chatInput');
    const btn      = document.getElementById('chatSendBtn');
    const message  = textarea.value.trim();
    if (!message) return;

    appendMessage(message, 'user');
    textarea.value = '';
    textarea.style.height = 'auto';

    textarea.disabled = true;
    setBtnLoading(btn, '…');
    showTypingIndicator();

    try {
        const body = { message };
        if (currentTopicId) body.topic_id = currentTopicId;

        const res = await apiFetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await res.json();
        removeTypingIndicator();

        if (res.ok) {
            appendMessage(data.response, 'ai', data.timestamp);

            // Update current topic id (backend may have created one)
            if (data.topic_id && !currentTopicId) {
                currentTopicId = data.topic_id;
            }

            // If topic was completed and next topic created, switch to it
            if (data.topic_status === 'completed') {
                showToast(`Topic "${data.topic_title}" completed!`, 'success');
                if (data.next_topic_id) {
                    setTimeout(() => {
                        currentTopicId = data.next_topic_id;
                        loadChatHistory();
                    }, 2000);
                } else {
                    // Refresh topics list
                    setTimeout(() => loadChatHistory(), 1500);
                }
            }

            // Update progress bar
            if (data.profile_completion) {
                const pct   = data.profile_completion.percentage;
                const count = data.profile_completion.count;
                setIfExists('chatProgressFill',  null, el => el.style.width = pct + '%');
                setIfExists('chatProgressLabel', `${count} / ${ALL_DIMS.length}`);
            }

            // Refresh topics sidebar
            fetchAndUpdateTopicsSidebar();
        } else {
            appendMessage(data.error || 'Something went wrong. Please try again.', 'ai');
        }
    } catch {
        removeTypingIndicator();
        appendMessage('Connection error. Please try again.', 'ai');
    } finally {
        textarea.disabled = false;
        resetBtn(btn, 'Send');
        textarea.focus();
    }
}

async function fetchProfileAndUpdateTopics() {
    // Kept for compatibility - now uses topics sidebar refresh
    await fetchAndUpdateTopicsSidebar();
}

function appendMessage(text, type, timestamp) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `message ${type}`;

    const timeStr = timestamp
        ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : 'Just now';

    div.innerHTML = `
        <div class="message-bubble">${escapeHtml(text)}</div>
        <div class="message-time">${timeStr}</div>`;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.id = 'typingIndicator';
    div.className = 'typing-indicator';
    div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

function autoResizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function setupChatInputKeydown() {
    document.addEventListener('keydown', e => {
        if (e.target.id === 'chatInput') {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }
    });
}

/* ============================================================
   MATCH VIEW
   ============================================================ */
async function loadMatch() {
    if (!authToken) return;

    const container = document.getElementById('matchContainer');
    container.innerHTML = '<div style="text-align:center;padding:48px;color:var(--slate-muted);">Loading…</div>';

    try {
        const [matchRes, profileRes] = await Promise.all([
            fetch(`${API_URL}/match`,   { headers: { Authorization: `Bearer ${authToken}` } }),
            fetch(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${authToken}` } }),
        ]);

        const matchData   = await matchRes.json();
        const profileData = await profileRes.json();

        if (!matchRes.ok) {
            container.innerHTML = renderNoMatch('Unable to load match data.');
            return;
        }

        // Check profile eligibility
        const dims = Object.keys(profileData.dimensions || {}).length;
        if (dims < 5) {
            container.innerHTML = renderNoMatch(
                'You need to complete at least 5 conversation topics before you can be matched.',
                true
            );
            return;
        }

        if (matchData.match) {
            container.innerHTML = renderMatchCard(matchData.match);

            // Load match topics if mutual acceptance
            if (matchData.match.mutual_acceptance) {
                loadMatchTopics();
                matchPollInterval = setInterval(() => {
                    if (matchTopicId) loadMatchTopicMessages(matchTopicId);
                }, 5000);
            }
        } else {
            container.innerHTML = renderNoMatch(matchData.message || "We're finding your match — check back soon.");
        }

    } catch (err) {
        console.error('Match load error:', err);
        container.innerHTML = renderNoMatch('Unable to load match data.');
    }
}

function renderNoMatch(message, needsMoreProfile) {
    return `
        <div class="no-match-state">
            <div class="icon"><i class="ph ph-hourglass"></i></div>
            <h2>No match yet</h2>
            <p>${message}</p>
            ${needsMoreProfile
                ? `<button class="btn btn-primary" onclick="showView('chat')">Continue Conversation</button>`
                : `<p class="text-muted" style="font-size:0.825rem;">Matching runs daily. Make sure your matching is set to Active in Settings.</p>`}
        </div>`;
}

function renderMatchCard(match) {
    const score         = match.match_score || 0;
    const userAccepted  = match.user_accepted;
    const matchAccepted = match.match_accepted;
    const mutual        = match.mutual_acceptance;
    const analysis      = match.match_analysis || {};

    const scoreColor = score >= 80 ? '#4A7C59' : score >= 60 ? '#B89A6A' : '#A07878';

    let bodyContent = '';

    // Analysis block
    if (analysis.reasoning) {
        bodyContent += `
            <div class="match-analysis-block">
                <h4>Why you might work</h4>
                <p>${escapeHtml(analysis.reasoning)}</p>
                ${analysis.strengths ? `<div class="match-tags">${analysis.strengths.split(',').map(s => `<span class="match-tag">${escapeHtml(s.trim())}</span>`).join('')}</div>` : ''}
            </div>`;
    }

    // Preview info
    const preview = match.preview || {};
    bodyContent += `
        <div class="match-preview-row">
            <div class="match-preview-item">
                <div class="val">${match.age || '?'}</div>
                <div class="key">Age</div>
            </div>
            <div class="match-preview-item">
                <div class="val">${preview.location || (match.location || '—')}</div>
                <div class="key">Location</div>
            </div>
            <div class="match-preview-item">
                <div class="val">${preview.completion_percentage || match.completion_percentage || '?'}%</div>
                <div class="key">Profile</div>
            </div>
        </div>`;

    // Photos (after mutual acceptance)
    if (mutual && match.photos && match.photos.length > 0) {
        const photoHtml = match.photos.map(url => `
            <img src="${url}" style="width:100%; height:120px; object-fit:cover; border-radius:var(--radius-sm); cursor:pointer;"
                 onclick="window.open('${url}','_blank')">`).join('');
        bodyContent += `
            <div style="margin-bottom:24px;">
                <p class="profile-section-title">Photos</p>
                <div style="display:grid; grid-template-columns:repeat(auto-fill,minmax(100px,1fr)); gap:8px;">${photoHtml}</div>
            </div>`;
    }

    // Actions
    if (!userAccepted) {
        bodyContent += `
            <div class="match-actions">
                <button class="btn btn-primary" onclick="acceptMatch()"><i class="ph ph-check"></i> Accept Introduction</button>
                <button class="btn btn-secondary" onclick="rejectMatch()">Decline</button>
            </div>`;
    } else if (!mutual) {
        bodyContent += `
            <div style="background:var(--cream-dark); border-radius:var(--radius); padding:20px; text-align:center;">
                <p style="font-size:0.875rem; color:var(--slate-muted);">You've accepted — waiting for the other person to respond.</p>
            </div>`;
    } else {
        // Mutual — show chat
        bodyContent += renderMatchChat(match);
    }

    return `
        <div class="match-card">
            <div class="match-card-header">
                <div class="compatibility-ring">
                    <div class="compatibility-number" style="color:${scoreColor}">${score}%</div>
                    <div class="compatibility-label">Match</div>
                </div>
                <h2>Your Match</h2>
                <div class="match-meta">
                    Matched ${match.matched_at ? new Date(match.matched_at).toLocaleDateString() : 'recently'}
                    ${userAccepted ? ' · <span style="color:#a0d4b0;">✓ You accepted</span>' : ''}
                    ${matchAccepted ? ' · <span style="color:#a0d4b0;">✓ They accepted</span>' : ''}
                </div>
            </div>
            <div class="match-card-body">
                ${bodyContent}
            </div>
        </div>`;
}

function renderMatchChat(matchInfo) {
    return `
        <div class="chaperone-intro">
            <p>You're connected! Our AI has started 3 conversation topics to help you get to know each other. Click any topic to begin.</p>
        </div>
        <div id="matchTopicsContainer">
            <div style="text-align:center; padding:24px; color:var(--slate-muted); font-size:0.875rem;">
                <span class="spinner"></span> Loading conversation topics…
            </div>
        </div>`;
}

async function loadMatchTopics() {
    try {
        const res  = await apiFetch(`${API_URL}/match/topics`);
        const data = await res.json();

        const container = document.getElementById('matchTopicsContainer');
        if (!container) return;

        if (!data.topics || data.topics.length === 0) {
            container.innerHTML = `<div style="text-align:center; padding:24px; color:var(--slate-muted);">Conversation topics are being prepared…</div>`;
            return;
        }

        // Show topic tabs
        let html = `<div class="match-topics-tabs">`;
        data.topics.forEach((topic, i) => {
            const isDone = topic.status === 'completed';
            const isActive = matchTopicId ? matchTopicId === topic.topic_id : i === 0;
            html += `
                <button class="match-topic-tab ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}"
                        onclick="selectMatchTopic('${topic.topic_id}', this)">
                    ${isDone ? '✓ ' : ''}${escapeHtml(topic.title)}
                </button>`;
        });
        html += `</div>`;

        // Chat area for selected topic
        html += `
            <div class="match-chat-area" id="matchTopicChatArea">
                <div class="match-chat-messages" id="matchChatMessages">
                    <div style="text-align:center; color:var(--slate-muted); padding:24px; font-size:0.875rem;">Select a topic above to begin…</div>
                </div>
                <div class="match-chat-input">
                    <input type="text" id="matchChatInput" placeholder="Share your thoughts…">
                    <button class="btn btn-primary btn-sm" onclick="sendMatchTopicMessage()">Send</button>
                </div>
            </div>`;

        container.innerHTML = html;

        // Auto-load first topic
        if (data.topics.length > 0) {
            const firstTopicId = matchTopicId || data.topics[0].topic_id;
            matchTopicId = firstTopicId;
            await loadMatchTopicMessages(firstTopicId);
        }
    } catch (err) {
        console.error('Match topics load error:', err);
    }
}

async function selectMatchTopic(topicId, tabEl) {
    matchTopicId = topicId;

    // Update tab active state
    document.querySelectorAll('.match-topic-tab').forEach(t => t.classList.remove('active'));
    if (tabEl) tabEl.classList.add('active');

    await loadMatchTopicMessages(topicId);
}

async function loadMatchTopicMessages(topicId) {
    const container = document.getElementById('matchChatMessages');
    if (!container) return;

    try {
        const [res, profileRes] = await Promise.all([
            apiFetch(`${API_URL}/match/topics/${topicId}`),
            apiFetch(`${API_URL}/profile`)
        ]);
        const data    = await res.json();
        const profile = await profileRes.json();
        const myId    = profile.user_id;

        container.innerHTML = '';

        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(m => {
                if (m.from === 'ai') {
                    const div = document.createElement('div');
                    div.className = 'match-ai-message';
                    div.innerHTML = `<span class="match-ai-label">✦ Love-Matcher</span> ${escapeHtml(m.message)}`;
                    container.appendChild(div);
                } else {
                    addMatchMessageToUI(m.message, m.from === myId ? 'sent' : 'received', m.timestamp);
                }
            });
        } else {
            container.innerHTML = `<div style="text-align:center; color:var(--slate-muted); padding:24px; font-size:0.875rem;">Start a conversation on this topic…</div>`;
        }
        container.scrollTop = container.scrollHeight;
    } catch (err) {
        console.error('Match topic messages error:', err);
    }
}

async function sendMatchTopicMessage() {
    if (!matchTopicId) return;
    const input = document.getElementById('matchChatInput');
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;

    input.disabled = true;

    try {
        const res  = await apiFetch(`${API_URL}/match/topics/${matchTopicId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();

        if (res.ok) {
            input.value = '';
            addMatchMessageToUI(msg, 'sent', data.timestamp);

            if (data.ai_message) {
                const container = document.getElementById('matchChatMessages');
                if (container) {
                    const div = document.createElement('div');
                    div.className = 'match-ai-message';
                    div.innerHTML = `<span class="match-ai-label">✦ Love-Matcher</span> ${escapeHtml(data.ai_message)}`;
                    container.appendChild(div);
                    container.scrollTop = container.scrollHeight;
                }
            }

            if (data.topic_status === 'completed') {
                showToast('This topic has been completed!', 'success');
                loadMatchTopics(); // Refresh to show completion
            }
        } else {
            showToast(data.error || 'Send failed', 'error');
        }
    } catch {
        showToast('Connection error', 'error');
    } finally {
        input.disabled = false;
    }
}

async function acceptMatch() {
    if (!confirm('Accept this introduction? Once both of you accept, you\'ll be able to chat.')) return;

    try {
        const res  = await fetch(`${API_URL}/match/accept`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message || 'Introduction accepted!', 'success');
            loadMatch();
        } else {
            showToast(data.error || 'Failed', 'error');
        }
    } catch {
        showToast('Connection error', 'error');
    }
}

async function rejectMatch() {
    if (!confirm('Decline this match? You\'ll be returned to the matching pool.')) return;

    try {
        const res  = await fetch(`${API_URL}/match/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (res.ok) {
            showToast('Match declined', 'info');
            loadMatch();
        } else {
            showToast(data.error || 'Failed', 'error');
        }
    } catch {
        showToast('Connection error', 'error');
    }
}

async function sendMatchMessage() {
    const input = document.getElementById('matchChatInput');
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;

    try {
        const res  = await fetch(`${API_URL}/match/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        if (res.ok) {
            input.value = '';
            addMatchMessageToUI(msg, 'sent', data.timestamp);
        } else {
            showToast(data.error || 'Send failed', 'error');
        }
    } catch {
        showToast('Connection error', 'error');
    }
}

async function loadMatchMessages() {
    try {
        const profileRes = await fetch(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${authToken}` } });
        const profile    = await profileRes.json();
        const myId       = profile.user_id;

        const res  = await fetch(`${API_URL}/match/messages`, { headers: { Authorization: `Bearer ${authToken}` } });
        const data = await res.json();

        if (res.ok && data.messages.length > 0) {
            const container = document.getElementById('matchChatMessages');
            if (!container) return;
            container.innerHTML = '';
            data.messages.forEach(m => {
                addMatchMessageToUI(m.message, m.from === myId ? 'sent' : 'received', m.timestamp);
            });
        }
    } catch {}
}

function addMatchMessageToUI(text, type, timestamp) {
    const container = document.getElementById('matchChatMessages');
    if (!container) return;

    // Clear placeholder
    const placeholder = container.querySelector('[style*="text-align:center"]');
    if (placeholder) placeholder.remove();

    const div = document.createElement('div');
    div.className = `match-message-bubble ${type}`;
    const timeStr = timestamp
        ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : 'Just now';
    div.innerHTML = `${escapeHtml(text)}<div style="font-size:0.7rem; opacity:0.6; margin-top:4px;">${timeStr}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// Match chat enter key
document.addEventListener('keypress', e => {
    if (e.target.id === 'matchChatInput' && e.key === 'Enter') sendMatchTopicMessage();
});

/* ============================================================
   PROFILE VIEW
   ============================================================ */
async function loadProfile() {
    if (!authToken) return;

    try {
        const res     = await fetch(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${authToken}` } });
        const profile = await res.json();
        if (!res.ok) return;

        currentUser = profile;

        setIfExists('profileName',   profile.name || '—');
        setIfExists('profileAge',    profile.age  || '—');
        setIfExists('profileLocation', profile.location || '—');
        setIfExists('profileGender', profile.gender === 'M' || profile.gender === 'male' ? 'Male' :
                                     profile.gender === 'F' || profile.gender === 'female' ? 'Female' : '—');

        const aboutEl = document.getElementById('profileAbout');
        if (aboutEl) {
            aboutEl.textContent = profile.about || 'Share something about yourself in conversation…';
            aboutEl.style.color = profile.about ? 'var(--slate)' : 'var(--slate-muted)';
        }

        const dims = Object.keys(profile.dimensions || {}).length;
        setIfExists('profileDims',   `${dims} / ${ALL_DIMS.length}`);
        setIfExists('profileConvos', profile.conversation_count || 0);

        if (profile.created_at) {
            setIfExists('profileMemberSince', new Date(profile.created_at).toLocaleDateString());
        }

        renderPhotos(profile.photos || [], 'profilePhotoGrid', 'photoUploadBtn');
        renderProfileMatchingToggle(profile, dims);
        renderProfileSummary(profile, dims);
    } catch (err) {
        console.error('Profile load error:', err);
    }
}

function renderProfileMatchingToggle(profile, dims) {
    const container = document.getElementById('profileMatchingContent');
    if (!container) return;

    const MIN_DIMS = 5;
    const isActive = profile.matching_active === true;

    if (dims < MIN_DIMS) {
        container.innerHTML = `
            <p style="font-size:0.875rem; color:var(--slate-muted); margin-bottom:12px;">
                Complete at least ${MIN_DIMS} conversation topics to enable matching (${dims}/${MIN_DIMS} so far).
            </p>
            <button class="btn btn-primary btn-sm" onclick="showView('chat')">Continue Conversation</button>`;
        return;
    }

    container.innerHTML = `
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div>
                <div style="font-size:0.9rem; font-weight:500; color:var(--slate); margin-bottom:2px;">
                    ${isActive ? 'You are in the matching pool' : 'Matching is off'}
                </div>
                <div style="font-size:0.825rem; color:var(--slate-muted);">
                    ${isActive ? 'Turn off to pause while you take a break.' : 'Turn on to be considered for matches.'}
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px; flex-shrink:0; margin-left:16px;">
                <label class="toggle-switch">
                    <input type="checkbox" id="profileMatchingToggle" onchange="toggleMatchingFromProfile()"
                           ${isActive ? 'checked' : ''}>
                    <span class="toggle-slider"></span>
                </label>
                <span class="status-pill ${isActive ? 'active' : 'inactive'}" id="profileMatchingStatus">
                    ${isActive ? 'Active' : 'Off'}
                </span>
            </div>
        </div>`;
}

async function toggleMatchingFromProfile() {
    const toggle = document.getElementById('profileMatchingToggle');
    const pill   = document.getElementById('profileMatchingStatus');
    const active = toggle.checked;

    toggle.disabled = true;
    try {
        const res  = await fetch(`${API_URL}/match/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ active })
        });
        const data = await res.json();

        if (res.ok) {
            const label = document.querySelector('#profileMatchingContent [style*="font-weight:500"]');
            const sub   = document.querySelector('#profileMatchingContent [style*="slate-muted"]');
            if (label) label.textContent = active ? 'You are in the matching pool' : 'Matching is off';
            if (sub)   sub.textContent   = active ? 'Turn off to pause while you take a break.' : 'Turn on to be considered for matches.';
            if (pill) {
                pill.textContent = active ? 'Active' : 'Off';
                pill.className   = `status-pill ${active ? 'active' : 'inactive'}`;
            }
            showToast(`Matching ${active ? 'activated' : 'paused'}`, 'success');
        } else {
            toggle.checked = !active;
            showToast(data.error || 'Failed to update', 'error');
        }
    } catch {
        toggle.checked = !active;
        showToast('Connection error', 'error');
    } finally {
        toggle.disabled = false;
    }
}

function renderProfileSummary(profile, dims) {
    const content = document.getElementById('profileSummaryContent');
    const regenBtn = document.getElementById('profileSummaryRegenBtn');
    if (!content) return;

    const MIN_CONVOS = 3;
    const convos = profile.conversation_count || 0;

    if (convos < MIN_CONVOS) {
        content.innerHTML = `<p style="color:var(--slate-muted);">Have at least ${MIN_CONVOS} conversations and we'll generate a personal summary for you.</p>`;
        if (regenBtn) regenBtn.style.display = 'none';
        return;
    }

    if (profile.profile_summary) {
        const paragraphs = profile.profile_summary.split(/\n\n+/).filter(p => p.trim());
        content.innerHTML = paragraphs.map(p => `<p style="margin-bottom:1em;">${escapeHtml(p.trim())}</p>`).join('');
        if (regenBtn) regenBtn.style.display = 'inline-flex';
    } else {
        content.innerHTML = `
            <p style="color:var(--slate-muted); margin-bottom:12px;">We'll write a short narrative summary of who you are based on your conversations.</p>
            <button class="btn btn-secondary btn-sm" onclick="generateProfileSummary()">
                <i class="ph ph-sparkle"></i> Generate My Story
            </button>`;
        if (regenBtn) regenBtn.style.display = 'none';
    }
}

async function generateProfileSummary() {
    const content  = document.getElementById('profileSummaryContent');
    const regenBtn = document.getElementById('profileSummaryRegenBtn');
    if (!content) return;

    content.innerHTML = '<span style="color:var(--slate-muted); font-size:0.875rem;"><span class="spinner"></span> Writing your story…</span>';
    if (regenBtn) regenBtn.disabled = true;

    try {
        const res  = await fetch(`${API_URL}/profile/summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` }
        });
        const data = await res.json();

        if (res.ok && data.summary) {
            const paragraphs = data.summary.split(/\n\n+/).filter(p => p.trim());
            content.innerHTML = paragraphs.map(p => `<p style="margin-bottom:1em;">${escapeHtml(p.trim())}</p>`).join('');
            if (regenBtn) { regenBtn.style.display = 'inline-flex'; regenBtn.disabled = false; }
            showToast('Your story has been written!', 'success');
        } else {
            content.innerHTML = `<p style="color:var(--error); font-size:0.875rem;">${escapeHtml(data.error || data.message || 'Could not generate summary.')}</p>`;
            if (regenBtn) regenBtn.disabled = false;
        }
    } catch {
        content.innerHTML = `<p style="color:var(--error); font-size:0.875rem;">Connection error. Please try again.</p>`;
        if (regenBtn) regenBtn.disabled = false;
    }
}

function handlePhotoSelect(event) {
    const file = event.target.files[0];
    if (file) uploadPhoto(file);
}

async function uploadPhoto(file) {
    const btn = document.getElementById('photoUploadBtn');
    setBtnLoading(btn, 'Uploading…');

    const formData = new FormData();
    formData.append('photo', file);

    try {
        const res  = await fetch(`${API_URL}/profile/photos`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${authToken}` },
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            showToast('Photo uploaded!', 'success');
            renderPhotos(data.photos, 'profilePhotoGrid', 'photoUploadBtn');
        } else {
            showToast(data.error || 'Upload failed', 'error');
        }
    } catch {
        showToast('Upload connection error', 'error');
    } finally {
        resetBtn(btn, '<i class="ph ph-upload-simple"></i> Upload Photo');
        document.getElementById('photoUploadInput').value = '';
    }
}

async function deletePhoto(url) {
    if (!confirm('Delete this photo?')) return;

    try {
        const res  = await fetch(`${API_URL}/profile/photos`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ photo_url: url })
        });
        const data = await res.json();

        if (res.ok) {
            showToast('Photo deleted', 'success');
            renderPhotos(data.photos, 'profilePhotoGrid', 'photoUploadBtn');
        } else {
            showToast(data.error || 'Delete failed', 'error');
        }
    } catch {
        showToast('Connection error', 'error');
    }
}

function renderPhotos(photos, gridId, btnId) {
    const grid = document.getElementById(gridId);
    if (!grid) return;

    grid.innerHTML = '';

    photos.forEach(url => {
        const div = document.createElement('div');
        div.className = 'photo-item';
        div.innerHTML = `
            <img src="${url}" alt="Profile photo">
            <button class="photo-delete-btn" onclick="deletePhoto('${url}')" title="Delete photo">×</button>`;
        grid.appendChild(div);
    });

    for (let i = photos.length; i < 3; i++) {
        const div = document.createElement('div');
        div.className = 'photo-item photo-item-empty';
        div.innerHTML = '<i class="ph ph-plus"></i>';
        grid.appendChild(div);
    }

    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = photos.length >= 3;
}

/* ============================================================
   SETTINGS
   ============================================================ */
async function loadSettings() {
    if (!authToken) return;

    try {
        const [profileRes, matchRes] = await Promise.all([
            fetch(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${authToken}` } }),
            fetch(`${API_URL}/match`,   { headers: { Authorization: `Bearer ${authToken}` } }),
        ]);

        const profile = await profileRes.json();
        const matchData = await matchRes.json();

        if (!profileRes.ok) return;

        setIfExists('settingsEmail',       profile.email || '—');
        setIfExists('settingsMemberNum',   '#' + (profile.member_number || '?'));
        setIfExists('settingsAccountType', 'Free');

        const dims = Object.keys(profile.dimensions || {}).length;
        const pct  = Math.round((dims / ALL_DIMS.length) * 100);
        setIfExists('settingsCompletion',   pct + '%');
        setIfExists('settingsDimensions',   `${dims} / ${ALL_DIMS.length}`);
        setIfExists('settingsConversations', profile.conversation_count || 0);
        setIfExists('settingsPhotos',        `${(profile.photos || []).length} / 3`);

        const isActive = profile.matching_active !== false;
        const toggle   = document.getElementById('settingsMatchingToggle');
        const pill     = document.getElementById('settingsMatchingStatus');
        if (toggle) toggle.checked = isActive;
        if (pill) {
            pill.textContent  = isActive ? 'Active' : 'Paused';
            pill.className    = `status-pill ${isActive ? 'active' : 'inactive'}`;
        }

        const matchStatus = matchData.match ? 'Matched' : 'Searching';
        setIfExists('settingsCurrentMatch', matchStatus);

    } catch (err) {
        console.error('Settings load error:', err);
    }
}

async function toggleMatchingFromSettings() {
    const toggle = document.getElementById('settingsMatchingToggle');
    const pill   = document.getElementById('settingsMatchingStatus');
    const active = toggle.checked;

    toggle.disabled = true;
    try {
        const res  = await fetch(`${API_URL}/match/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ active })
        });
        const data = await res.json();

        if (res.ok) {
            if (pill) {
                pill.textContent = active ? 'Active' : 'Paused';
                pill.className   = `status-pill ${active ? 'active' : 'inactive'}`;
            }
            showToast(`Matching ${active ? 'activated' : 'paused'}`, 'success');
        } else {
            toggle.checked = !active;
            showToast(data.error || 'Failed to update', 'error');
        }
    } catch {
        toggle.checked = !active;
        showToast('Connection error', 'error');
    } finally {
        toggle.disabled = false;
    }
}

/* ============================================================
   CANCEL / DELETE ACCOUNT
   ============================================================ */
function showCancelModal() {
    document.getElementById('cancelModal').style.display = 'flex';
}

function hideCancelModal() {
    document.getElementById('cancelModal').style.display = 'none';
}

async function deleteAccount() {
    const btn = document.getElementById('confirmDeleteBtn');
    setBtnLoading(btn, 'Deleting…');

    try {
        const res = await fetch(`${API_URL}/account`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${authToken}` }
        });

        if (res.ok) {
            hideCancelModal();
            showToast('Your account has been deleted.', 'info');
            setTimeout(() => logout(), 1500);
        } else {
            const data = await res.json();
            showToast(data.error || 'Failed to delete account', 'error');
            resetBtn(btn, 'Yes, Delete My Account');
        }
    } catch {
        showToast('Connection error', 'error');
        resetBtn(btn, 'Yes, Delete My Account');
    }
}

/* ============================================================
   TOAST NOTIFICATIONS
   ============================================================ */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast     = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✓', error: '✗', info: 'i' };
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || 'i'}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
        <div class="toast-close" onclick="this.parentElement.remove()">×</div>`;

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

/* ============================================================
   AUTHENTICATED FETCH — auto-handles 401 with re-login prompt
   ============================================================ */
async function apiFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    if (authToken) options.headers['Authorization'] = `Bearer ${authToken}`;

    const res = await fetch(url, options);

    if (res.status === 401) {
        const data = await res.json().catch(() => ({}));
        // Session expired — clear credentials and prompt re-login
        authToken   = null;
        currentUser = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('currentUser');
        document.getElementById('mainNav').classList.remove('active');
        VIEWS.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        const landingEl = document.getElementById('landingPage');
        if (landingEl) landingEl.style.display = 'block';
        showToast('Your session has expired — please sign in again.', 'error');
        // Return a fake Response so callers don't crash
        return new Response(JSON.stringify(data), { status: 401, headers: { 'Content-Type': 'application/json' } });
    }

    return res;
}

/* ============================================================
   UTILITY HELPERS
   ============================================================ */
function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function setIfExists(id, value, fn) {
    const el = document.getElementById(id);
    if (!el) return;
    if (fn) { fn(el); return; }
    if (value !== null && value !== undefined) el.textContent = value;
}

function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.textContent = msg;
}

function clearErrors() {
    document.querySelectorAll('.input-error').forEach(el => el.textContent = '');
}

function showMsg(id, msg, type) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<div class="msg-${type}">${escapeHtml(msg)}</div>`;
}

function setBtnLoading(btn, label) {
    if (!btn) return;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> ${label}`;
}

function resetBtn(btn, label) {
    if (!btn) return;
    btn.disabled = false;
    btn.innerHTML = label;
}

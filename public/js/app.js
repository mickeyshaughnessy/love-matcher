const API_URL = 'https://rse-api.com:5009';
let authToken = null;
let currentUser = null;
let matchMessagesInterval = null;
let currentStream = null;

// Camera Functions
async function startCamera(videoId) {
    // Only request if in browser environment that supports it
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        const videoEl = document.getElementById(videoId);
        if (videoEl) {
            videoEl.srcObject = stream;
            currentStream = stream;
        } else {
            // If element missing, stop stream immediately
            stream.getTracks().forEach(track => track.stop());
        }
    } catch (err) {
        console.warn("Camera access denied or error:", err);
    }
}

function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
}

// Toast notification system
function showToast(message, type = 'info') {
    const toastHTML = `
        <div class="toast ${type}">
            <div class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'}</div>
            <div class="toast-message">${message}</div>
            <div class="toast-close" onclick="this.parentElement.remove()">×</div>
        </div>
    `;
    
    const toast = document.createElement('div');
    toast.innerHTML = toastHTML;
    document.body.appendChild(toast.firstElementChild);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        const toastEl = document.querySelector('.toast:last-of-type');
        if (toastEl) toastEl.remove();
    }, 3000);
}

// Inline Validation Helpers
function showInputError(elementId, message) {
    const errorDiv = document.getElementById(elementId);
    if (errorDiv) {
        errorDiv.textContent = message;
    }
}

function clearInputErrors() {
    document.querySelectorAll('.input-error').forEach(el => el.textContent = '');
}

// Show typing indicator
function showTypingIndicator() {
    const messagesDiv = document.getElementById('chatMessages');
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    messagesDiv.appendChild(indicator);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadMemberStats();
    checkAutoLogin();
});

// Check for saved session and auto-login
function checkAutoLogin() {
    const savedToken = localStorage.getItem('authToken');
    const savedUser = localStorage.getItem('currentUser');
    
    if (savedToken && savedUser) {
        authToken = savedToken;
        currentUser = JSON.parse(savedUser);
        document.getElementById('mainNav').classList.add('active');
        showView('chat');
    }
}

// Load membership statistics
async function loadMemberStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('totalMembers').textContent = data.total_members.toLocaleString();
            document.getElementById('spotsRemaining').textContent = data.spots_remaining.toLocaleString();
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Scroll functions
function scrollToAuth() {
    document.getElementById('authSection').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function scrollToAbout() {
    document.getElementById('aboutSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// View management
function showView(viewName) {
    // Clear any existing message polling
    if (matchMessagesInterval) {
        clearInterval(matchMessagesInterval);
        matchMessagesInterval = null;
    }
    
    // Stop camera from previous view
    stopCamera();
    
    // Hide all views
    document.getElementById('landingPage').style.display = 'none';
    document.getElementById('chatView').style.display = 'none';
    document.getElementById('matchView').style.display = 'none';
    document.getElementById('profileView').style.display = 'none';
    document.getElementById('privacyView').style.display = 'none';
    document.getElementById('termsView').style.display = 'none';
    document.getElementById('settingsView').style.display = 'none';

    // Remove active class from all nav links
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));

    // Show selected view
    switch(viewName) {
        case 'landing':
            document.getElementById('landingPage').style.display = 'block';
            // Hide nav when on landing page (unless logged in)
            if (!authToken) {
                document.getElementById('mainNav').classList.remove('active');
            }
            break;
        case 'chat':
            document.getElementById('chatView').style.display = 'block';
            document.querySelectorAll('.nav-link')[1].classList.add('active');
            loadChatHistory();
            startCamera('buildCamera');
            break;
        case 'profile':
            document.getElementById('profileView').style.display = 'block';
            document.querySelectorAll('.nav-link')[2].classList.add('active');
            loadProfile();
            startCamera('connectCamera');
            break;
        case 'privacy':
            document.getElementById('privacyView').style.display = 'block';
            break;
        case 'terms':
            document.getElementById('termsView').style.display = 'block';
            break;
        case 'settings':
            document.getElementById('settingsView').style.display = 'block';
            document.querySelectorAll('.nav-link')[3].classList.add('active');
            loadSettings();
            break;
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Signup
document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Clear previous errors
    clearInputErrors();
    
    const email = document.getElementById('signupEmail').value.trim();
    const age = parseInt(document.getElementById('signupAge').value);
    const gender = document.getElementById('signupGender').value;
    
    let hasError = false;
    
    // Input validation
    if (!email || !email.includes('@')) {
        showInputError('signupEmailError', 'Please enter a valid email address');
        hasError = true;
    }
    
    if (!gender) {
        showInputError('signupGenderError', 'Please select your gender');
        hasError = true;
    }
    
    if (age < 18 || age > 120) {
        showInputError('signupAgeError', 'Age must be between 18 and 120');
        hasError = true;
    }
    
    if (hasError) return;
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span>Creating...';
    
    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, age, gender })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            currentUser = data;
            
            // Save to localStorage for auto-login
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            showToast(data.message || 'Account created successfully!', 'success');
            document.getElementById('signupMessage').innerHTML = 
                `<div class="success">${data.message}</div>`;
            
            // Show chat to start building profile
            setTimeout(() => {
                document.getElementById('mainNav').classList.add('active');
                showView('chat');
            }, 1500);
        } else {
            const errorMsg = data.error || 'Signup failed';
            // Generic signup error fallback
            showToast(errorMsg, 'error');
            document.getElementById('signupMessage').innerHTML = 
                `<div class="error">${errorMsg}</div>`;
        }
    } catch (error) {
        const errorMsg = 'Connection error. Please try again.';
        showToast(errorMsg, 'error');
        document.getElementById('signupMessage').innerHTML = 
            `<div class="error">${errorMsg}</div>`;
        console.error('Signup error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Account';
    }
});

// Login
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearInputErrors();
    
    const email = document.getElementById('loginEmail').value.trim();
    
    // Input validation
    if (!email || !email.includes('@')) {
        showInputError('loginEmailError', 'Please enter a valid email address');
        return;
    }
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span>Logging in...';
    
    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            currentUser = data;
            
            // Save to localStorage for auto-login
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            showToast('Login successful!', 'success');
            document.getElementById('loginMessage').innerHTML = 
                `<div class="success">Login successful!</div>`;
            
            // Show chat view
            setTimeout(() => {
                document.getElementById('mainNav').classList.add('active');
                showView('chat');
            }, 1000);
        } else {
            const errorMsg = data.error || 'Login failed';
            showToast(errorMsg, 'error');
            document.getElementById('loginMessage').innerHTML = 
                `<div class="error">${errorMsg}</div>`;
        }
    } catch (error) {
        const errorMsg = 'Connection error. Please try again.';
        showToast(errorMsg, 'error');
        document.getElementById('loginMessage').innerHTML = 
            `<div class="error">${errorMsg}</div>`;
        console.error('Login error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Login';
    }
});

// Logout
function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    document.getElementById('mainNav').classList.remove('active');
    showView('landing');
    showToast('Logged out successfully');
}

// Load chat history
async function loadChatHistory() {
    if (!authToken) return;
    
    try {
        // Clear existing chat first
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';
        
        const response = await fetch(`${API_URL}/chat/history`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        
        if (response.ok && data.messages.length > 0) {
            data.messages.forEach(msg => {
                addMessage(msg.user, 'user', msg.timestamp);
                addMessage(msg.ai, 'ai', msg.timestamp);
            });
        } else {
            // Show initial message if no history
            chatMessages.innerHTML = `
                <div class="message ai">
                    <div>Hi! Let's build your profile together. First, tell me your name, where you're located, and a bit about yourself. Then we'll dive into what matters most to you in a relationship.</div>
                    <div class="message-time">Just now</div>
                </div>
            `;
        }
        
        // Update sidebar
        updateChatSidebar();
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

// Update chat sidebar with dimension progress
async function updateChatSidebar() {
    try {
        const response = await fetch(`${API_URL}/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const profile = await response.json();
        
        if (response.ok) {
            const dimensionsCount = Object.keys(profile.dimensions || {}).length;
            const percentage = Math.round((dimensionsCount / 29) * 100);
            
            document.getElementById('sidebarDimensionCount').textContent = dimensionsCount;
            document.getElementById('sidebarPercentage').textContent = `${percentage}%`;
            document.getElementById('sidebarProgressBar').style.width = `${percentage}%`;
            
            // Update matching toggle state
            const isActive = profile.matching_active !== false;
            const buildToggle = document.getElementById('buildMatchingToggle');
            const buildStatusLabel = document.getElementById('buildMatchingStatusLabel');
            if (buildToggle) {
                buildToggle.checked = isActive;
                buildStatusLabel.textContent = isActive ? 'Active' : 'Inactive';
                buildStatusLabel.className = isActive ? 'status-text active' : 'status-text inactive';
            }
            
            // Update photos in Build Profile sidebar
            if (typeof renderPhotos === 'function') {
                renderPhotos(profile.photos || [], 'chatPhotoGrid', 'chatPhotoUploadBtn');
            }
            
            // Update JSON viewer
            const jsonViewer = document.getElementById('jsonViewer');
            if (jsonViewer) {
                jsonViewer.textContent = JSON.stringify(profile, null, 2);
            }
        }
    } catch (error) {
        console.error('Error updating sidebar:', error);
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const sendBtn = input.nextElementSibling;
    const message = input.value.trim();
    
    if (!message) return;
    
    addMessage(message, 'user');
    input.value = '';
    
    // Disable input and show spinner
    input.disabled = true;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="spinner"></span>Sending...';
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator();
        
        if (response.ok) {
            addMessage(data.response, 'ai', data.timestamp);
            updateChatSidebar();
        } else {
            const errorMsg = data.error || 'Sorry, there was an error. Please try again.';
            addMessage(errorMsg, 'ai');
            showToast(errorMsg, 'error');
        }
    } catch (error) {
        removeTypingIndicator();
        const errorMsg = 'Connection error. Please try again.';
        addMessage(errorMsg, 'ai');
        showToast(errorMsg, 'error');
        console.error('Chat error:', error);
    } finally {
        // Re-enable input and remove spinner
        input.disabled = false;
        sendBtn.disabled = false;
        sendBtn.innerHTML = 'Send';
        input.focus();
    }
}

// Add message to chat
function addMessage(text, type, timestamp) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : 'Just now';
    
    messageDiv.innerHTML = `
        <div>${text}</div>
        <div class="message-time">${timeStr}</div>
    `;
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Keyboard shortcuts for chat input
document.getElementById('chatInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    } else if (e.key === 'Escape') {
        e.target.value = '';
        e.target.blur();
    }
});

// Load current match
async function loadMatch() {
    try {
        const response = await fetch(`${API_URL}/match`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        
        // Update matching toggle status - read from top level of response
        const isActive = data.matching_active !== false;
        const statusLabel = document.getElementById('matchingStatusLabel');
        document.getElementById('matchingActiveToggle').checked = isActive;
        statusLabel.textContent = isActive ? 'Active' : 'Inactive';
        statusLabel.className = isActive ? 'status-text active' : 'status-text inactive';
        
        const matchContainer = document.getElementById('matchContainer');
        
        if (response.ok && data.match) {
            const match = data.match;
            matchContainer.innerHTML = createMatchCard(match, isActive, currentUser ? currentUser.photos : []);
            
            // Load match messages if both users accepted (mutual acceptance)
            if (match.mutual_acceptance) {
                loadMatchMessages();
            }
        } else {
            // No match yet - show self-preview for debugging
            const profileComplete = data.profile_complete;
            const dimensionsCount = data.dimensions_count || 0;
            
            // Fetch own profile to display as self-preview
            try {
                const profileResponse = await fetch(`${API_URL}/profile`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const profile = await profileResponse.json();
                
                if (profileResponse.ok) {
                    // Create a mock match object from own profile for debugging
                    const selfMatch = {
                        match_score: 100,
                        user_accepted: false,
                        match_accepted: false,
                        mutual_acceptance: false,
                        age: profile.age,
                        matched_at: new Date().toISOString(),
                        match_analysis: {
                            reasoning: '[DEBUG] This is how you appear to potential matches',
                            strengths: 'Self-preview for debugging purposes',
                            concerns: 'None - this is your own profile'
                        },
                        preview: {
                            age: profile.age,
                            location: profile.location || 'Not set',
                            completion_percentage: Math.round((dimensionsCount / 29) * 100)
                        },
                        full_profile: profile.dimensions || {}
                    };
                    
                    matchContainer.innerHTML = `
                        <div style="background: rgba(255, 193, 7, 0.1); border: 2px dashed #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #ffc107; margin-bottom: 10px;">🔧 Debug Mode: Self-Preview</h4>
                            <p style="color: var(--text-gray);">You have no match yet. Below is how you would appear in the "Your Match" section.</p>
                        </div>
                        ${createMatchCard(selfMatch, isActive)}
                    `;
                    return;
                }
            } catch (err) {
                console.error('Error loading self-preview:', err);
            }
            
            // Fallback to original "no match" UI if self-preview fails
            matchContainer.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-white);">
                    <div style="font-size: 3rem; margin-bottom: 20px;">🔍</div>
                    <h3 style="color: var(--text-white); margin-bottom: 15px;">${data.message || 'No match yet'}</h3>
                    ${!profileComplete ? `
                        <p style="color: var(--text-gray); margin-bottom: 20px;">You have ${dimensionsCount}/29 dimensions filled.</p>
                        <button class="btn-primary" onclick="showView('chat')" style="margin-top: 20px;">Continue Building Profile</button>
                    ` : `
                        <p style="color: var(--text-gray);">Your profile is complete! We'll notify you when we find a great match.</p>
                    `}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading match:', error);
    }
}

// Create match card
function createMatchCard(match, isActive, userPhotos = []) {
    const score = match.match_score || 0;
    const userAccepted = match.user_accepted || false;
    const matchAccepted = match.match_accepted || false;
    const mutualAcceptance = match.mutual_acceptance || false;
    
    // Match analysis
    const analysis = match.match_analysis || {};
    const reasoning = analysis.reasoning || 'AI-powered compatibility analysis';
    const strengths = analysis.strengths || 'Analyzing compatibility...';
    const concerns = analysis.concerns || 'None identified';
    
    // User's own photos (Digital Mirror concept in match card)
    let userPhotosHtml = '';
    if (userPhotos && userPhotos.length > 0) {
        const photoItems = userPhotos.map(url => `
            <div style="width: 60px; height: 60px; border-radius: 4px; overflow: hidden; border: 1px solid var(--gold-primary); margin: 0 4px;">
                <img src="${url}" style="width: 100%; height: 100%; object-fit: cover;">
            </div>
        `).join('');
        
        userPhotosHtml = `
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(212, 175, 55, 0.1); display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 0.8rem; color: var(--text-gray); margin-right: 10px;">You:</span>
                <div style="display: flex;">
                    ${photoItems}
                </div>
            </div>
        `;
    }
    
    // Build photo gallery HTML for mutual acceptance
    let photosHtml = '';
    if (mutualAcceptance && match.photos && match.photos.length > 0) {
        const photoItems = match.photos.map(url => `
            <div style="flex: 1; min-width: 100px; max-width: 150px;">
                <img src="${url}" alt="Match Photo" style="width: 100%; height: 150px; object-fit: cover; border-radius: 8px; cursor: pointer;" onclick="window.open('${url}', '_blank')">
            </div>
        `).join('');
        photosHtml = `
            <div style="background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid rgba(212, 175, 55, 0.2);">
                <h4 style="color: var(--gold-primary); margin-bottom: 15px;">📸 Photos</h4>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                    ${photoItems}
                </div>
            </div>
        `;
    }
    
    let profileDataHtml = '';
    if (mutualAcceptance && match.full_profile) {
        // Show full profile JSON after mutual acceptance
        const fullProfile = match.full_profile;
        const profileKeys = Object.keys(fullProfile);
        const profileItems = profileKeys.map(key => {
            const value = typeof fullProfile[key] === 'object' ? JSON.stringify(fullProfile[key]) : fullProfile[key];
            return `<div style="margin-bottom: 10px;"><strong>${key}:</strong> ${value}</div>`;
        }).join('');
        
        profileDataHtml = `
            <div style="background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid rgba(212, 175, 55, 0.2);">
                <h4 style="color: var(--gold-primary); margin-bottom: 15px;">📋 Match Profile (${profileKeys.length} dimensions)</h4>
                <div style="max-height: 300px; overflow-y: auto; font-size: 0.9rem; color: var(--text-gray);">
                    ${profileItems}
                </div>
            </div>
        `;
    } else if (match.preview) {
        // Show limited preview before acceptance
        const preview = match.preview;
        profileDataHtml = `
            <div style="background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid rgba(212, 175, 55, 0.2);">
                <h4 style="color: var(--gold-primary); margin-bottom: 15px;">👤 Match Preview</h4>
                <p style="color: var(--text-white);"><strong>Age:</strong> ${preview.age || 'N/A'}</p>
                <p style="color: var(--text-white);"><strong>Location:</strong> ${preview.location || 'N/A'}</p>
                <p style="color: var(--text-white);"><strong>Profile Completion:</strong> ${preview.completion_percentage || 0}%</p>
                <p style="color: var(--text-gray); font-style: italic; margin-top: 10px;">
                    Accept the match to see full profile details and start chatting!
                </p>
            </div>
        `;
    }
    
    let actionsHtml = '';
    if (!userAccepted) {
        // Show accept/decline buttons
        actionsHtml = `
            <div class="match-actions" style="margin-top: 20px;">
                <p style="color: var(--text-gray); margin-bottom: 15px; text-align: center;">
                    Review this match and decide if you'd like to connect
                </p>
                <div style="display: flex; gap: 15px; justify-content: center;">
                    <button class="btn-primary" onclick="acceptMatch()" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">
                        ✓ Accept Match
                    </button>
                    <button class="btn-reject" onclick="rejectMatch()">
                        ✗ Decline Match
                    </button>
                </div>
            </div>
        `;
    } else if (!mutualAcceptance) {
        // User accepted, waiting for match to accept
        actionsHtml = `
            <div style="background: #d1ecf1; padding: 20px; border-radius: 8px; margin-top: 20px; text-align: center;">
                <h4 style="color: #0c5460; margin-bottom: 10px;">⏳ Waiting for Match Response</h4>
                <p style="color: #0c5460;">You've accepted this match! Waiting for them to accept too.</p>
                <p style="color: #0c5460; font-size: 0.9rem; margin-top: 10px;">
                    Chat will be enabled once both of you accept.
                </p>
            </div>
        `;
    } else {
        // Both accepted - show chat interface
        actionsHtml = `
            <div class="match-chat-container" style="margin-top: 20px;">
                <h3 style="margin-bottom: 15px; color: var(--gold-primary);">💬 Private Chat</h3>
                <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center;">
                    <p style="color: #155724; font-weight: 600;">🎉 Match Accepted! You can now chat privately.</p>
                </div>
                <div class="match-chat-messages" id="matchChatMessages">
                    <div style="text-align: center; color: var(--text-gray); padding: 20px;">
                        Start a conversation!
                    </div>
                </div>
                <div class="match-chat-input-area">
                    <input type="text" id="matchChatInput" placeholder="Type your message...">
                    <button onclick="sendMatchMessage()">Send</button>
                </div>
            </div>
        `;
    }
    
    return `
        <div class="match-card">
            <div class="match-score">
                <div class="compatibility-circle">${score}%</div>
                <div style="color: var(--text-gray);">Compatibility</div>
            </div>
            <div class="match-info">
                <h3>Your Match</h3>
                <p style="color: var(--text-gray);">Age: ${match.age || 'N/A'}</p>
                <p style="color: var(--text-gray); margin-top: 10px;">Matched on ${match.matched_at ? new Date(match.matched_at).toLocaleDateString() : 'recently'}</p>
                ${userAccepted ? '<p style="color: #28a745; margin-top: 5px;">✓ You accepted</p>' : ''}
                ${matchAccepted ? '<p style="color: #28a745; margin-top: 5px;">✓ Match accepted</p>' : ''}
            </div>
            <div style="background: linear-gradient(135deg, #667eea10 0%, rgba(212, 175, 55, 0.1) 100%); padding: 15px; border-radius: 8px; margin-top: 15px;">
                <h4 style="color: var(--gold-primary); margin-bottom: 10px;">🔍 Compatibility Analysis</h4>
                <p style="color: var(--text-white); margin-bottom: 8px;"><strong>Reasoning:</strong> ${reasoning}</p>
                <p style="color: var(--text-white); margin-bottom: 8px;"><strong>Strengths:</strong> ${strengths}</p>
                <p style="color: var(--text-white);"><strong>Considerations:</strong> ${concerns}</p>
            </div>
            ${photosHtml}
            ${profileDataHtml}
            ${actionsHtml}
            ${userPhotosHtml}
        </div>
    `;
}

// Toggle matching active/inactive
async function toggleMatchingStatus() {
    const isActive = document.getElementById('matchingActiveToggle').checked;
    const statusLabel = document.getElementById('matchingStatusLabel');
    
    showToast(`Matching ${isActive ? 'activated' : 'deactivated'}`, 'info');
    
    try {
        const response = await fetch(`${API_URL}/match/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ active: isActive })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusLabel.textContent = isActive ? 'Active' : 'Inactive';
            statusLabel.className = isActive ? 'status-text active' : 'status-text inactive';
            showToast(`Matching ${isActive ? 'activated' : 'deactivated'} successfully`, 'success');
            syncAllToggles(isActive);
            // Reload match view to show appropriate UI
            loadMatch();
        } else {
            showToast(data.error || 'Failed to update status', 'error');
            // Revert toggle
            document.getElementById('matchingActiveToggle').checked = !isActive;
        }
    } catch (error) {
        console.error('Error toggling status:', error);
        showToast('Connection error. Please try again.', 'error');
        document.getElementById('matchingActiveToggle').checked = !isActive;
    }
}

// Accept current match
async function acceptMatch() {
    if (!confirm('Accept this match? This will allow both of you to chat once they also accept.')) {
        return;
    }
    
    showToast('Accepting match...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/match/accept`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(data.message || 'Match accepted successfully!', 'success');
            loadMatch();
        } else {
            showToast(data.error || 'Failed to accept match', 'error');
        }
    } catch (error) {
        console.error('Error accepting match:', error);
        showToast('Connection error. Please try again.', 'error');
    }
}

// Reject current match
async function rejectMatch() {
    if (!confirm('Decline this match? You will be matched with someone new in the next cycle.')) {
        return;
    }
    
    showToast('Declining match...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/match/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(data.message || 'Match declined successfully', 'success');
            loadMatch();
        } else {
            showToast(data.error || 'Failed to decline match', 'error');
        }
    } catch (error) {
        console.error('Error declining match:', error);
        showToast('Connection error. Please try again.', 'error');
    }
}

// Send message to match
async function sendMatchMessage() {
    const input = document.getElementById('matchChatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    try {
        const response = await fetch(`${API_URL}/match/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            input.value = '';
            // Add message to UI immediately
            addMatchMessage(message, 'sent', data.timestamp);
        } else {
            alert(data.error || 'Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Connection error. Please try again.');
    }
}

// Load match messages
async function loadMatchMessages() {
    try {
        // Get current user profile to determine user_id
        const profileResponse = await fetch(`${API_URL}/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const profile = await profileResponse.json();
        const myUserId = profile.user_id;
        
        const response = await fetch(`${API_URL}/match/messages`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        
        if (response.ok && data.messages.length > 0) {
            const messagesDiv = document.getElementById('matchChatMessages');
            messagesDiv.innerHTML = '';
            
            data.messages.forEach(msg => {
                const type = msg.from === myUserId ? 'sent' : 'received';
                addMatchMessage(msg.message, type, msg.timestamp);
            });
        }
    } catch (error) {
        console.error('Error loading match messages:', error);
    }
}

// Add match message to UI
function addMatchMessage(text, type, timestamp) {
    const messagesDiv = document.getElementById('matchChatMessages');
    if (!messagesDiv) return;
    
    // Clear placeholder if exists
    if (messagesDiv.querySelector('[style*="text-align: center"]')) {
        messagesDiv.innerHTML = '';
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `match-message ${type}`;
    
    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : 'Just now';
    
    messageDiv.innerHTML = `
        <div>${text}</div>
        <div style="font-size: 0.75rem; opacity: 0.7; margin-top: 5px;">${timeStr}</div>
    `;
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Enter key to send match message
document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('keypress', (e) => {
        if (e.target.id === 'matchChatInput' && e.key === 'Enter') {
            sendMatchMessage();
        }
    });
});

// Load profile (combined with match)
async function loadProfile() {
    try {
        // Load profile data
        const response = await fetch(`${API_URL}/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const profile = await response.json();
        
        if (response.ok) {
            // Update global current user with fresh data
            currentUser = profile;

            // Update stats
            const dimensionsCount = Object.keys(profile.dimensions || {}).length;
            const percentage = Math.round((dimensionsCount / 29) * 100);
            
            document.getElementById('profileDimCount').textContent = dimensionsCount;
            document.getElementById('profileCompletion').textContent = `${percentage}%`;
            document.getElementById('profileConvos').textContent = profile.conversation_count || 0;
            
            // Set main matching toggle state
            const isActive = profile.matching_active !== false;
            const mainToggle = document.getElementById('mainMatchingToggle');
            const mainStatusLabel = document.getElementById('mainMatchingStatusLabel');
            if (mainToggle) {
                mainToggle.checked = isActive;
                mainStatusLabel.textContent = isActive ? 'Active' : 'Inactive';
                mainStatusLabel.className = isActive ? 'status-text active' : 'status-text inactive';
            }
            
            // Update basic info
            document.getElementById('profileName').textContent = profile.name || 'Not set';
            document.getElementById('profileAge').textContent = profile.age || '-';
            document.getElementById('profileLocation').textContent = profile.location || 'Not set';
            document.getElementById('profileAbout').textContent = profile.about || 'Share something about yourself in the Build Profile section...';
            document.getElementById('profileAbout').style.fontStyle = profile.about ? 'normal' : 'italic';
            document.getElementById('profileAbout').style.color = profile.about ? 'var(--text-white)' : 'var(--text-gray)';
            
            // Update JSON viewer
            const jsonViewer = document.getElementById('profileJsonViewer');
            jsonViewer.textContent = JSON.stringify(profile, null, 2);
            
            // Load match data in the match section
            await loadMatchInProfile();
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

// Load match data for profile view
async function loadMatchInProfile() {
    try {
        const response = await fetch(`${API_URL}/match`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        const matchSection = document.getElementById('matchSection');
        
        if (response.ok && data.match) {
            const match = data.match;
            const isActive = data.matching_active !== false;
            
            matchSection.innerHTML = `
                <div class="matches-header">
                    <h2>Your Match</h2>
                    <p style="color: var(--text-gray); margin-top: 10px;">Based on 29-dimension compatibility analysis</p>
                </div>
                
                ${createMatchCard(match, isActive, currentUser ? currentUser.photos : [])}
            `;
        } else {
            // No match yet - show self-preview for debugging
            const isActive = data.matching_active !== false;
            const dimensionsCount = data.dimensions_count || 0;
            
            // Fetch own profile to display as self-preview
            try {
                const profileResponse = await fetch(`${API_URL}/profile`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const profile = await profileResponse.json();
                
                if (profileResponse.ok) {
                    // Create a mock match object from own profile for debugging
                    const selfMatch = {
                        match_score: 100,
                        user_accepted: false,
                        match_accepted: false,
                        mutual_acceptance: false,
                        age: profile.age,
                        matched_at: new Date().toISOString(),
                        match_analysis: {
                            reasoning: '[DEBUG] This is how you appear to potential matches',
                            strengths: 'Self-preview for debugging purposes',
                            concerns: 'None - this is your own profile'
                        },
                        preview: {
                            age: profile.age,
                            location: profile.location || 'Not set',
                            completion_percentage: Math.round((dimensionsCount / 29) * 100)
                        },
                        full_profile: profile.dimensions || {}
                    };
                    
                    matchSection.innerHTML = `
                        <div class="matches-header">
                            <h2>Your Match</h2>
                            <p style="color: var(--text-gray); margin-top: 10px;">Based on 29-dimension compatibility analysis</p>
                        </div>
                        <div style="background: rgba(255, 193, 7, 0.1); border: 2px dashed #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #ffc107; margin-bottom: 10px;">🔧 Debug Mode: Self-Preview</h4>
                            <p style="color: var(--text-gray);">You have no match yet. Below is how you would appear in the "Your Match" section.</p>
                        </div>
                        ${createMatchCard(selfMatch, isActive)}
                    `;
                    return;
                }
            } catch (err) {
                console.error('Error loading self-preview:', err);
            }
            
            // Fallback if self-preview fails
            matchSection.innerHTML = `
                <div class="matches-header">
                    <h2>Your Match</h2>
                    <p style="color: var(--text-gray); margin-top: 10px;">No match yet. Complete your profile to get matched!</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading match:', error);
    }
}

// Toggle matching status from Build Profile view
async function toggleBuildMatchingStatus() {
    const isActive = document.getElementById('buildMatchingToggle').checked;
    const statusLabel = document.getElementById('buildMatchingStatusLabel');
    
    try {
        const response = await fetch(`${API_URL}/match/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ active: isActive })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusLabel.textContent = isActive ? 'Active' : 'Inactive';
            statusLabel.className = isActive ? 'status-text active' : 'status-text inactive';
            showToast(`Matching ${isActive ? 'activated' : 'deactivated'}`, 'success');
            
            // Sync other toggles
            syncAllToggles(isActive);
        } else {
            showToast(data.error || 'Failed to update status', 'error');
            document.getElementById('buildMatchingToggle').checked = !isActive;
        }
    } catch (error) {
        console.error('Error toggling status:', error);
        showToast('Connection error. Please try again.', 'error');
        document.getElementById('buildMatchingToggle').checked = !isActive;
    }
}

// Sync all matching toggles across views
function syncAllToggles(isActive) {
    const toggles = [
        { toggle: 'buildMatchingToggle', label: 'buildMatchingStatusLabel' },
        { toggle: 'mainMatchingToggle', label: 'mainMatchingStatusLabel' },
        { toggle: 'matchingActiveToggle', label: 'matchingStatusLabel' },
        { toggle: 'profileMatchToggle', label: 'profileMatchStatusLabel' },
        { toggle: 'settingsMatchingToggle', label: 'settingsMatchingStatus' }
    ];
    
    toggles.forEach(({ toggle, label }) => {
        const toggleEl = document.getElementById(toggle);
        const labelEl = document.getElementById(label);
        if (toggleEl) {
            toggleEl.checked = isActive;
        }
        if (labelEl) {
            labelEl.textContent = isActive ? 'Active' : 'Inactive';
            labelEl.className = isActive ? 'status-text active' : 'status-text inactive';
        }
    });
}

// Toggle main matching status from profile view
async function toggleMainMatchingStatus() {
    const isActive = document.getElementById('mainMatchingToggle').checked;
    const statusLabel = document.getElementById('mainMatchingStatusLabel');
    
    try {
        const response = await fetch(`${API_URL}/match/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ active: isActive })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusLabel.textContent = isActive ? 'Active' : 'Inactive';
            statusLabel.className = isActive ? 'status-text active' : 'status-text inactive';
            showToast(`Matching ${isActive ? 'activated' : 'deactivated'}`, 'success');
            syncAllToggles(isActive);
            loadMatchInProfile();
        } else {
            showToast(data.error || 'Failed to update status', 'error');
            document.getElementById('mainMatchingToggle').checked = !isActive;
        }
    } catch (error) {
        console.error('Error toggling status:', error);
        showToast('Connection error. Please try again.', 'error');
        document.getElementById('mainMatchingToggle').checked = !isActive;
    }
}

// Toggle matching status from profile view (secondary toggle in match section)
async function toggleMatchingStatusFromProfile() {
    const isActive = document.getElementById('profileMatchToggle').checked;
    const statusLabel = document.getElementById('profileMatchStatusLabel');
    
    try {
        const response = await fetch(`${API_URL}/match/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ active: isActive })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusLabel.textContent = isActive ? 'Active' : 'Inactive';
            statusLabel.className = isActive ? 'status-text active' : 'status-text inactive';
            showToast(`Matching ${isActive ? 'activated' : 'deactivated'}`, 'success');
            
            // Sync all toggles
            syncAllToggles(isActive);
        } else {
            showToast(data.error || 'Failed to update status', 'error');
            document.getElementById('profileMatchToggle').checked = !isActive;
        }
    } catch (error) {
        console.error('Error toggling status:', error);
        showToast('Connection error. Please try again.', 'error');
        document.getElementById('profileMatchToggle').checked = !isActive;
    }
}

// Load Settings
async function loadSettings() {
    if (!currentUser) return;
    
    // Load profile data
    try {
        const response = await fetch(`${API_URL}/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const profile = await response.json();
        
        if (response.ok) {
            document.getElementById('settingsEmail').textContent = profile.email || 'Unknown';
            document.getElementById('settingsMemberNum').textContent = '#' + (profile.member_number || '?');
            document.getElementById('settingsAccountType').textContent = profile.payment_status === 'free' ? 'Lifetime Free' : 'Standard';
            
            // Stats
            const dimensionsCount = Object.keys(profile.dimensions || {}).length;
            const percentage = Math.round((dimensionsCount / 29) * 100);
            document.getElementById('settingsCompletion').textContent = percentage + '%';
            document.getElementById('settingsDimensions').textContent = dimensionsCount + ' / 29';
            document.getElementById('settingsConversations').textContent = profile.conversation_count || 0;
            document.getElementById('settingsPhotos').textContent = (profile.photos ? profile.photos.length : 0) + ' / 3';
            
            // Matching
            const isActive = profile.matching_active !== false;
            const statusSpan = document.getElementById('settingsMatchingStatus');
            const toggle = document.getElementById('settingsMatchingToggle');
            
            toggle.checked = isActive;
            statusSpan.textContent = isActive ? 'Active' : 'Inactive';
            statusSpan.className = 'status-text ' + (isActive ? 'active' : 'inactive');
            
            document.getElementById('settingsCurrentMatch').textContent = profile.current_match_id ? '1 Match' : 'None';
            
            // Theme
            const savedTheme = localStorage.getItem('theme') || 'default';
            document.getElementById('themeSelector').value = savedTheme;
            applyTheme(savedTheme);
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Toggle Matching from Settings
async function toggleMatchingFromSettings() {
    const toggle = document.getElementById('settingsMatchingToggle');
    const statusSpan = document.getElementById('settingsMatchingStatus');
    const newStatus = toggle.checked;
    
    toggle.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/match/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ active: newStatus })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusSpan.textContent = newStatus ? 'Active' : 'Inactive';
            statusSpan.className = 'status-text ' + (newStatus ? 'active' : 'inactive');
            
            // Sync other toggles
            syncAllToggles(newStatus);
            
            showToast(`Matching ${newStatus ? 'activated' : 'paused'}`, 'success');
        } else {
            toggle.checked = !newStatus;
            showToast(data.error || 'Failed to update status', 'error');
        }
    } catch (error) {
        console.error('Error toggling status:', error);
        toggle.checked = !newStatus;
        showToast('Connection error', 'error');
    } finally {
        toggle.disabled = false;
    }
}

// Theme Management
function changeTheme(theme) {
    localStorage.setItem('theme', theme);
    applyTheme(theme);
}

function applyTheme(theme) {
    // Remove all theme classes
    document.body.classList.remove('theme-borland', 'theme-dark', 'theme-nature', 'theme-ocean');
    
    // Add selected theme class
    if (theme !== 'default') {
        document.body.classList.add(`theme-${theme}`);
    }
}

// Apply saved theme on load
const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    applyTheme(savedTheme);
}

// Photo Upload Handling
let selectedChatPhoto = null;

function triggerChatPhotoUpload() {
    document.getElementById('chatPhotoUploadInput').click();
}

function handleChatPhotoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    uploadPhoto(file);
}

async function uploadPhoto(file) {
    if (!file) return;
    
    // Show uploading state
    const btn = document.getElementById('chatPhotoUploadBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Uploading...';
    
    const formData = new FormData();
    formData.append('photo', file);
    
    try {
        const response = await fetch(`${API_URL}/profile/photos`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Photo uploaded successfully!', 'success');
            renderPhotos(data.photos, 'chatPhotoGrid', 'chatPhotoUploadBtn');
        } else {
            showToast(data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        console.error('Photo upload error:', error);
        showToast('Upload connection error', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
        // Clear input
        document.getElementById('chatPhotoUploadInput').value = '';
    }
}

async function deletePhoto(photoUrl) {
    if (!confirm('Delete this photo?')) return;
    
    try {
        const response = await fetch(`${API_URL}/profile/photos`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ photo_url: photoUrl })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Photo deleted', 'success');
            renderPhotos(data.photos, 'chatPhotoGrid', 'chatPhotoUploadBtn');
        } else {
            showToast(data.error || 'Delete failed', 'error');
        }
    } catch (error) {
        console.error('Photo delete error:', error);
        showToast('Delete connection error', 'error');
    }
}

function renderPhotos(photos, gridId, uploadBtnId) {
    const grid = document.getElementById(gridId);
    if (!grid) return;
    
    grid.innerHTML = '';
    
    // Render existing photos
    photos.forEach(url => {
        const div = document.createElement('div');
        div.className = 'photo-item';
        div.innerHTML = `
            <img src="${url}" alt="Profile Photo">
            <button class="photo-delete-btn" onclick="deletePhoto('${url}')">×</button>
        `;
        grid.appendChild(div);
    });
    
    // Render placeholders
    const placeholdersNeeded = 3 - photos.length;
    for (let i = 0; i < placeholdersNeeded; i++) {
        const div = document.createElement('div');
        div.className = 'photo-item photo-item-empty';
        div.innerHTML = '<span>+</span>';
        grid.appendChild(div);
    }
    
    // Disable upload if full
    const btn = document.getElementById(uploadBtnId);
    if (btn) {
        if (photos.length >= 3) {
            btn.disabled = true;
            btn.title = 'Maximum 3 photos allowed';
        } else {
            btn.disabled = false;
            btn.title = '';
        }
    }
}

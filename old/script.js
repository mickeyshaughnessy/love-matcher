const API_URL = 'http://localhost:42069/api';
let currentUser = null;
let currentMatch = null;

// API Calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) options.body = JSON.stringify(data);
    const response = await fetch(`${API_URL}${endpoint}`, options);
    if (!response.ok) throw new Error(await response.text());
    return response.json();
}

// Profile Management
async function loadProfile() {
    try {
        const profile = await apiCall(`/profiles/${currentUser}`);
        document.getElementById('name').value = profile.name;
        document.getElementById('age').value = profile.age;
        document.getElementById('location').value = profile.location;
        
        const interestsList = document.querySelector('.interests-list');
        interestsList.innerHTML = '';
        profile.preferences.interests.forEach(interest => {
            const tag = document.createElement('span');
            tag.className = 'interest-tag';
            tag.textContent = interest;
            interestsList.appendChild(tag);
        });
        interestsList.appendChild(createAddInterestTag());
        
        document.getElementById('max-age').value = profile.preferences.max_age_difference;
        document.getElementById('goal').value = profile.preferences.relationship_goal;
        document.getElementById('education').value = profile.preferences.education_level;
    } catch (err) {
        console.error('Error loading profile:', err);
    }
}

async function saveProfile(e) {
    e.preventDefault();
    const formData = {
        name: document.getElementById('name').value,
        age: parseInt(document.getElementById('age').value),
        location: document.getElementById('location').value,
        preferences: {
            interests: Array.from(document.querySelectorAll('.interest-tag'))
                .map(tag => tag.textContent)
                .filter(text => text !== '+ Add Interest'),
            max_age_difference: parseInt(document.getElementById('max-age').value),
            relationship_goal: document.getElementById('goal').value,
            education_level: document.getElementById('education').value
        }
    };
    try {
        await apiCall('/profiles', 'POST', formData);
        loadProfile();
    } catch (err) {
        console.error('Error saving profile:', err);
    }
}

// Match Management
async function loadCurrentMatch() {
    try {
        const matches = await apiCall(`/matches/${currentUser}`);
        const matchInfo = document.getElementById('match-info');
        
        if (matches && matches.length > 0) {
            currentMatch = matches[0];
            matchInfo.innerHTML = `
                <span class="match-score">${currentMatch.match_score}% Match</span>
                <h3>${currentMatch.name}, ${currentMatch.age}</h3>
                <p>${currentMatch.location} • ${currentMatch.preferences.relationship_goal} • ${currentMatch.preferences.education_level}</p>
                <p>${currentMatch.preferences.interests.length} common interests: ${currentMatch.preferences.interests.join(', ')}</p>
            `;
            loadMessages();
        } else {
            matchInfo.innerHTML = '<p>No current match available.</p>';
        }
    } catch (err) {
        console.error('Error loading match:', err);
    }
}

// Messaging
async function loadMessages() {
    if (!currentMatch) return;
    try {
        const messages = await apiCall(`/messages/${currentMatch.id}`);
        const container = document.getElementById('match-messages');
        container.innerHTML = '';
        messages.forEach(msg => {
            const div = document.createElement('div');
            div.className = `message ${msg.from_user_id === currentUser ? 'sent' : 'received'}`;
            div.textContent = msg.content;
            container.appendChild(div);
        });
        container.scrollTop = container.scrollHeight;
    } catch (err) {
        console.error('Error loading messages:', err);
    }
}

async function sendMessage(e) {
    e.preventDefault();
    if (!currentMatch) return;
    
    const input = e.target.querySelector('input');
    const content = input.value.trim();
    if (!content) return;
    
    try {
        await apiCall('/messages', 'POST', {
            from: currentUser,
            to: currentMatch.id,
            content
        });
        input.value = '';
        loadMessages();
    } catch (err) {
        console.error('Error sending message:', err);
    }
}

// Stats
async function loadStats() {
    try {
        const stats = await apiCall(`/users/${currentUser}/stats`);
        const container = document.getElementById('user-stats');
        container.innerHTML = `
            <div>
                <h3>Profile</h3>
                <p>Profile Completeness: ${stats.profile_completeness}%</p>
                <p>Active Since: ${new Date(stats.active_since).toLocaleDateString()}</p>
            </div>
            <div>
                <h3>Matching</h3>
                <p>Total Matches: ${stats.total_matches}</p>
                <p>Response Rate: ${stats.response_rate}%</p>
            </div>
        `;
    } catch (err) {
        console.error('Error loading stats:', err);
    }
}

// Love Matcher Chat
async function handleLoveMatcherChat(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const content = input.value.trim();
    if (!content) return;

    const messages = document.getElementById('chat-messages');
    const userMsg = document.createElement('div');
    userMsg.className = 'message sent';
    userMsg.textContent = content;
    messages.appendChild(userMsg);
    input.value = '';

    // Simulate bot response
    setTimeout(() => {
        const botMsg = document.createElement('div');
        botMsg.className = 'message received';
        botMsg.textContent = "I'm here to help! Let me know what questions you have about Love Matcher.";
        messages.appendChild(botMsg);
        messages.scrollTop = messages.scrollHeight;
    }, 1000);
}

// Event Listeners
document.getElementById('profile-form').addEventListener('submit', saveProfile);
document.getElementById('match-chat-form').addEventListener('submit', sendMessage);
document.getElementById('chat-form').addEventListener('submit', handleLoveMatcherChat);

// Initialize
document.querySelector('.login-button').addEventListener('click', async () => {
    // Simulated login for now
    currentUser = 'test-user-id';
    await Promise.all([
        loadProfile(),
        loadCurrentMatch(),
        loadStats()
    ]);
});

// Interest tag management
function createAddInterestTag() {
    const tag = document.createElement('span');
    tag.className = 'interest-tag';
    tag.textContent = '+ Add Interest';
    tag.addEventListener('click', () => {
        const interest = prompt('Enter new interest:');
        if (interest && interest.trim()) {
            const newTag = document.createElement('span');
            newTag.className = 'interest-tag';
            newTag.textContent = interest.trim();
            tag.parentElement.insertBefore(newTag, tag);
        }
    });
    return tag;
}
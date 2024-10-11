const API_URL = 'https://api.love-matcher.com';
const clerk = window.Clerk;

async function initializeClerk() {
    await clerk.load({
        frontendApi: 'YOUR_FRONTEND_API_KEY'
    });

    const userStatus = document.getElementById('user-status');
    const loginContainer = document.getElementById('login-container');
    const content = document.getElementById('content');

    if (clerk.user) {
        userStatus.textContent = `Logged in as: ${clerk.user.firstName}`;
        content.style.display = 'block';
        loginContainer.style.display = 'none';
    } else {
        userStatus.textContent = 'Not logged in';
        content.style.display = 'none';
        loginContainer.style.display = 'block';
        const signInBtn = clerk.mountSignIn(loginContainer);
    }

    clerk.addListener(({ user }) => {
        if (user) {
            userStatus.textContent = `Logged in as: ${user.firstName}`;
            content.style.display = 'block';
            loginContainer.style.display = 'none';
        } else {
            userStatus.textContent = 'Not logged in';
            content.style.display = 'none';
            loginContainer.style.display = 'block';
        }
    });
}

async function pingServer() {
    const pingResult = document.getElementById('ping-result');
    try {
        const response = await fetch(`${API_URL}/ping`, {
            headers: {
                'Authorization': `Bearer ${await clerk.session.getToken()}`
            }
        });
        const data = await response.json();
        pingResult.textContent = `Server response: ${data.message}`;
    } catch (error) {
        pingResult.textContent = `Error: ${error.message}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeClerk();
    const pingBtn = document.getElementById('ping-btn');
    pingBtn.addEventListener('click', pingServer);
});
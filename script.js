const API_URL = 'http://localhost:5000'; // Update if your backend runs on a different host or port
const clerk = window.Clerk;

async function initializeClerk() {
    await clerk.load({
        frontendApi: 'pk_test_d2VsbC1iaXNvbi0zNi5jbGVyay5hY2NvdW50cy5kZXYk' // Replace with your actual Clerk frontend API key
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
        const token = await clerk.session.getToken();
        const response = await fetch(`${API_URL}/ping`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await response.json();
        pingResult.textContent = `Server response: ${data.message}`;
    } catch (error) {
        pingResult.textContent = `Error: ${error.message}`;
    }
}

function initializeThemeSwitcher() {
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        themeSelect.addEventListener('change', function() {
            const themeLink = document.getElementById('theme-style');
            if (themeLink) {
                themeLink.href = this.value + '.css';
            }
        });
    }
}

function initializeContactForm() {
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', function(event) {
            event.preventDefault();
            // Here you would typically send the form data to your server
            alert('Message sent successfully!');
            this.reset();
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeClerk();
    initializeThemeSwitcher();
    initializeContactForm();

    const pingBtn = document.getElementById('ping-btn');
    if (pingBtn) {
        pingBtn.addEventListener('click', pingServer);
    }
});
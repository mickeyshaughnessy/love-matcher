import { loadStripe } from '@stripe/stripe-js';

const stripePromise = loadStripe('your-publishable-key');

export const initializePayment = async () => {
    const stripe = await stripePromise;
    const elements = stripe.elements();

    // Create card element
    const card = elements.create('card', {
        style: {
            base: {
                color: '#fff',
                fontFamily: 'system-ui, -apple-system, sans-serif',
                fontSize: '16px',
                '::placeholder': {
                    color: '#aab7c4'
                },
            },
            invalid: {
                color: '#fa755a',
                iconColor: '#fa755a'
            }
        }
    });

    // Mount card element
    card.mount('#card-element');

    return { stripe, card };
};

export const handlePayment = async (clerkUser) => {
    try {
        const stripe = await stripePromise;
        
        // Create payment intent
        const response = await fetch('/api/create-payment-intent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${await clerkUser.getToken()}`
            },
            body: JSON.stringify({
                amount: 15000, // $150.00
                currency: 'usd'
            })
        });

        const { clientSecret } = await response.json();

        // Show Stripe payment form
        const result = await stripe.confirmCardPayment(clientSecret, {
            payment_method: {
                card: elements.getElement('card'),
                billing_details: {
                    email: clerkUser.emailAddress
                }
            }
        });

        if (result.error) {
            throw new Error(result.error.message);
        }
        
        // Payment successful
        await activateUserAccount(clerkUser.id);
        window.location.href = '/dashboard';
        
    } catch (error) {
        console.error('Payment failed:', error);
        showError(error.message || 'Payment failed. Please try again.');
    }
};

const showError = (message) => {
    const errorDiv = document.getElementById('payment-error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
};

const activateUserAccount = async (userId) => {
    await fetch('/api/activate-account', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${await clerkUser.getToken()}`
        },
        body: JSON.stringify({ userId })
    });
};
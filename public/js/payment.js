// Initialize Stripe - replace with your actual public key
const stripe = Stripe('pk_live_yBS40NcWxb5MwmtJq3yhUxUU');

export async function initializePayment() {
    const { error } = await stripe.redirectToCheckout({
        items: [{
            product: 'prod_R92mKzdvXQKc9N',
            quantity: 1
        }],
        mode: 'payment',
        successUrl: window.location.origin + '/dashboard',
        cancelUrl: window.location.origin
    });

    if (error) {
        const errorElement = document.getElementById('payment-error');
        errorElement.textContent = error.message;
        errorElement.classList.remove('hidden');
    }
}

export async function handlePayment(user) {
    const submitButton = document.getElementById('submit-payment');
    submitButton.disabled = true;
    submitButton.textContent = 'Redirecting to payment...';
    
    try {
        const session = await stripe.redirectToCheckout({
            items: [{
                product: 'prod_R92mKzdvXQKc9N',
                quantity: 1
            }],
            mode: 'payment',
            successUrl: `${window.location.origin}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
            cancelUrl: window.location.origin,
            customerEmail: user.emailAddress
        });

        if (session.error) {
            throw new Error(session.error.message);
        }

    } catch (err) {
        const errorElement = document.getElementById('payment-error');
        errorElement.textContent = err.message;
        errorElement.classList.remove('hidden');
        submitButton.disabled = false;
        submitButton.textContent = 'Pay $150 and Join';
    }
}

"""
🤔 Payment Module - Simple Stripe checkout with product ID
"""

const stripe = Stripe('pk_test_TYooMQauvdEDq54NiTphI7jx');

export async function initializePayment() {
    console.log('Starting payment...');
    return stripe;
}

export async function handlePayment(user) {
    console.log('Processing payment:', user?.emailAddress);
    
    const button = document.querySelector('#submit-payment');
    button.disabled = true;
    button.textContent = 'Processing...';
    
    try {
        const { error } = await stripe.redirectToCheckout({
            items: [{ product: 'prod_R92mKzdvXQKc9N', quantity: 1 }],
            mode: 'payment',
            successUrl: `${window.location.origin}/success`,
            cancelUrl: `${window.location.origin}/cancel`,
            customerEmail: user?.emailAddress
        });

        if (error) throw error;
        
    } catch (err) {
        console.error('Payment failed:', err);
        const errorDiv = document.querySelector('#payment-error');
        errorDiv.textContent = err.message;
        errorDiv.classList.remove('hidden');
        button.disabled = false;
        button.textContent = 'Try Payment Again';
    }
}
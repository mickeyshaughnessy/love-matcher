const stripe = Stripe('pk_test_TYooMQauvdEDq54NiTphI7jx');

export async function handlePayment(user) {
    console.log('Processing payment:', user?.email);
    
    const button = document.querySelector('#submit-payment');
    button.disabled = true;
    button.textContent = 'Processing...';
    
    try {
        const { error } = await stripe.redirectToCheckout({
            lineItems: [{ price: 'price_1QQnfiP3RiwFKPqfhXg4c7n3', quantity: 1 }],
            mode: 'payment',
            successUrl: `${window.location.origin}/success.html`,
            cancelUrl: `${window.location.origin}/cancel.html`,
            customerEmail: user?.email
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
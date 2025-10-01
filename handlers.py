from flask import request, jsonify
from functools import wraps
import jwt
from datetime import datetime, timedelta
import json
import requests

# Global variables to be set by api_server
s3_client = None
S3_BUCKET = None
S3_PREFIX = None
jwt_secret = None
openrouter_config = None  # Will hold OpenRouter configuration

# Constants
FIRST_10K_FREE_LIMIT = 10000
MEMBER_LIST_KEY = "member_list.json"

# System prompt for the matchmaking AI
SYSTEM_PROMPT = """You are a professional AI matchmaker for LoveDashMatcher, a service that helps people find compatible partners for lasting relationships. Your role is to:

1. Learn about the user through natural conversation
2. Understand their values, goals, interests, and what they're looking for in a partner
3. Assess compatibility across 29 dimensions including: communication style, family values, lifestyle preferences, career ambitions, emotional intelligence, conflict resolution, financial attitudes, religious/spiritual views, parenting philosophy, social preferences, and more
4. Be warm, empathetic, and professional
5. Ask thoughtful follow-up questions to deeply understand the user
6. Provide insights and guidance about relationships and compatibility

Keep your responses conversational and engaging. Make the user feel heard and understood. Be encouraging and positive while remaining honest and realistic about relationship dynamics."""

# JWT decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            request.user_id = data['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

# Helper functions
def s3_get(key):
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}{key}")
        return json.loads(response['Body'].read())
    except:
        return None

def s3_put(key, data):
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_PREFIX}{key}",
        Body=json.dumps(data),
        ContentType='application/json'
    )

def get_member_count():
    """Get current member count from S3"""
    member_list = s3_get(MEMBER_LIST_KEY)
    if not member_list:
        return 0
    return len(member_list.get('members', []))

def add_to_member_list(user_id, email, age, registration_time):
    """Add new member to the member list and return member number"""
    member_list = s3_get(MEMBER_LIST_KEY) or {'members': [], 'created_at': datetime.utcnow().isoformat()}
    
    member_number = len(member_list['members']) + 1
    
    new_member = {
        'member_number': member_number,
        'user_id': user_id,
        'email': email,
        'age': age,
        'registration_time': registration_time,
        'is_free': member_number <= FIRST_10K_FREE_LIMIT
    }
    
    member_list['members'].append(new_member)
    member_list['updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(MEMBER_LIST_KEY, member_list)
    return member_number

def is_member_free(member_number):
    """Check if member gets free access based on signup order"""
    return member_number <= FIRST_10K_FREE_LIMIT

def call_openrouter_llm(messages):
    """Call OpenRouter API with Grok model"""
    try:
        headers = {
            'Authorization': f"Bearer {openrouter_config['api_key']}",
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://lovedashmatcher.com',  # Optional but recommended
            'X-Title': 'LoveDashMatcher'  # Optional but recommended
        }
        
        payload = {
            'model': openrouter_config['model'],
            'messages': messages,
            'temperature': openrouter_config['temperature'],
            'max_tokens': openrouter_config['max_tokens']
        }
        
        response = requests.post(
            openrouter_config['api_url'],
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # OpenRouter returns choices array with message content
        if 'choices' in result and len(result['choices']) > 0:
            return {
                'content': result['choices'][0]['message']['content'],
                'model': result.get('model', openrouter_config['model']),
                'usage': result.get('usage', {})
            }
        else:
            print(f"Unexpected OpenRouter response format: {result}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"OpenRouter API error: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error calling OpenRouter: {e}")
        return None

def build_profile_context(profile):
    """Build context string from user profile for LLM"""
    context_parts = []
    
    if profile.get('age'):
        context_parts.append(f"Age: {profile['age']}")
    
    if profile.get('dimensions'):
        context_parts.append("\nUser Profile Information:")
        for key, value in profile['dimensions'].items():
            context_parts.append(f"- {key}: {value}")
    
    member_number = profile.get('member_number')
    if member_number:
        context_parts.append(f"\nMember #: {member_number}")
    
    if profile.get('is_free_member'):
        context_parts.append("Status: Free lifetime member")
    
    if context_parts:
        return "\n".join(context_parts)
    return "New user - profile being built"

# Route handlers
def ping():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    age = data.get('age')
    
    if not all([email, password, age]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Allow registration for all ages, but note matching eligibility
    age_int = int(age)
    matching_eligible = age_int >= 18
    
    # Check if user exists
    user_id = email.replace('@', '_').replace('.', '_')
    if s3_get(f"profiles/{user_id}.json"):
        return jsonify({'error': 'User already exists'}), 400
    
    # Add to member list and get member number
    registration_time = datetime.utcnow().isoformat()
    member_number = add_to_member_list(user_id, email, age_int, registration_time)
    is_free = is_member_free(member_number)
    
    # Determine payment status
    if is_free:
        payment_status = 'free' if matching_eligible else 'free_pending_age'
    else:
        payment_status = 'payment_required'
    
    # Create user profile
    profile = {
        'user_id': user_id,
        'email': email,
        'age': age_int,
        'member_number': member_number,
        'created_at': registration_time,
        'payment_status': payment_status,
        'matching_eligible': matching_eligible,
        'profile_complete': False,
        'dimensions': {},
        'is_free_member': is_free
    }
    
    s3_put(f"profiles/{user_id}.json", profile)
    
    # Generate token
    token = jwt.encode(
        {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=1)},
        jwt_secret,
        algorithm='HS256'
    )
    
    response_data = {
        'token': token, 
        'user_id': user_id,
        'member_number': member_number,
        'matching_eligible': matching_eligible,
        'is_free_member': is_free
    }
    
    # Add appropriate message based on status
    if not matching_eligible:
        response_data['message'] = "Account created! You can explore the service and chat with our AI. Matching will be available when you turn 18."
    elif is_free:
        response_data['message'] = f"Welcome! You're member #{member_number} and get free lifetime access to LoveDashMatcher!"
    else:
        response_data['message'] = f"Welcome! You're member #{member_number}. Payment is required to access matching services."
    
    return jsonify(response_data)

def login():
    data = request.json
    email = data.get('email')
    user_id = email.replace('@', '_').replace('.', '_')
    
    profile = s3_get(f"profiles/{user_id}.json")
    if not profile:
        return jsonify({'error': 'User not found'}), 404
    
    token = jwt.encode(
        {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=1)},
        jwt_secret,
        algorithm='HS256'
    )
    
    return jsonify({'token': token, 'user_id': user_id})

@token_required
def get_profile():
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    return jsonify(profile)

@token_required
def update_profile():
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    data = request.json
    
    # If user is updating age and becomes 18+, update matching eligibility
    if 'age' in data:
        new_age = int(data['age'])
        if new_age >= 18 and not profile.get('matching_eligible', False):
            profile['matching_eligible'] = True
            # Update payment status if they're a free member
            if profile.get('is_free_member', False):
                profile['payment_status'] = 'free'
    
    profile.update(data)
    profile['updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(f"profiles/{request.user_id}.json", profile)
    return jsonify(profile)

@token_required
def chat():
    """Chat endpoint with OpenRouter LLM integration"""
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Load user profile
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    # Load chat history
    history_key = f"chat/{request.user_id}_history.json"
    chat_history = s3_get(history_key) or {'messages': [], 'created_at': datetime.utcnow().isoformat()}
    
    # Build profile context for system message
    profile_context = build_profile_context(profile)
    
    # Construct messages for LLM
    messages = [
        {
            'role': 'system',
            'content': f"{SYSTEM_PROMPT}\n\nCurrent User Context:\n{profile_context}"
        }
    ]
    
    # Add conversation history (last 20 exchanges to keep context manageable)
    recent_messages = chat_history['messages'][-40:] if chat_history['messages'] else []
    for msg in recent_messages:
        messages.append({'role': 'user', 'content': msg['user']})
        messages.append({'role': 'assistant', 'content': msg['ai']})
    
    # Add current user message
    messages.append({'role': 'user', 'content': user_message})
    
    # Call OpenRouter LLM
    llm_response = call_openrouter_llm(messages)
    
    if not llm_response or 'content' not in llm_response:
        ai_response = "I'm sorry, I'm having trouble processing that right now. Could you try again?"
    else:
        ai_response = llm_response['content']
    
    # Store in chat history
    chat_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'user': user_message,
        'ai': ai_response
    }
    
    # Add model info if available
    if llm_response:
        chat_entry['model'] = llm_response.get('model', 'unknown')
        chat_entry['usage'] = llm_response.get('usage', {})
    
    chat_history['messages'].append(chat_entry)
    chat_history['updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(history_key, chat_history)
    
    return jsonify({
        'response': ai_response,
        'timestamp': chat_entry['timestamp']
    })

@token_required
def get_chat_history():
    """Get user's chat history"""
    history_key = f"chat/{request.user_id}_history.json"
    chat_history = s3_get(history_key) or {'messages': [], 'created_at': datetime.utcnow().isoformat()}
    
    return jsonify({
        'messages': chat_history.get('messages', []),
        'total_messages': len(chat_history.get('messages', []))
    })

@token_required
def get_matches():
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    # Check if user is eligible for matching
    if not profile.get('matching_eligible', False):
        return jsonify({
            'matches': [],
            'message': 'Matching will be available when you turn 18. Keep building your profile!'
        })
    
    # Check payment status
    payment_status = profile.get('payment_status', 'payment_required')
    if payment_status not in ['free', 'completed']:
        return jsonify({
            'matches': [],
            'message': 'Payment required to access matching services. Please complete your payment to continue.',
            'payment_required': True
        })
    
    # Get matches (placeholder for now)
    matches = s3_get(f"matches/{request.user_id}_matches.json") or []
    return jsonify({'matches': matches})

@token_required
def initiate_payment():
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    # Check if user is a free member
    if profile.get('is_free_member', False):
        return jsonify({
            'error': 'You have free lifetime access - no payment required!',
            'member_number': profile.get('member_number'),
            'is_free_member': True
        }), 400
    
    # Placeholder for XMoney integration
    return jsonify({
        'payment_url': 'https://xmoney.example.com/pay/placeholder',
        'amount': 49.99,
        'currency': 'USD',
        'member_number': profile.get('member_number')
    })

@token_required
def get_member_stats():
    """Get membership statistics"""
    member_list = s3_get(MEMBER_LIST_KEY)
    if not member_list:
        return jsonify({
            'total_members': 0,
            'free_members': 0,
            'paid_members': 0,
            'spots_remaining': FIRST_10K_FREE_LIMIT
        })
    
    members = member_list.get('members', [])
    total_members = len(members)
    free_members = sum(1 for m in members if m.get('is_free', False))
    paid_members = total_members - free_members
    spots_remaining = max(0, FIRST_10K_FREE_LIMIT - total_members)
    
    return jsonify({
        'total_members': total_members,
        'free_members': free_members,
        'paid_members': paid_members,
        'spots_remaining': spots_remaining,
        'free_limit': FIRST_10K_FREE_LIMIT
    })

# Register all routes with the Flask app
def register_routes(app, s3_client_instance, s3_bucket, s3_prefix, openrouter_cfg):
    global s3_client, S3_BUCKET, S3_PREFIX, jwt_secret, openrouter_config
    s3_client = s3_client_instance
    S3_BUCKET = s3_bucket
    S3_PREFIX = s3_prefix
    jwt_secret = app.config['JWT_SECRET']
    openrouter_config = openrouter_cfg
    
    app.add_url_rule('/ping', 'ping', ping, methods=['GET'])
    app.add_url_rule('/register', 'register', register, methods=['POST'])
    app.add_url_rule('/login', 'login', login, methods=['POST'])
    app.add_url_rule('/profile', 'get_profile', get_profile, methods=['GET'])
    app.add_url_rule('/profile', 'update_profile', update_profile, methods=['PUT'])
    app.add_url_rule('/chat', 'chat', chat, methods=['POST'])
    app.add_url_rule('/chat/history', 'get_chat_history', get_chat_history, methods=['GET'])
    app.add_url_rule('/matches', 'get_matches', get_matches, methods=['GET'])
    app.add_url_rule('/payment/initiate', 'initiate_payment', initiate_payment, methods=['POST'])
    app.add_url_rule('/stats', 'get_member_stats', get_member_stats, methods=['GET'])
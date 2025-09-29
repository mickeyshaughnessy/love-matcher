from flask import request, jsonify
from functools import wraps
import jwt
from datetime import datetime, timedelta
import json

# Global variables to be set by api_server
s3_client = None
S3_BUCKET = None
S3_PREFIX = None
jwt_secret = None

# Constants
FIRST_10K_FREE_LIMIT = 10000
MEMBER_LIST_KEY = "member_list.json"

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
    # Simplified chat endpoint - integrate OpenAI later
    message = request.json.get('message')
    
    # Store chat history
    history_key = f"profiles/{request.user_id}_history.json"
    history = s3_get(history_key) or []
    history.append({
        'timestamp': datetime.utcnow().isoformat(),
        'user': message,
        'ai': 'This is a placeholder response. OpenAI integration coming soon!'
    })
    s3_put(history_key, history)
    
    return jsonify({'response': 'Thanks for sharing! Tell me more about that.'})

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
    """New endpoint to get membership statistics"""
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
def register_routes(app, s3_client_instance, s3_bucket, s3_prefix):
    global s3_client, S3_BUCKET, S3_PREFIX, jwt_secret
    s3_client = s3_client_instance
    S3_BUCKET = s3_bucket
    S3_PREFIX = s3_prefix
    jwt_secret = app.config['JWT_SECRET']
    
    app.add_url_rule('/api/ping', 'ping', ping, methods=['GET'])
    app.add_url_rule('/api/register', 'register', register, methods=['POST'])
    app.add_url_rule('/api/login', 'login', login, methods=['POST'])
    app.add_url_rule('/api/profile', 'get_profile', get_profile, methods=['GET'])
    app.add_url_rule('/api/profile', 'update_profile', update_profile, methods=['PUT'])
    app.add_url_rule('/api/chat', 'chat', chat, methods=['POST'])
    app.add_url_rule('/api/matches', 'get_matches', get_matches, methods=['GET'])
    app.add_url_rule('/api/payment/initiate', 'initiate_payment', initiate_payment, methods=['POST'])
    app.add_url_rule('/api/stats', 'get_member_stats', get_member_stats, methods=['GET'])
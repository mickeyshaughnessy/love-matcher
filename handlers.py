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
    
    if int(age) < 18:
        return jsonify({'error': 'Must be 18 or older'}), 400
    
    # Check if user exists
    user_id = email.replace('@', '_').replace('.', '_')
    if s3_get(f"profiles/{user_id}.json"):
        return jsonify({'error': 'User already exists'}), 400
    
    # Create user profile
    profile = {
        'user_id': user_id,
        'email': email,
        'age': age,
        'created_at': datetime.utcnow().isoformat(),
        'payment_status': 'pending',
        'profile_complete': False,
        'dimensions': {}
    }
    
    s3_put(f"profiles/{user_id}.json", profile)
    
    # Generate token
    token = jwt.encode(
        {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=1)},
        jwt_secret,
        algorithm='HS256'
    )
    
    return jsonify({'token': token, 'user_id': user_id})

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
    matches = s3_get(f"matches/{request.user_id}_matches.json") or []
    return jsonify({'matches': matches})

@token_required
def initiate_payment():
    # Placeholder for XMoney integration
    return jsonify({
        'payment_url': 'https://xmoney.example.com/pay/placeholder',
        'amount': 49.99,
        'currency': 'USD'
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
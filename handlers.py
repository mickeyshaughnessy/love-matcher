"""
🤔 Love Matcher API Handlers
Updated for:
- User registration
- Profile CRUD
- Unified chat
- Better validation
"""
import logging, time, json, bcrypt
from datetime import datetime, timedelta
from flask import jsonify, request
from models import User, Match, Message

logger = logging.getLogger(__name__)

def is_test_request():
    return request.headers.get('X-Test-Channel') == 'true'

def handle_monitor(redis_client):
    try:
        now = datetime.now()
        start = time.perf_counter()
        prefix = 'love:test:' if is_test_request() else 'love:'
        
        pipe = redis_client.pipeline()
        pipe.hgetall(f'{prefix}users')
        pipe.hgetall(f'{prefix}matches')
        pipe.hgetall(f'{prefix}messages')
        users_raw, matches_raw, messages_raw = pipe.execute()
        
        users = [User.from_dict(u) for u in users_raw.values()]
        matches = [Match.from_dict(m) for m in matches_raw.values()]
        messages = [Message.from_dict(m) for m in messages_raw.values()]

        active_24h = sum(1 for u in users if u.last_active and now - u.last_active < timedelta(hours=24))
        messages_1h = sum(1 for m in messages if now - m.created_at < timedelta(hours=1))
        success_rate = sum(1 for m in matches if m.status == 'accepted') / max(len(matches), 1) * 100

        response_time = (time.perf_counter() - start) * 1000

        return jsonify({
            'status': 'ok',
            'timestamp': int(time.time()),
            'metrics': {
                'users': {
                    'total': len(users),
                    'active_24h': active_24h,
                    'signup_rate': len([u for u in users if now - u.created_at < timedelta(hours=24)])
                },
                'matches': {
                    'total': len(matches),
                    'success_rate': round(success_rate, 1),
                    'pending': sum(1 for m in matches if m.status == 'pending')
                },
                'messages': {
                    'total': len(messages),
                    'last_hour': messages_1h,
                    'avg_length': sum(len(m.content) for m in messages) / max(len(messages), 1)
                }
            },
            'health': {
                'redis_connected': bool(redis_client.ping()),
                'response_time_ms': round(response_time, 2),
                'memory_used': redis_client.info()['used_memory_human']
            }
        })
    except Exception as e:
        logger.error(f'Monitor failed: {e}')
        return jsonify({'status': 'error', 'error': str(e)}), 500

def handle_register(redis_client):
    data = request.json
    if not data or not all(k in data for k in ['email', 'password', 'name', 'age']):
        return jsonify({'error': 'Missing required fields'}), 400
        
    # Validate email not taken
    existing = redis_client.hget('love:users:emails', data['email'])
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # Hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(data['password'].encode(), salt)
    
    # Create user
    user = User(
        email=data['email'],
        name=data['name'],
        age=data['age'],
        password_hash=hashed.decode(),
        is_test=is_test_request()
    )
    user.save(redis_client)
    
    # Store email lookup
    redis_client.hset('love:users:emails', data['email'], user.id)
    
    # Generate JWT
    token = jwt.encode(
        {'user_id': user.id, 'exp': datetime.utcnow() + timedelta(days=30)},
        current_app.config['JWT_SECRET']
    )
    
    return jsonify({
        'user_id': user.id,
        'token': token,
        'status': 'active'
    })

def handle_get_profile(redis_client, user_id):
    user = User.get(redis_client, user_id)
    if not user or is_test_request() != user.is_test:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())

def handle_update_profile(redis_client, user_id):
    user = User.get(redis_client, user_id)
    if not user or is_test_request() != user.is_test:
        return jsonify({'error': 'User not found'}), 404
        
    data = request.json
    if not data:
        return jsonify({'error': 'No update data'}), 400
        
    # Don't allow email/password updates here
    data.pop('email', None)
    data.pop('password', None)
        
    user.update(redis_client, data)
    return jsonify({'message': 'Profile updated successfully'})

def handle_delete_profile(redis_client, user_id):
    user = User.get(redis_client, user_id)
    if not user or is_test_request() != user.is_test:
        return jsonify({'error': 'User not found'}), 404

    # Delete all user data
    prefix = 'love:test:' if user.is_test else 'love:'
    pipe = redis_client.pipeline()
    
    # Delete profile
    pipe.hdel(f'{prefix}users', user.id)
    pipe.hdel('love:users:emails', user.email)
    
    # Delete matches
    matches = Match.get_user_matches(redis_client, user.id)
    for match in matches:
        pipe.hdel(f'{prefix}matches', match.id)
    
    # Delete messages 
    messages = Message.get_user_messages(redis_client, user.id)
    for msg in messages:
        pipe.hdel(f'{prefix}messages', msg.id)
        
    pipe.execute()
    return jsonify({'message': 'Profile deleted successfully'})

def handle_send_message(redis_client):
    data = request.json
    if not data or 'to' not in data or 'content' not in data:
        return jsonify({'error': 'Invalid message data'}), 400
        
    # Validate both users exist
    sender = User.get(redis_client, request.user_id)
    recipient = User.get(redis_client, data['to'])
    
    if not sender or not recipient:
        return jsonify({'error': 'Invalid users'}), 404
        
    if sender.is_test != recipient.is_test:
        return jsonify({'error': 'Cannot message across test boundary'}), 400
    
    if is_test_request() != sender.is_test:
        return jsonify({'error': 'Invalid users'}), 404
    
    # Create message
    message = Message.create(
        redis_client,
        from_user_id=request.user_id,
        to_user_id=data['to'],
        content=data['content'],
        is_test=sender.is_test
    )
    return jsonify({
        'message_id': message.id,
        'status': 'sent',
        'timestamp': message.created_at.isoformat()
    })

def handle_get_messages(redis_client, user_id, other_id):
    user = User.get(redis_client, user_id)
    other = User.get(redis_client, other_id)
    
    if not user or not other or user.is_test != other.is_test:
        return jsonify({'error': 'Invalid users'}), 404
        
    if is_test_request() != user.is_test:
        return jsonify({'error': 'Invalid users'}), 404
        
    messages = Message.get_conversation_between(redis_client, user_id, other_id)
    return jsonify({
        'messages': [m.to_dict() for m in messages],
        'participants': {
            user_id: user.name,
            other_id: other.name
        }
    })
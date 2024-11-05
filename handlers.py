"""
🤔 Love Matcher API Handlers
Core business logic handlers split from routing
"""

import logging, time
from datetime import datetime, timedelta
from flask import jsonify, request
from models import User, Match, Message

logger = logging.getLogger(__name__)

def is_test_request():
    return request.headers.get('X-Test-Channel') == 'true'

import logging, time, json
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

        # Get all data in parallel
        pipe = redis_client.pipeline()
        pipe.hgetall(f'{prefix}users')
        pipe.hgetall(f'{prefix}matches')
        pipe.hgetall(f'{prefix}messages')
        users_raw, matches_raw, messages_raw = pipe.execute()
        
        # Parse raw data
        users = [User.from_dict(json.loads(u)) for u in users_raw.values()]
        matches = [Match.from_dict(json.loads(m)) for m in matches_raw.values()]
        messages = [Message.from_dict(json.loads(m)) for m in messages_raw.values()]

        # Calculate metrics
        active_24h = sum(1 for u in users if u.last_active and now - u.last_active < timedelta(hours=24))
        messages_1h = sum(1 for m in messages if now - m.created_at < timedelta(hours=1))
        success_rate = sum(1 for m in matches if m.status == 'accepted') / max(len(matches), 1) * 100

        # Response timing
        response_time = (time.perf_counter() - start) * 1000

        return jsonify({
            'status': 'ok',
            'timestamp': int(time.time()),
            'metrics': {
                'users': {
                    'total': len(users),
                    'active_24h': active_24h,
                    'signup_rate': sum(1 for u in users if now - u.created_at < timedelta(hours=24))
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

def handle_health_check(redis_client):
    try:
        metrics = {}
        if is_test_request():
            metrics = {
                'test_users': len(redis_client.hgetall('love:test:users')),
                'test_matches': len(redis_client.hgetall('love:test:matches'))
            }
        return jsonify({"status": "ok", "metrics": metrics})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error"}), 500

def handle_create_profile(redis_client):
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No profile data'}), 400
            
        required = ['name', 'age', 'preferences']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
            
        if is_test_request():
            data['is_test'] = True
            
        user = User(
            name=data['name'],
            age=data['age'],
            preferences=data['preferences'],
            is_test=data.get('is_test', False)
        )
        user.save(redis_client)
        return jsonify({'user_id': user.id, 'status': 'active'})
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Profile creation failed: {e}")
        return jsonify({'error': str(e)}), 500

def handle_get_profile(redis_client, user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user or is_test_request() != user.is_test:
            return jsonify({'error': 'User not found'}), 404
        return jsonify(user.to_dict())
    except Exception as e:
        logger.error(f"Profile fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

def handle_update_profile(redis_client, user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user or is_test_request() != user.is_test:
            return jsonify({'error': 'User not found'}), 404
            
        data = request.json
        if not data:
            return jsonify({'error': 'No update data'}), 400
            
        user.update(redis_client, data)
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        return jsonify({'error': str(e)}), 500

def handle_get_matches(redis_client, user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user or is_test_request() != user.is_test:
            return jsonify({'error': 'User not found'}), 404
            
        matches = Match.get_user_matches(redis_client, user_id, user.is_test)
        return jsonify({
            'matches': [{
                'user_id': m.target_id,
                'score': m.score,
                'profile': User.get(redis_client, m.target_id).to_dict()
            } for m in matches]
        })
    except Exception as e:
        logger.error(f"Match fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

def handle_match_outcome(redis_client, user_id):
    try:
        data = request.json
        if not data or 'match_id' not in data or 'outcome' not in data:
            return jsonify({'error': 'Invalid match outcome data'}), 400
            
        match = Match.get(redis_client, data['match_id'])
        if not match or is_test_request() != match.is_test:
            return jsonify({'error': 'Match not found'}), 404
            
        match.respond(redis_client, data['outcome'])
        return jsonify({'message': 'Match outcome recorded successfully'})
    except Exception as e:
        logger.error(f"Match outcome failed: {e}")
        return jsonify({'error': str(e)}), 500

def handle_send_message(redis_client):
    try:
        data = request.json
        if not data or not all(k in data for k in ['from', 'to', 'content']):
            return jsonify({'error': 'Invalid message data'}), 400
            
        from_user = User.get(redis_client, data['from'])
        to_user = User.get(redis_client, data['to'])
        
        if not from_user or not to_user or from_user.is_test != to_user.is_test:
            return jsonify({'error': 'Invalid users'}), 404
            
        if is_test_request() != from_user.is_test:
            return jsonify({'error': 'Invalid users'}), 404
            
        message = Message.create(
            redis_client,
            from_user_id=data['from'],
            to_user_id=data['to'],
            content=data['content'],
            is_test=from_user.is_test
        )
        return jsonify({'message': 'Message sent successfully'})
    except Exception as e:
        logger.error(f"Message send failed: {e}")
        return jsonify({'error': str(e)}), 500

def handle_get_messages(redis_client, user_id):
    try:
        other_id = request.args.get('other_user_id')
        if not other_id:
            return jsonify({'error': 'Missing other_user_id parameter'}), 400
            
        user = User.get(redis_client, user_id)
        other = User.get(redis_client, other_id)
        
        if not user or not other or user.is_test != other.is_test:
            return jsonify({'error': 'Invalid users'}), 404
            
        if is_test_request() != user.is_test:
            return jsonify({'error': 'Invalid users'}), 404
            
        messages = Message.get_conversation_between(redis_client, user_id, other_id)
        return jsonify([m.to_dict() for m in messages])
    except Exception as e:
        logger.error(f"Message fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

def handle_user_stats(redis_client, user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user or is_test_request() != user.is_test:
            return jsonify({'error': 'User not found'}), 404
            
        matches = Match.get_user_matches(redis_client, user_id, user.is_test)
        messages = Message.get_user_messages(redis_client, user_id)
        
        total_received = sum(1 for m in messages if m.to_user_id == user_id)
        total_responded = sum(1 for m in messages if m.from_user_id == user_id)
        
        return jsonify({
            'profile_completeness': user.calculate_completeness(),
            'active_since': user.created_at.isoformat(),
            'total_matches': len(matches),
            'response_rate': int((total_responded / max(total_received, 1)) * 100)
        })
    except Exception as e:
        logger.error(f"Stats fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

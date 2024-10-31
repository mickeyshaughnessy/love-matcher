"""
🤔 Love Matcher API Server with user stats and simplified endpoints
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os, logging, redis, time
from models import User, Match, Message
from utils import create_match

app = Flask(__name__)
CORS(app)

redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6378)),
    db=int(os.environ.get('REDIS_DB', 0)),
    decode_responses=True
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_test_request():
    return request.headers.get('X-Test-Channel') == 'true'

@app.route('/ping', methods=['GET'])
def ping():
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

@app.route('/api/users/<user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if is_test_request() != user.is_test:
            return jsonify({'error': 'User not found'}), 404
            
        stats = {
            'profile_completeness': user.calculate_completeness(),
            'active_since': user.created_at,
            'total_matches': len(Match.get_user_matches(redis_client, user_id, user.is_test)),
            'response_rate': calculate_response_rate(user_id),
            'is_test': user.is_test
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles', methods=['POST'])
def create_profile():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No profile data'}), 400
            
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

@app.route('/api/profiles/<user_id>', methods=['GET', 'PUT'])
def handle_profile(user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if is_test_request() != user.is_test:
            return jsonify({'error': 'Profile not found'}), 404
            
        if request.method == 'GET':
            return jsonify(user.to_dict())
            
        data = request.json
        if not data:
            return jsonify({'error': 'No update data'}), 400
            
        user.update(redis_client, data)
        return jsonify({'user': user.to_dict()})
    except Exception as e:
        logger.error(f"Profile operation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches/<user_id>', methods=['GET'])
def get_matches(user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if is_test_request() != user.is_test:
            return jsonify({'error': 'User not found'}), 404
            
        matches = Match.get_user_matches(redis_client, user_id, user.is_test)
        return jsonify([m.to_dict() for m in matches])
    except Exception as e:
        logger.error(f"Match fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/<match_id>', methods=['GET', 'POST'])
def handle_messages(match_id):
    try:
        match = Match.get(redis_client, match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404
            
        if is_test_request() != match.is_test:
            return jsonify({'error': 'Match not found'}), 404
            
        if request.method == 'GET':
            messages = Message.get_conversation(redis_client, match_id)
            return jsonify([m.to_dict() for m in messages])
            
        data = request.json
        if not data or 'content' not in data:
            return jsonify({'error': 'No message content'}), 400
            
        message = Message.create(
            redis_client,
            match_id=match_id,
            content=data['content'],
            is_test=match.is_test
        )
        return jsonify({'message_id': message.id})
    except Exception as e:
        logger.error(f"Message handling failed: {e}")
        return jsonify({'error': str(e)}), 500

def calculate_response_rate(user_id):
    messages = Message.get_user_messages(redis_client, user_id)
    if not messages:
        return 100
    
    total_received = sum(1 for m in messages if m.to_user_id == user_id)
    total_responded = sum(1 for m in messages if m.from_user_id == user_id)
    
    return int((total_responded / max(total_received, 1)) * 100)

if __name__ == '__main__':
    try:
        redis_client.ping()
        logger.info("Redis connection successful")
    except redis.ConnectionError:
        logger.error("Could not connect to Redis!")
        exit(1)
        
    app.run(host='0.0.0.0', port=42068, debug=True)

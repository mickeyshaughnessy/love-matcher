from flask import Flask, jsonify, request
from flask_redis import FlaskRedis
from flask_cors import CORS
import os, logging
from models import User, Match, Message
from utils import create_match

"""
🤔 Love Matcher API Server
- Test traffic isolation
- Clean data separation
- Common endpoint handling
<Flow>
1. Check test header
2. Use appropriate Redis keys
3. Keep data separate
4. Support cleanup
"""

app = Flask(__name__)
CORS(app)
app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6378')
redis_client = FlaskRedis(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_test_request():
    """Check if this is a test request"""
    return request.headers.get('X-Test-Channel') == 'true'

@app.route('/ping', methods=['GET'])
def ping():
    """Health check with optional metrics"""
    try:
        metrics = {}
        if is_test_request():
            metrics = {
                'test_users': len(redis_client.hgetall('love:test:users')),
                'test_matches': len(redis_client.hgetall('love:test:matches'))
            }
        return jsonify({
            "status": "ok",
            "metrics": metrics
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/api/test/cleanup', methods=['POST'])
def cleanup_test_data():
    """Clean up all test data - only works with test header"""
    if not is_test_request():
        return jsonify({'error': 'Not a test request'}), 403
        
    try:
        # Clear test data from Redis
        test_keys = [
            'love:test:users',
            'love:test:matches',
            'love:test:messages',
            'love:test:metrics'
        ]
        for key in test_keys:
            redis_client.delete(key)
        return jsonify({'message': 'Test data cleaned'})
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles', methods=['POST'])
def create_profile():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No profile data'}), 400
            
        # Mark test profiles
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

@app.route('/api/profiles/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Test data isolation
        if is_test_request() != user.is_test:
            return jsonify({'error': 'Profile not found'}), 404
            
        return jsonify(user.to_dict())
    except Exception as e:
        logger.error(f"Profile fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<user_id>', methods=['PUT']) 
def update_profile(user_id):
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No update data'}), 400
            
        user = User.get(redis_client, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Test data isolation
        if is_test_request() != user.is_test:
            return jsonify({'error': 'Profile not found'}), 404
            
        user.update(redis_client, data)
        return jsonify({'user': user.to_dict()})
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches/<user_id>', methods=['GET'])
def find_matches(user_id):
    try:
        user = User.get(redis_client, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Test data isolation
        if is_test_request() != user.is_test:
            return jsonify({'error': 'User not found'}), 404
            
        matches = Match.find_matches(redis_client, user_id)
        return jsonify({
            'status': 'success',
            'matches': [m.to_dict() for m in matches]
        })
    except Exception as e:
        logger.error(f"Match finding failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches/<user_id>/propose', methods=['POST'])
def propose_match(user_id):
    try:
        data = request.json
        if not data or 'target_id' not in data:
            return jsonify({'error': 'No target specified'}), 400
            
        user = User.get(redis_client, user_id)
        target = User.get(redis_client, data['target_id'])
        
        if not user or not target:
            return jsonify({'error': 'User not found'}), 404
            
        # Test data isolation
        if is_test_request() != user.is_test or user.is_test != target.is_test:
            return jsonify({'error': 'Cannot match across test boundary'}), 400
            
        match = Match.create(redis_client, user_id, data['target_id'])
        return jsonify({'match_id': match.id})
    except Exception as e:
        logger.error(f"Match proposal failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches/<match_id>/respond', methods=['POST'])
def respond_to_match(match_id):
    try:
        data = request.json
        if not data or 'response' not in data:
            return jsonify({'error': 'No response provided'}), 400
            
        match = Match.get(redis_client, match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404
            
        # Test data isolation
        if is_test_request() != match.is_test:
            return jsonify({'error': 'Match not found'}), 404
            
        match.respond(redis_client, data['response'])
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Match response failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/<match_id>', methods=['GET', 'POST'])
def handle_messages(match_id):
    try:
        match = Match.get(redis_client, match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404
            
        # Test data isolation
        if is_test_request() != match.is_test:
            return jsonify({'error': 'Match not found'}), 404
            
        if request.method == 'GET':
            messages = Message.get_conversation(redis_client, match_id)
            return jsonify([m.to_dict() for m in messages])
            
        else:  # POST
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=42069, debug=True)
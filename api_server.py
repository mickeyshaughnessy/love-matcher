"""
🤔 Love Matcher API Server
Clean routing layer using handlers.py for business logic
"""

from flask import Flask
from flask_cors import CORS
import os, logging, redis
import handlers

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

# Health check
@app.route('/ping', methods=['GET'])
def ping():
    return handlers.handle_health_check(redis_client)

# Profile endpoints
@app.route('/api/profiles', methods=['POST'])
def create_profile():
    return handlers.handle_create_profile(redis_client)

@app.route('/api/profiles/<user_id>', methods=['GET'])
def get_profile(user_id):
    return handlers.handle_get_profile(redis_client, user_id)

@app.route('/api/profiles/<user_id>', methods=['PUT'])
def update_profile(user_id):
    return handlers.handle_update_profile(redis_client, user_id)

# Match endpoints  
@app.route('/api/matches/<user_id>', methods=['GET'])
def get_matches(user_id):
    return handlers.handle_get_matches(redis_client, user_id)

@app.route('/api/matches/<user_id>/outcome', methods=['POST'])
def match_outcome(user_id):
    return handlers.handle_match_outcome(redis_client, user_id)

# Message endpoints
@app.route('/api/messages', methods=['POST'])
def send_message():
    return handlers.handle_send_message(redis_client)

@app.route('/api/messages/<user_id>', methods=['GET'])
def get_messages(user_id):
    return handlers.handle_get_messages(redis_client, user_id)

# Stats endpoints
@app.route('/api/users/<user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    return handlers.handle_user_stats(redis_client, user_id)

if __name__ == '__main__':
    try:
        redis_client.ping()
        logger.info("Redis connection successful")
    except redis.ConnectionError:
        logger.error("Could not connect to Redis!")
        exit(1)
        
    app.run(host='0.0.0.0', port=42069, debug=True)
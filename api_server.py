from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from functools import wraps
import os, logging, redis, handlers, jwt, time

app = Flask(__name__)
CORS(app)
app.config.update(
    JWT_SECRET=os.environ.get('JWT_SECRET', 'dev-secret-key'),
    REDIS_URL=os.environ.get('REDIS_URL', 'redis://localhost:6378/0')
)

redis_client = redis.from_url(app.config['REDIS_URL'], decode_responses=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def error_response(msg, code=500): 
    return jsonify({'error': str(msg)}), code

def rate_limit(func=None, limit=100, window=60):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = f'ratelimit:{request.remote_addr}:{f.__name__}'
            current = redis_client.get(key)
            
            reset_time = int(time.time()) + window
            response = make_response()
            response.headers.update({
                'X-RateLimit-Limit': str(limit),
                'X-RateLimit-Reset': str(reset_time),
                'X-RateLimit-Remaining': str(max(0, limit - (int(current or 0) + 1)))
            })
            
            if current is not None and int(current) >= limit:
                return error_response('Rate limit exceeded', 429)
            
            redis_client.setex(key, window, int(current or 0) + 1)
            return f(*args, **kwargs)
        return decorated
    return decorator(func) if func else decorator

def authenticated(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return error_response('No valid auth token', 401)
        try:
            token = auth.split(' ')[1]
            payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            request.user_id = payload['user_id']
            return f(*args, **kwargs)
        except jwt.InvalidTokenError:
            return error_response('Invalid auth token', 401)
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return error_response('Authentication failed', 401)
    return decorated

# Public endpoints
@app.route('/ping')
def ping():
    return jsonify({"status": "ok"})

@app.route('/register', methods=['POST'])
@rate_limit(limit=20)
def register():
    try:
        data = request.json
        if not data or not all(k in data for k in ['email', 'password', 'name', 'age']):
            return error_response('Missing required fields', 400)
        return handlers.handle_register(redis_client)
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return error_response("Registration failed", 500)

# Profile endpoints
@app.route('/api/profiles/<user_id>', methods=['GET'])
@authenticated
@rate_limit(limit=100)
def get_profile(user_id):
    try:
        return handlers.handle_get_profile(redis_client, user_id)
    except Exception as e:
        logger.error(f"Profile fetch failed: {e}")
        return error_response("Could not fetch profile", 500)

@app.route('/api/profiles', methods=['POST', 'DELETE'])
@authenticated
@rate_limit(limit=100)
def manage_profile():
    try:
        if request.method == 'POST':
            if not request.json:
                return error_response('Missing profile data', 400)
            if not all(k in request.json for k in ['name', 'age', 'preferences']):
                return error_response('Invalid profile data', 400)
            return handlers.handle_update_profile(redis_client, request.user_id)
        else:  # DELETE
            return handlers.handle_delete_profile(redis_client, request.user_id)
    except Exception as e:
        logger.error(f"Profile operation failed: {e}")
        return error_response("Profile operation failed", 500)

# Chat endpoints
@app.route('/api/chat', methods=['GET', 'POST'])
@authenticated
@rate_limit(limit=300)
def handle_chat():
    try:
        if request.method == 'GET':
            other_id = request.args.get('with')
            if not other_id:
                return error_response("Missing 'with' parameter", 400)
            return handlers.handle_get_messages(redis_client, request.user_id, other_id)
        else:  # POST
            if not request.json or 'to' not in request.json or 'content' not in request.json:
                return error_response('Invalid message data', 400)
            return handlers.handle_send_message(
                redis_client, request.user_id, request.json['to'], request.json['content']
            )
    except Exception as e:
        logger.error(f"Chat operation failed: {e}")
        return error_response("Chat operation failed", 500)

if __name__ == '__main__':
    try:
        redis_client.ping()
        logger.info("Redis connection successful")
    except redis.ConnectionError:
        logger.error("Could not connect to Redis!")
        exit(1)
        
    app.run(host='0.0.0.0', port=42069, debug=True)
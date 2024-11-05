"""
🤔 Love Matcher API Server
Simplified core functionality:
- Profiles (create/read/update)
- Messages (send/receive)
- Monitor (public health check)
"""
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from functools import wraps
import os, logging, redis, handlers, jwt, time

app = Flask(__name__)
CORS(app)
app.config.update(
    JWT_SECRET=os.environ.get('JWT_SECRET', 'dev-secret-key'),
    API_VERSION='v1'
)

redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6378)),
    db=int(os.environ.get('REDIS_DB', 0)),
    decode_responses=True
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def error_response(msg, code=500):
    return jsonify({'error': str(msg)}), code

def check_version():
    accept = request.headers.get('Accept', '')
    if f'application/vnd.love-matcher.{app.config["API_VERSION"]}+json' not in accept:
        return error_response('Invalid API version', 406)
    return None

def rate_limit(func=None, limit=100, window=60):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            version_error = check_version()
            if version_error:
                return version_error
            
            key = f'ratelimit:{request.remote_addr}:{f.__name__}'
            current = redis_client.get(key)
            
            reset_time = int(time.time()) + window
            response = make_response()
            response.headers.update({
                'X-RateLimit-Limit': str(limit),
                'X-RateLimit-Reset': str(reset_time)
            })
            
            if current is not None and int(current) >= limit:
                response.headers['X-RateLimit-Remaining'] = '0'
                return error_response('Rate limit exceeded', 429)
            
            pipe = redis_client.pipeline()
            if current is None:
                pipe.setex(key, window, 1)
                remaining = limit - 1
            else:
                pipe.incr(key)
                remaining = limit - int(current) - 1
            pipe.execute()
            
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            return f(*args, **kwargs)
        return decorated
    return decorator(func) if func else decorator

def authenticated(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return error_response('No valid auth token', 401)
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            request.user_id = payload['user_id']
            return f(*args, **kwargs)
        except jwt.InvalidTokenError:
            return error_response('Invalid auth token', 401)
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return error_response('Authentication failed', 401)
    return decorated

@app.route('/ping', methods=['GET'])
@rate_limit(limit=100)
def ping():
    return jsonify({"status": "ok"})

@app.route('/monitor', methods=['GET'])
@rate_limit(limit=30)
def monitor():
    try:
        metrics = {
            "status": "ok",
            "timestamp": int(time.time()),
            "metrics": {
                "total_users": len(redis_client.hgetall('love:users')),
                "active_users": 0,
                "total_matches": len(redis_client.hgetall('love:matches')),
                "active_matches": 0,
                "match_success_rate": 0.0,
                "messages_last_hour": 0,
                "total_messages": len(redis_client.hgetall('love:messages'))
            },
            "health": {
                "api": True,
                "redis": redis_client.ping(),
                "rate_limited": False
            }
        }
        handler_metrics = handlers.handle_monitor(redis_client)
        metrics["metrics"].update(handler_metrics.get("metrics", {}))
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        return error_response("Could not fetch monitor data", 500)

@app.route('/api/profiles', methods=['POST'])
@authenticated
@rate_limit(limit=100)
def create_profile():
    try:
        return handlers.handle_create_profile(redis_client)
    except Exception as e:
        logger.error(f"Profile creation failed: {e}")
        return error_response("Could not create profile", 500)

@app.route('/api/profiles/<user_id>', methods=['GET'])
@authenticated
@rate_limit(limit=100)
def get_profile(user_id):
    try:
        return handlers.handle_get_profile(redis_client, user_id)
    except Exception as e:
        logger.error(f"Profile fetch failed: {e}")
        return error_response("Could not fetch profile", 500)

@app.route('/api/profiles/<user_id>', methods=['PUT'])
@authenticated
@rate_limit(limit=100)
def update_profile(user_id):
    try:
        if user_id != request.user_id:
            return error_response("Not authorized", 403)
        return handlers.handle_update_profile(redis_client, user_id)
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        return error_response("Could not update profile", 500)

@app.route('/api/messages', methods=['POST'])
@authenticated
@rate_limit(limit=300)
def send_message():
    try:
        return handlers.handle_send_message(redis_client)
    except Exception as e:
        logger.error(f"Message send failed: {e}")
        return error_response("Could not send message", 500)

@app.route('/api/messages/<user_id>', methods=['GET'])
@authenticated
@rate_limit(limit=300)
def get_messages(user_id):
    try:
        if user_id != request.user_id:
            return error_response("Not authorized", 403)
        return handlers.handle_get_messages(redis_client, user_id)
    except Exception as e:
        logger.error(f"Message fetch failed: {e}")
        return error_response("Could not fetch messages", 500)

if __name__ == '__main__':
    try:
        redis_client.ping()
        logger.info("Redis connection successful")
    except redis.ConnectionError:
        logger.error("Could not connect to Redis!")
        exit(1)

    app.run(host='0.0.0.0', port=42069, debug=True)
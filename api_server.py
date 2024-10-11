from flask import Flask, jsonify, request
from flask_redis import FlaskRedis
import os
from models import User, Match, Message
from utils import create_match

app = Flask(__name__)
app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379')
redis_client = FlaskRedis(app)

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"message": "pong"})

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    user = User(data['name'], data['age'], data['preferences'], is_simulated=data.get('is_simulated', False))
    user.save(redis_client)
    return jsonify(user.to_dict()), 201

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    user = User.get(redis_client, user_id)
    if user:
        return jsonify(user.to_dict())
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    if User.delete(redis_client, user_id):
        return jsonify({'message': 'User deleted successfully'})
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/users/<user_id>/preferences', methods=['PUT'])
def update_preferences(user_id):
    data = request.json
    user = User.get(redis_client, user_id)
    if user:
        user.update_preferences(redis_client, data)
        return jsonify({'message': 'Preferences updated successfully'})
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/matches/<user_id>', methods=['GET'])
def get_matches(user_id):
    user = User.get(redis_client, user_id)
    if user:
        matches = Match.get_user_matches(redis_client, user_id, user.is_simulated)
        return jsonify([match.to_dict() for match in matches])
    return jsonify({'message': 'No matches found'}), 404

@app.route('/api/matches/<user_id>/create', methods=['POST'])
def create_new_match(user_id):
    match = create_match(redis_client, user_id)
    if match:
        return jsonify(match), 201
    return jsonify({'message': 'Unable to create a match at this time'}), 400

@app.route('/api/matches/<match_id>/complete', methods=['POST'])
def complete_existing_match(match_id):
    match = Match.get(redis_client, match_id)
    if match:
        if match.complete(redis_client):
            return jsonify({'message': 'Match completed successfully'})
    return jsonify({'error': 'Match not found or already completed'}), 404

@app.route('/api/matches/<user_id>/<match_id>/profile', methods=['GET'])
def get_match_user_profile(user_id, match_id):
    match = Match.get(redis_client, match_id)
    if match:
        profile = match.get_profile(redis_client, user_id)
        if profile:
            return jsonify(profile)
    return jsonify({'error': 'Match not found or not completed'}), 404

@app.route('/api/matches/<user_id>/outcome', methods=['POST'])
def set_match_outcome(user_id):
    data = request.json
    match = Match.get(redis_client, data['match_id'])
    if match:
        if match.record_outcome(redis_client, data['outcome']):
            if data['outcome'] == 'accepted':
                match.complete(redis_client)
            return jsonify({'message': 'Match outcome recorded successfully'})
    return jsonify({'error': 'Match not found'}), 404

@app.route('/api/messages', methods=['POST'])
def send_message():
    data = request.json
    from_user = User.get(redis_client, data['from'])
    to_user = User.get(redis_client, data['to'])
    
    if not from_user or not to_user:
        return jsonify({'error': 'User not found'}), 404
    
    if from_user.is_simulated != to_user.is_simulated:
        return jsonify({'error': 'Cannot send messages between simulated and real users'}), 400
    
    message = Message(data['from'], data['to'], data['content'], is_simulated=from_user.is_simulated)
    message.save(redis_client)
    return jsonify({'message': 'Message sent successfully'})

@app.route('/api/messages/<user_id>', methods=['GET'])
def get_messages(user_id):
    other_user_id = request.args.get('other_user_id')
    user = User.get(redis_client, user_id)
    other_user = User.get(redis_client, other_user_id)
    
    if not user or not other_user:
        return jsonify({'error': 'User not found'}), 404
    
    messages = Message.get_conversation(redis_client, user_id, other_user_id, user.is_simulated)
    return jsonify([message.to_dict() for message in messages])

@app.route('/api/users/<user_id>/stats', methods=['GET'])
def user_stats(user_id):
    user = User.get(redis_client, user_id)
    if user:
        stats = user.get_stats(redis_client)
        return jsonify(stats)
    return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
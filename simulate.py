import redis
import json
import random
from datetime import datetime, timedelta
import uuid

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def generate_user():
    return {
        'id': str(uuid.uuid4()),
        'name': f"SimUser_{random.randint(1000, 9999)}",
        'age': random.randint(18, 65),
        'preferences': {
            'max_age_difference': random.randint(1, 20),
            'interests': random.sample(['reading', 'hiking', 'movies', 'cooking', 'travel', 'music', 'sports', 'art'], k=random.randint(1, 5)),
            'location': random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']),
            'relationship_goal': random.choice(['casual', 'long-term', 'friendship']),
            'education_level': random.choice(['high school', 'bachelor', 'master', 'phd'])
        },
        'is_simulated': True
    }

def generate_match(user1_id, user2_id):
    match_time = (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
    return {
        'user1_id': user1_id,
        'user2_id': user2_id,
        'match_time': match_time,
        'is_simulated': True
    }

def generate_user_activity(user_id):
    now = datetime.now()
    for _ in range(random.randint(1, 20)):
        login_time = (now - timedelta(days=random.randint(0, 30))).isoformat()
        redis_client.zadd(f'user_logins:{user_id}', {login_time: login_time})

def generate_communication(user1_id, user2_id):
    now = datetime.now()
    for _ in range(random.randint(0, 50)):
        message_time = (now - timedelta(days=random.randint(0, 30))).isoformat()
        message = {
            'from_user_id': user1_id,
            'to_user_id': user2_id,
            'content': f"Simulated message {random.randint(1000, 9999)}",
            'timestamp': message_time,
            'is_simulated': True
        }
        msg = Message(
            from_user_id=message['from_user_id'],
            to_user_id=message['to_user_id'],
            content=message['content'],
            is_simulated=message['is_simulated'],
            timestamp=message['timestamp']
        )
        msg.save(redis_client)

def main():
    # Generate users
    users = [generate_user() for _ in range(1000)]
    
    # Save users to Redis
    for user in users:
        user_obj = User(
            name=user['name'],
            age=user['age'],
            preferences=user['preferences'],
            user_id=user['id'],
            is_simulated=user['is_simulated']
        )
        user_obj.save(redis_client)
        generate_user_activity(user['id'])
    
    # Generate matches
    for _ in range(500):
        user1, user2 = random.sample(users, 2)
        # Ensure users are not the same and avoid duplicate matches
        if user1['id'] == user2['id']:
            continue
        match = create_match(redis_client, user1['id'])
        if match:
            generate_communication(match['user1_id'], match['user2_id'])
    
    print("Simulated data generation complete.")

if __name__ == "__main__":
    main()

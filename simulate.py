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
    match_time = (datetime.now() - timedelta(days=random.randint(0, 30))).timestamp()
    return {
        'user1_id': user1_id,
        'user2_id': user2_id,
        'match_time': match_time,
        'is_simulated': True
    }

def generate_user_activity(user_id):
    now = datetime.now()
    for _ in range(random.randint(1, 20)):
        login_time = (now - timedelta(days=random.randint(0, 30))).timestamp()
        redis_client.zadd(f'user_logins:{user_id}', {login_time: login_time})

def generate_communication(user1_id, user2_id):
    now = datetime.now()
    for _ in range(random.randint(0, 50)):
        message_time = (now - timedelta(days=random.randint(0, 30))).timestamp()
        message = {
            'from': user1_id,
            'to': user2_id,
            'content': f"Simulated message {random.randint(1000, 9999)}",
            'timestamp': message_time,
            'is_simulated': True
        }
        redis_client.lpush(f'messages:{user1_id}:{user2_id}', json.dumps(message))

def main():
    # Generate users
    users = [generate_user() for _ in range(1000)]
    
    # Save users to Redis
    for user in users:
        redis_client.set(f"user:{user['id']}", json.dumps(user))
        generate_user_activity(user['id'])
    
    # Generate matches
    for _ in range(500):
        user1, user2 = random.sample(users, 2)
        match = generate_match(user1['id'], user2['id'])
        redis_client.set(f"match:{match['user1_id']}:{match['user2_id']}", json.dumps(match))
        generate_communication(user1['id'], user2['id'])
    
    print("Simulated data generation complete.")

if __name__ == "__main__":
    main()
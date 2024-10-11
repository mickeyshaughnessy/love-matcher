import uuid
import json
from datetime import datetime

class User:
    HASH_KEY_REAL = "REDHASH_USER_REAL"
    HASH_KEY_SIMULATED = "REDHASH_USER_SIMULATED"

    def __init__(self, name, age, preferences, user_id=None, is_simulated=False):
        self.id = user_id or str(uuid.uuid4())
        self.name = name
        self.age = age
        self.preferences = preferences or {
            'max_age_difference': 5,
            'interests': [],
            'location': '',
            'relationship_goal': '',
            'education_level': ''
        }
        self.is_simulated = is_simulated

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'preferences': self.preferences,
            'is_simulated': self.is_simulated
        }

    def save(self, redis_client):
        hash_key = self.HASH_KEY_SIMULATED if self.is_simulated else self.HASH_KEY_REAL
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    def update_preferences(self, redis_client, new_preferences):
        # Update the user's preferences with the provided data
        self.preferences.update(new_preferences)
        self.save(redis_client)

    def get_stats(self, redis_client):
        # Example statistics: number of matches and messages
        match_key = "REDHASH_MATCH_SIMULATED" if self.is_simulated else "REDHASH_MATCH_REAL"
        matches = [m for m in redis_client.hvals(match_key) if self.id.encode() in m]
        message_key = "REDHASH_MESSAGE_SIMULATED" if self.is_simulated else "REDHASH_MESSAGE_REAL"
        messages = [msg for msg in redis_client.hvals(message_key) if self.id.encode() in msg]
        return {
            'total_matches': len(matches),
            'total_messages': len(messages)
        }

    @classmethod
    def get(cls, redis_client, user_id):
        user_data = redis_client.hget(cls.HASH_KEY_REAL, user_id)
        if not user_data:
            user_data = redis_client.hget(cls.HASH_KEY_SIMULATED, user_id)
        
        if user_data:
            data = json.loads(user_data.decode('utf-8'))
            return cls(data['name'], data['age'], data['preferences'], data['id'], data['is_simulated'])
        return None

    @classmethod
    def get_all(cls, redis_client, include_simulated=False):
        real_user_ids = redis_client.hkeys(cls.HASH_KEY_REAL)
        real_users = [cls.get(redis_client, uid.decode('utf-8')) for uid in real_user_ids]
        if include_simulated:
            simulated_user_ids = redis_client.hkeys(cls.HASH_KEY_SIMULATED)
            simulated_users = [cls.get(redis_client, uid.decode('utf-8')) for uid in simulated_user_ids]
            return real_users + simulated_users
        return real_users

    @classmethod
    def delete(cls, redis_client, user_id):
        if redis_client.hdel(cls.HASH_KEY_REAL, user_id) == 0:
            return redis_client.hdel(cls.HASH_KEY_SIMULATED, user_id) > 0
        return True

class Match:
    HASH_KEY_REAL = "REDHASH_MATCH_REAL"
    HASH_KEY_SIMULATED = "REDHASH_MATCH_SIMULATED"

    def __init__(self, user1_id, user2_id, match_score, match_id=None, is_simulated=False, outcome=None, completed=False):
        self.id = match_id or str(uuid.uuid4())
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.match_score = match_score
        self.created_at = datetime.now().isoformat()
        self.is_simulated = is_simulated
        self.outcome = outcome  # 'accepted', 'rejected', etc.
        self.completed = completed

    def to_dict(self):
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'match_score': self.match_score,
            'created_at': self.created_at,
            'is_simulated': self.is_simulated,
            'outcome': self.outcome,
            'completed': self.completed
        }

    def save(self, redis_client):
        hash_key = self.HASH_KEY_SIMULATED if self.is_simulated else self.HASH_KEY_REAL
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    def complete(self, redis_client):
        if not self.completed:
            self.completed = True
            self.save(redis_client)
            return True
        return False

    def record_outcome(self, redis_client, outcome):
        if not self.completed:
            self.outcome = outcome
            self.save(redis_client)
            return True
        return False

    def get_profile(self, redis_client, user_id):
        other_user_id = self.user2_id if self.user1_id == user_id else self.user1_id
        return User.get(redis_client, other_user_id).to_dict() if User.get(redis_client, other_user_id) else None

    @classmethod
    def get(cls, redis_client, match_id):
        match_data = redis_client.hget(cls.HASH_KEY_REAL, match_id)
        if not match_data:
            match_data = redis_client.hget(cls.HASH_KEY_SIMULATED, match_id)
        
        if match_data:
            data = json.loads(match_data.decode('utf-8'))
            return cls(
                data['user1_id'],
                data['user2_id'],
                data['match_score'],
                data['id'],
                data['is_simulated'],
                data.get('outcome'),
                data.get('completed', False)
            )
        return None

    @classmethod
    def get_user_matches(cls, redis_client, user_id, is_simulated):
        hash_key = cls.HASH_KEY_SIMULATED if is_simulated else cls.HASH_KEY_REAL
        all_matches = [json.loads(match.decode('utf-8')) for match in redis_client.hvals(hash_key)]
        return [cls(**match) for match in all_matches if match['user1_id'] == user_id or match['user2_id'] == user_id]

class Message:
    HASH_KEY_REAL = "REDHASH_MESSAGE_REAL"
    HASH_KEY_SIMULATED = "REDHASH_MESSAGE_SIMULATED"

    def __init__(self, from_user_id, to_user_id, content, message_id=None, is_simulated=False, timestamp=None):
        self.id = message_id or str(uuid.uuid4())
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.is_simulated = is_simulated

    def to_dict(self):
        return {
            'id': self.id,
            'from_user_id': self.from_user_id,
            'to_user_id': self.to_user_id,
            'content': self.content,
            'timestamp': self.timestamp,
            'is_simulated': self.is_simulated
        }

    def save(self, redis_client):
        hash_key = self.HASH_KEY_SIMULATED if self.is_simulated else self.HASH_KEY_REAL
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    @classmethod
    def get(cls, redis_client, message_id):
        message_data = redis_client.hget(cls.HASH_KEY_REAL, message_id)
        if not message_data:
            message_data = redis_client.hget(cls.HASH_KEY_SIMULATED, message_id)
        
        if message_data:
            data = json.loads(message_data.decode('utf-8'))
            return cls(
                data['from_user_id'],
                data['to_user_id'],
                data['content'],
                data['id'],
                data['is_simulated'],
                data['timestamp']
            )
        return None

    @classmethod
    def get_conversation(cls, redis_client, user1_id, user2_id, is_simulated):
        hash_key = cls.HASH_KEY_SIMULATED if is_simulated else cls.HASH_KEY_REAL
        all_messages = [json.loads(msg.decode('utf-8')) for msg in redis_client.hvals(hash_key)]
        return [
            cls(**msg) for msg in all_messages
            if (msg['from_user_id'] == user1_id and msg['to_user_id'] == user2_id) or
               (msg['from_user_id'] == user2_id and msg['to_user_id'] == user1_id)
        ]

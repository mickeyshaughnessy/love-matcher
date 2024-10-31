import uuid, json
from datetime import datetime

class User:
    """
    🤔 Key changes:
    - Added is_test parameter to __init__ 
    - Modified hash key selection to use test-specific keys
    - Added parameter forwarding in class methods
    """
    HASH_KEY_PROD = "REDHASH_USER_PROD"
    HASH_KEY_TEST = "REDHASH_USER_TEST"
    
    def __init__(self, name, age, preferences, user_id=None, is_simulated=False, is_test=False):
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
        self.is_test = is_test

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'preferences': self.preferences,
            'is_simulated': self.is_simulated,
            'is_test': self.is_test
        }

    def save(self, redis_client):
        hash_key = self._get_hash_key()
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    def _get_hash_key(self):
        return self.HASH_KEY_TEST if self.is_test else self.HASH_KEY_PROD

    @classmethod
    def get(cls, redis_client, user_id, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        user_data = redis_client.hget(hash_key, user_id)
        
        if user_data:
            data = json.loads(user_data)
            return cls(
                data['name'], 
                data['age'], 
                data['preferences'], 
                data['id'],
                data.get('is_simulated', False),
                data.get('is_test', False)
            )
        return None

    @classmethod
    def get_all(cls, redis_client, include_simulated=False, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        users = [cls.get(redis_client, uid, is_test) for uid in redis_client.hkeys(hash_key)]
        if include_simulated:
            return users
        return [u for u in users if not u.is_simulated]

    @classmethod
    def delete(cls, redis_client, user_id, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        return redis_client.hdel(hash_key, user_id) > 0

class Match:
    """Similar test/prod separation for Match class"""
    HASH_KEY_PROD = "REDHASH_MATCH_PROD"
    HASH_KEY_TEST = "REDHASH_MATCH_TEST"
    
    def __init__(self, user1_id, user2_id, match_score, match_id=None, is_simulated=False, is_test=False):
        self.id = match_id or str(uuid.uuid4())
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.match_score = match_score
        self.created_at = datetime.now().isoformat()
        self.is_simulated = is_simulated
        self.is_test = is_test

    def to_dict(self):
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'match_score': self.match_score,
            'created_at': self.created_at,
            'is_simulated': self.is_simulated,
            'is_test': self.is_test
        }

    def save(self, redis_client):
        hash_key = self._get_hash_key()
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    def _get_hash_key(self):
        return self.HASH_KEY_TEST if self.is_test else self.HASH_KEY_PROD

    @classmethod
    def get(cls, redis_client, match_id, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        match_data = redis_client.hget(hash_key, match_id)
        
        if match_data:
            data = json.loads(match_data)
            return cls(
                data['user1_id'],
                data['user2_id'], 
                data['match_score'],
                data['id'],
                data.get('is_simulated', False),
                data.get('is_test', False)
            )
        return None

class Message:
    """Similar test/prod separation for Message class"""
    HASH_KEY_PROD = "REDHASH_MESSAGE_PROD"
    HASH_KEY_TEST = "REDHASH_MESSAGE_TEST"
    
    def __init__(self, from_user_id, to_user_id, content, message_id=None, is_simulated=False, is_test=False):
        self.id = message_id or str(uuid.uuid4())
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.is_simulated = is_simulated
        self.is_test = is_test

    def to_dict(self):
        return {
            'id': self.id,
            'from_user_id': self.from_user_id,
            'to_user_id': self.to_user_id,
            'content': self.content,
            'timestamp': self.timestamp,
            'is_simulated': self.is_simulated,
            'is_test': self.is_test
        }

    def save(self, redis_client):
        hash_key = self._get_hash_key()
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    def _get_hash_key(self):
        return self.HASH_KEY_TEST if self.is_test else self.HASH_KEY_PROD

    @classmethod
    def get(cls, redis_client, message_id, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        message_data = redis_client.hget(hash_key, message_id)
        
        if message_data:
            data = json.loads(message_data)
            return cls(
                data['from_user_id'],
                data['to_user_id'],
                data['content'],
                data['id'],
                data.get('is_simulated', False),
                data.get('is_test', False)
            )
        return None
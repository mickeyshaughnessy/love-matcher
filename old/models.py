import json, time, uuid
from datetime import datetime

class User:
    HASH_KEY_PROD, HASH_KEY_TEST = "users:prod", "users:test"
    
    def __init__(self, profile_data, is_test=False, user_id=None):
        self.id = user_id or str(uuid.uuid4())
        self.profile = profile_data
        self.is_test = is_test
        self.created_at = int(time.time())
        self.last_active = self.created_at

    def to_dict(self): return {
        'id': self.id,
        'profile': self.profile,
        'is_test': self.is_test,
        'created_at': self.created_at,
        'last_active': self.last_active
    }

    def save(self, redis_client):
        hash_key = self.HASH_KEY_TEST if self.is_test else self.HASH_KEY_PROD
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    @classmethod
    def get(cls, redis_client, user_id, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        data = redis_client.hget(hash_key, user_id)
        if not data: return None
        data = json.loads(data)
        return cls(data['profile'], data['is_test'], data['id'])

    @classmethod
    def get_all(cls, redis_client, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        return [cls.get(redis_client, uid, is_test) 
                for uid in redis_client.hkeys(hash_key)]

class Chat:
    HASH_KEY_PROD, HASH_KEY_TEST = "chats:prod", "chats:test"
    
    def __init__(self, user1_id, user2_id, is_test=False, chat_id=None):
        self.id = chat_id or str(uuid.uuid4())
        self.user1_id, self.user2_id = user1_id, user2_id
        self.is_test = is_test
        self.created_at = int(time.time())
        self.messages = []
        self.match_score = None
        self.status = 'pending'  # pending, active, declined

    def add_message(self, from_id, content):
        self.messages.append({
            'id': str(uuid.uuid4()),
            'from_id': from_id,
            'content': content,
            'timestamp': int(time.time())
        })
        self.save(self._redis)  # Save after each message

    def set_match_score(self, score):
        self.match_score = score
        self.save(self._redis)

    def set_status(self, status):
        self.status = status
        self.save(self._redis)

    def to_dict(self): return {
        'id': self.id,
        'user1_id': self.user1_id,
        'user2_id': self.user2_id,
        'is_test': self.is_test,
        'created_at': self.created_at,
        'messages': self.messages,
        'match_score': self.match_score,
        'status': self.status
    }

    def save(self, redis_client):
        self._redis = redis_client  # Store for message updates
        hash_key = self.HASH_KEY_TEST if self.is_test else self.HASH_KEY_PROD
        redis_client.hset(hash_key, self.id, json.dumps(self.to_dict()))

    @classmethod
    def get(cls, redis_client, chat_id, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        data = redis_client.hget(hash_key, chat_id)
        if not data: return None
        data = json.loads(data)
        chat = cls(data['user1_id'], data['user2_id'], 
                  data['is_test'], data['id'])
        chat.messages = data['messages']
        chat.match_score = data['match_score']
        chat.status = data['status']
        chat._redis = redis_client
        return chat

    @classmethod
    def get_user_chats(cls, redis_client, user_id, is_test=False):
        hash_key = cls.HASH_KEY_TEST if is_test else cls.HASH_KEY_PROD
        all_chats = [cls.get(redis_client, cid, is_test) 
                    for cid in redis_client.hkeys(hash_key)]
        return [c for c in all_chats 
                if c and (c.user1_id == user_id or c.user2_id == user_id)]
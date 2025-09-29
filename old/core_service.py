import json, time, math, uuid, logging
from models import User, Match, Message
from llm import matched_service

"""
🤔 Love Matcher Core Service Layer
- Unified match/message handling
- Integrated LLM compatibility scoring
- Location-aware matching
- Real-time state management
<Flow>
[User] created -> active -> matched -> connected
[Match] pending -> active -> completed
[Chat] created -> active -> archived
"""

def dist(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

class LoveMatcherService:
    def __init__(self, redis):
        self.redis = redis
        self.users = "love:users"
        self.matches = "love:matches" 
        self.messages = "love:messages"
        self.metrics = "love:metrics"

    def create_profile(self, data):
        if not all(k in data for k in ['name', 'age', 'gender', 'preferences', 'location']):
            raise ValueError("Missing required profile fields")
            
        loc = data['location']
        if not isinstance(loc, dict) or not all(k in loc for k in ['lat', 'lon']):
            raise ValueError("Invalid location format")

        user_id = str(uuid.uuid4())
        user = {
            'id': user_id,
            'status': 'active',
            'created_at': time.time(),
            'last_active': time.time(),
            **data
        }
        
        self.redis.hset(self.users, user_id, json.dumps(user))
        self._update_metrics('profiles_created')
        return {'user_id': user_id, 'status': 'active'}

    def find_matches(self, user_id, max_distance=50):
        user = self._get_user(user_id)
        if not user:
            return {'status': 'error', 'message': 'User not found'}

        loc = user['location']
        matches = []

        # Fast path: Find users within range first
        for other_id, data in self.redis.hgetall(self.users).items():
            if other_id == user_id:
                continue
                
            try:
                other = json.loads(data)
                if other['status'] != 'active':
                    continue

                # Quick distance check
                d = dist(loc['lat'], loc['lon'],
                        other['location']['lat'], 
                        other['location']['lon'])

                if d <= max_distance:
                    matches.append((other_id, other, d))
            except:
                continue

        if not matches:
            return {'status': 'no_matches', 'message': 'No users in range'}

        # Detailed compatibility check
        compatibility_scores = []
        for other_id, other, distance in matches:
            score = self._calculate_compatibility(user, other)
            if score > 0:
                compatibility_scores.append({
                    'user_id': other_id,
                    'score': score,
                    'distance': distance,
                    'profile': {
                        'name': other['name'],
                        'age': other['age'],
                        'bio': other.get('bio', ''),
                        'interests': other.get('interests', [])
                    }
                })

        # Sort by score and return top matches
        compatibility_scores.sort(key=lambda x: (-x['score'], x['distance']))
        return {
            'status': 'success',
            'matches': compatibility_scores[:10]  # Return top 10 matches
        }

    def propose_match(self, user_id, target_id):
        user = self._get_user(user_id)
        target = self._get_user(target_id)
        
        if not user or not target:
            return {'status': 'error', 'message': 'User not found'}
            
        # Check if match already exists
        existing = self._get_match(user_id, target_id)
        if existing:
            return {'status': 'error', 'message': 'Match already exists'}
            
        match_id = str(uuid.uuid4())
        match = {
            'id': match_id,
            'user1_id': user_id,
            'user2_id': target_id,
            'status': 'pending',
            'created_at': time.time(),
            'compatibility_score': self._calculate_compatibility(user, target),
            'user1_response': 'proposed',
            'user2_response': 'pending'
        }
        
        self.redis.hset(self.matches, match_id, json.dumps(match))
        self._update_metrics('matches_proposed')
        return {'status': 'success', 'match_id': match_id}

    def respond_to_match(self, match_id, user_id, response):
        match = json.loads(self.redis.hget(self.matches, match_id))
        if not match:
            return {'status': 'error', 'message': 'Match not found'}
            
        if user_id == match['user1_id']:
            match['user1_response'] = response
        elif user_id == match['user2_id']:
            match['user2_response'] = response
        else:
            return {'status': 'error', 'message': 'User not part of match'}
            
        # Check if both accepted
        if match['user1_response'] == 'accepted' and match['user2_response'] == 'accepted':
            match['status'] = 'active'
            self._update_metrics('matches_connected')
            
        # Update match record
        self.redis.hset(self.matches, match_id, json.dumps(match))
        return {'status': 'success', 'match': match}

    def send_message(self, from_id, to_id, content):
        # Verify active match exists
        match = self._get_match(from_id, to_id)
        if not match or match['status'] != 'active':
            return {'status': 'error', 'message': 'No active match'}
            
        msg_id = str(uuid.uuid4())
        message = {
            'id': msg_id,
            'match_id': match['id'],
            'from_id': from_id,
            'to_id': to_id,
            'content': content,
            'timestamp': time.time(),
            'status': 'sent'
        }
        
        self.redis.hset(self.messages, msg_id, json.dumps(message))
        self._update_metrics('messages_sent')
        return {'status': 'success', 'message_id': msg_id}

    def get_messages(self, match_id):
        messages = []
        for msg_id, data in self.redis.hgetall(self.messages).items():
            try:
                msg = json.loads(data)
                if msg['match_id'] == match_id:
                    messages.append(msg)
            except:
                continue
                
        return sorted(messages, key=lambda x: x['timestamp'])

    def _get_user(self, user_id):
        data = self.redis.hget(self.users, user_id)
        return json.loads(data) if data else None

    def _get_match(self, user1_id, user2_id):
        for match_id, data in self.redis.hgetall(self.matches).items():
            try:
                match = json.loads(data)
                if (match['user1_id'] == user1_id and match['user2_id'] == user2_id) or \
                   (match['user1_id'] == user2_id and match['user2_id'] == user1_id):
                    return match
            except:
                continue
        return None

    def _calculate_compatibility(self, user1, user2):
        score = 0
        
        # Basic compatibility (age, location, preferences)
        age_diff = abs(user1['age'] - user2['age'])
        if age_diff <= user1['preferences'].get('max_age_diff', 10):
            score += 20
            
        # Location score
        d = dist(user1['location']['lat'], user1['location']['lon'],
                user2['location']['lat'], user2['location']['lon'])
        if d <= 5: score += 20
        elif d <= 15: score += 10
        
        # Use LLM for deep compatibility analysis
        try:
            description = f"""
            Person 1: {user1.get('bio', '')}
            Interests: {', '.join(user1.get('interests', []))}
            Looking for: {user1['preferences'].get('relationship_type', 'relationship')}
            
            Person 2: {user2.get('bio', '')}
            Interests: {', '.join(user2.get('interests', []))}
            Looking for: {user2['preferences'].get('relationship_type', 'relationship')}
            """
            
            if matched_service(description, "relationship compatibility analysis"):
                score += 30
        except:
            # Fallback to basic interest matching
            common_interests = set(user1.get('interests', [])) & set(user2.get('interests', []))
            score += len(common_interests) * 5
            
        return min(score, 100)  # Cap at 100

    def _update_metrics(self, metric_name):
        try:
            self.redis.hincrby(self.metrics, metric_name, 1)
            self.redis.hincrby(self.metrics, f"{metric_name}_today", 1)
            
            # Reset daily counters at midnight
            now = time.time()
            last_reset = float(self.redis.get('metrics_last_reset') or 0)
            if time.strftime('%Y-%m-%d', time.localtime(now)) != \
               time.strftime('%Y-%m-%d', time.localtime(last_reset)):
                for key in self.redis.hkeys(self.metrics):
                    if key.endswith('_today'):
                        self.redis.hset(self.metrics, key, 0)
                self.redis.set('metrics_last_reset', now)
        except:
            pass  # Don't let metrics errors affect core functionality
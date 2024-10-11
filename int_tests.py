import requests
import unittest
import random
import uuid

BASE_URL = 'http://localhost:5000'

class TestLoveMatcherAPI(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()

    def test_ping(self):
        response = self.session.get(f'{BASE_URL}/ping')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'message': 'pong'})

    def create_user(self, is_simulated=False):
        user_data = {
            'name': f'Test User {random.randint(1000, 9999)}',
            'age': random.randint(18, 65),
            'preferences': {
                'max_age_difference': random.randint(1, 20),
                'interests': random.sample(['reading', 'hiking', 'movies', 'cooking', 'travel'], k=3),
                'location': random.choice(['New York', 'Los Angeles', 'Chicago']),
                'relationship_goal': random.choice(['casual', 'long-term', 'friendship']),
                'education_level': random.choice(['high school', 'bachelor', 'master', 'phd'])
            },
            'is_simulated': is_simulated
        }
        response = self.session.post(f'{BASE_URL}/api/users', json=user_data)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_user_lifecycle(self):
        # Create user
        user = self.create_user()
        user_id = user['id']

        # Get user
        response = self.session.get(f'{BASE_URL}/api/users/{user_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], user['name'])

        # Update user preferences
        new_preferences = {
            'max_age_difference': 7,
            'interests': ['reading', 'hiking', 'traveling']
        }
        response = self.session.put(f'{BASE_URL}/api/users/{user_id}/preferences', json=new_preferences)
        self.assertEqual(response.status_code, 200)

        # Verify updated preferences
        response = self.session.get(f'{BASE_URL}/api/users/{user_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['preferences']['max_age_difference'], 7)
        self.assertEqual(set(response.json()['preferences']['interests']), set(['reading', 'hiking', 'traveling']))

        # Delete user
        response = self.session.delete(f'{BASE_URL}/api/users/{user_id}')
        self.assertEqual(response.status_code, 200)

        # Verify user is deleted
        response = self.session.get(f'{BASE_URL}/api/users/{user_id}')
        self.assertEqual(response.status_code, 404)

    def test_matching_and_messaging(self):
        # Create two users
        user1 = self.create_user()
        user2 = self.create_user()

        # Create a match for user1 with user2 directly for testing purposes
        # Assuming you have an endpoint or a way to create a specific match
        # Alternatively, simulate the match creation
        match = {
            'id': str(uuid.uuid4()),
            'user1_id': user1['id'],
            'user2_id': user2['id'],
            'match_score': 85,
            'created_at': datetime.now().isoformat(),
            'is_simulated': False,
            'outcome': None,
            'completed': False
        }
        # Manually create the match in Redis for testing
        match_obj = Match(
            user1_id=match['user1_id'],
            user2_id=match['user2_id'],
            match_score=match['match_score'],
            match_id=match['id'],
            is_simulated=match['is_simulated']
        )
        match_obj.save(redis_client)  # You'll need access to redis_client here or mock it

        # Record match outcome
        outcome_data = {
            'match_id': match['id'],
            'outcome': 'accepted'
        }
        response = self.session.post(f'{BASE_URL}/api/matches/{user1["id"]}/outcome', json=outcome_data)
        self.assertEqual(response.status_code, 200)

        # Send a message
        message_data = {
            'from': user1['id'],
            'to': user2['id'],
            'content': 'Hello, nice to meet you!'
        }
        response = self.session.post(f'{BASE_URL}/api/messages', json=message_data)
        self.assertEqual(response.status_code, 200)

        # Get messages
        response = self.session.get(f'{BASE_URL}/api/messages/{user1["id"]}', params={'other_user_id': user2['id']})
        self.assertEqual(response.status_code, 200)
        messages = response.json()
        self.assertGreaterEqual(len(messages), 1)
        self.assertEqual(messages[0]['content'], 'Hello, nice to meet you!')

        # Clean up
        self.session.delete(f'{BASE_URL}/api/users/{user1["id"]}')
        self.session.delete(f'{BASE_URL}/api/users/{user2["id"]}')

    def test_simulated_user_separation(self):
        real_user = self.create_user(is_simulated=False)
        simulated_user = self.create_user(is_simulated=True)

        # Try to create a match for the real user
        response = self.session.post(f'{BASE_URL}/api/matches/{real_user["id"]}/create')
        self.assertEqual(response.status_code, 201)
        match = response.json()
        
        if 'id' in match:
            # If a match is found, ensure it's not the simulated user
            self.assertNotEqual(match['user2_id'], simulated_user['id'])
        else:
            # If no match is found, that's also acceptable
            self.assertIn('message', match)

        # Clean up
        self.session.delete(f'{BASE_URL}/api/users/{real_user["id"]}')
        self.session.delete(f'{BASE_URL}/api/users/{simulated_user["id"]}')

if __name__ == '__main__':
    unittest.main()

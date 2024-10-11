import requests
import unittest
import random

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

        # Get match for user1
        response = self.session.get(f'{BASE_URL}/api/matches/{user1["id"]}')
        self.assertEqual(response.status_code, 200)
        match = response.json()
        self.assertIn('match_id', match)

        # Record match outcome
        outcome_data = {
            'match_id': match['match_id'],
            'outcome': 'accepted'
        }
        response = self.session.post(f'{BASE_URL}/api/matches/{user1["id"]}/outcome', json=outcome_data)
        self.assertEqual(response.status_code, 200)

        # Send a message
        message_data = {
            'to': match['match_id'],
            'content': 'Hello, nice to meet you!',
            'timestamp': 1635724800  # Example timestamp
        }
        response = self.session.post(f'{BASE_URL}/api/messages/{user1["id"]}', json=message_data)
        self.assertEqual(response.status_code, 200)

        # Get messages
        response = self.session.get(f'{BASE_URL}/api/messages/{match["match_id"]}?match_id={user1["id"]}')
        self.assertEqual(response.status_code, 200)
        messages = response.json()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['content'], 'Hello, nice to meet you!')

        # Clean up
        self.session.delete(f'{BASE_URL}/api/users/{user1["id"]}')
        self.session.delete(f'{BASE_URL}/api/users/{user2["id"]}')

    def test_simulated_user_separation(self):
        real_user = self.create_user(is_simulated=False)
        simulated_user = self.create_user(is_simulated=True)

        # Try to get a match for the real user
        response = self.session.get(f'{BASE_URL}/api/matches/{real_user["id"]}')
        self.assertEqual(response.status_code, 200)
        match = response.json()
        
        if 'match_id' in match:
            # If a match is found, ensure it's not the simulated user
            self.assertNotEqual(match['match_id'], simulated_user['id'])
        else:
            # If no match is found, that's also acceptable
            self.assertIn('message', match)

        # Clean up
        self.session.delete(f'{BASE_URL}/api/users/{real_user["id"]}')
        self.session.delete(f'{BASE_URL}/api/users/{simulated_user["id"]}')

if __name__ == '__main__':
    unittest.main()
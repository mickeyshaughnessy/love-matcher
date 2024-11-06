"""
🤔 Love Matcher Integration Tests
Simple golden path testing for each endpoint
"""
import unittest, requests, time
from datetime import datetime

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = 'http://localhost:42069'
        try:
            r = requests.get(f'{cls.base_url}/ping')
            assert r.status_code == 200, "API server not responding"
        except:
            raise unittest.SkipTest("API server not available")

    def setUp(self):
        self.users = []
        for i in range(2):
            email = f'test{i}_{int(time.time())}@test.com'
            user = self.create_test_user(email)
            self.users.append(user)

    def create_test_user(self, email):
        data = {
            'email': email,
            'password': 'test1234',
            'name': f'Test User {email}',
            'age': 25
        }
        r = requests.post(f'{self.base_url}/register', json=data)
        self.assertEqual(r.status_code, 200)
        return {
            'id': r.json()['user_id'],
            'token': r.json()['token'],
            'email': email
        }

    def test_1_health_check(self):
        """Test basic health check endpoint"""
        r = requests.get(f'{self.base_url}/ping')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'ok')

    def test_2_monitor(self):
        """Test monitor endpoint"""
        r = requests.get(f'{self.base_url}/monitor')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('metrics', data)
        self.assertIn('health', data)

    def test_3_profile_management(self):
        """Test full profile management flow"""
        user = self.users[0]
        headers = {'Authorization': f'Bearer {user["token"]}'}

        # Get profile
        r = requests.get(f'{self.base_url}/api/profiles/{user["id"]}', headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['email'], user['email'])

        # Update profile
        update_data = {
            'name': 'Updated Name',
            'preferences': {
                'interests': ['testing', 'coding'],
                'location': 'Test City',
                'max_age_difference': 5
            }
        }
        r = requests.post(f'{self.base_url}/api/profiles', headers=headers, json=update_data)
        self.assertEqual(r.status_code, 200)

        # Verify update
        r = requests.get(f'{self.base_url}/api/profiles/{user["id"]}', headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['name'], 'Updated Name')

    def test_4_chat_flow(self):
        """Test basic chat functionality"""
        sender = self.users[0]
        recipient = self.users[1]
        headers = {'Authorization': f'Bearer {sender["token"]}'}

        # Send message
        message_data = {
            'to': recipient['id'],
            'content': 'Test message'
        }
        r = requests.post(f'{self.base_url}/api/chat', headers=headers, json=message_data)
        self.assertEqual(r.status_code, 200)
        self.assertIn('message_id', r.json())

        # Get conversation
        r = requests.get(
            f'{self.base_url}/api/chat',
            headers=headers,
            params={'with': recipient['id']}
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('messages', data)
        self.assertIn('participants', data)
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['content'], 'Test message')

    def test_5_profile_deletion(self):
        """Test profile deletion"""
        user = self.users[0]
        headers = {'Authorization': f'Bearer {user["token"]}'}

        # Delete profile
        r = requests.delete(f'{self.base_url}/api/profiles', headers=headers)
        self.assertEqual(r.status_code, 200)

        # Verify deletion
        r = requests.get(f'{self.base_url}/api/profiles/{user["id"]}', headers=headers)
        self.assertEqual(r.status_code, 404)

if __name__ == '__main__':
    unittest.main(verbosity=2)
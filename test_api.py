"""
🤔 Test API Configuration
- Separates test traffic from production
- Ensures test data cleanup
- Provides test-specific endpoints
"""

import requests, json

class TestAPI:
    def __init__(self, base_url='http://localhost:42069'):
        self.base_url = base_url
        self.headers = {'X-Test-Channel': 'true'}

    def _get(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.get('headers', {})}
        return requests.get(
            f'{self.base_url}/{endpoint}',
            **{**kwargs, 'headers': headers}
        )

    def _post(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.get('headers', {})}
        return requests.post(
            f'{self.base_url}/{endpoint}',
            **{**kwargs, 'headers': headers}
        )

    def _put(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.get('headers', {})}
        return requests.put(
            f'{self.base_url}/{endpoint}',
            **{**kwargs, 'headers': headers}
        )

    def _delete(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.get('headers', {})}
        return requests.delete(
            f'{self.base_url}/{endpoint}',
            **{**kwargs, 'headers': headers}
        )

    def cleanup_test_data(self):
        """Clean up all test data"""
        return self._post('api/test/cleanup')

    def create_profile(self, profile_data):
        """Create test profile"""
        return self._post('api/profiles', json={
            **profile_data,
            'is_test': True
        })

    def get_profile(self, user_id, auth_token):
        """Get test profile"""
        return self._get(
            f'api/profiles/{user_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )

    def update_profile(self, user_id, profile_data, auth_token):
        """Update test profile"""
        return self._put(
            f'api/profiles/{user_id}',
            json={**profile_data, 'is_test': True},
            headers={'Authorization': f'Bearer {auth_token}'}
        )

    def find_matches(self, user_id, auth_token):
        """Find matches for test user"""
        return self._get(
            f'api/matches/{user_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )

    def propose_match(self, user_id, target_id, auth_token):
        """Propose test match"""
        return self._post(
            f'api/matches/{user_id}/propose',
            json={'target_id': target_id},
            headers={'Authorization': f'Bearer {auth_token}'}
        )

    def respond_to_match(self, match_id, user_id, response, auth_token):
        """Respond to test match"""
        return self._post(
            f'api/matches/{match_id}/respond',
            json={'response': response},
            headers={'Authorization': f'Bearer {auth_token}'}
        )

    def send_message(self, match_id, content, auth_token):
        """Send test message"""
        return self._post(
            f'api/messages/{match_id}',
            json={'content': content},
            headers={'Authorization': f'Bearer {auth_token}'}
        )

    def get_messages(self, match_id, auth_token):
        """Get test messages"""
        return self._get(
            f'api/messages/{match_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )

    def verify_health(self):
        """Verify test API health"""
        return self._get('ping')
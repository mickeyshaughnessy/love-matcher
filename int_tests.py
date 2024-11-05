"""
🤔 Simple Love Matcher Tests
Just verify core functionality:
1. Create account
2. Find match
3. Accept match
4. Send messages
"""
import requests, random, time, sys
from datetime import datetime

BASE_URL = 'http://localhost:42069'

def random_user():
    return {
        'email': f'test{random.randint(1000,9999)}@test.com',
        'password': 'test123',
        'name': f'Test User {random.randint(1000,9999)}',
        'age': random.randint(21, 45),
        'preferences': {
            'age_range': [20, 45],
            'location': [40.7128, -74.0060],
            'max_distance': 50,
            'interests': random.sample(['hiking', 'reading', 'music'], k=2)
        }
    }

def create_user():
    resp = requests.post(f'{BASE_URL}/register', json=random_user())
    assert resp.status_code == 200, f'Registration failed: {resp.text}'
    return resp.json()['token'], resp.json()['user']['id']

def test_basic_flow():
    """🧪 Testing basic user flow"""
    print('\n1️⃣ Creating two users...')
    token1, user1 = create_user()
    token2, user2 = create_user()
    headers1 = {'Authorization': f'Bearer {token1}'}
    headers2 = {'Authorization': f'Bearer {token2}'}

    print('2️⃣ Getting match...')
    resp = requests.get(f'{BASE_URL}/match', headers=headers1)
    assert resp.status_code == 200, 'Match fetch failed'
    match = resp.json()['match']
    print(f'Got match: {match["id"]}')

    print('3️⃣ Both users accepting match...')
    resp = requests.post(f'{BASE_URL}/match/action', headers=headers1,
                        json={'action': 'accept', 'match_id': match['id']})
    assert resp.status_code == 200, 'Match accept 1 failed'

    resp = requests.post(f'{BASE_URL}/match/action', headers=headers2,
                        json={'action': 'accept', 'match_id': match['id']})
    assert resp.status_code == 200, 'Match accept 2 failed'
    assert resp.json()['match']['status'] == 'active'

    print('4️⃣ Sending test message...')
    msg = {'match_id': match['id'], 'content': 'Hello! 👋'}
    resp = requests.post(f'{BASE_URL}/messages', headers=headers1, json=msg)
    assert resp.status_code == 200, 'Message send failed'

    print('5️⃣ Getting conversation...')
    resp = requests.get(f'{BASE_URL}/messages?match_id={match["id"]}', headers=headers2)
    assert resp.status_code == 200, 'Message fetch failed'
    messages = resp.json()['messages']
    assert len(messages) == 1, 'Wrong message count'
    assert messages[0]['content'] == 'Hello! 👋'

    print('✅ All basic tests passed!')

def run_tests():
    print(f'\n💕 Love Matcher Basic Tests - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    try:
        requests.get(f'{BASE_URL}/ping', timeout=1)
    except requests.exceptions.ConnectionError:
        print('❌ API server not running!')
        sys.exit(1)

    try:
        test_basic_flow()
        return True
    except Exception as e:
        print(f'❌ Test failed: {str(e)}')
        return False

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
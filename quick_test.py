import random, time, sys
from test_api import TestAPI

"""
🤔 Quick Dev Tests for Love Matcher
- Uses test-only channel
- Cleans up after itself
- Clear visual feedback
- Core flow validation
"""

COLORS = {
    'love': '\033[38;5;205m',
    'match': '\033[38;5;118m',
    'chat': '\033[38;5;51m',
    'alert': '\033[38;5;227m',
    'end': '\033[0m'
}

def c(text, color): return f"{COLORS[color]}{text}{COLORS['end']}"

def generate_test_profile():
    """Generate profile with test data"""
    age = random.randint(21, 45)
    gender = random.choice(['M', 'F'])
    looking_for = 'F' if gender == 'M' else 'M'
    
    # NYC-centered coordinates
    lat = 40.7128 + random.uniform(-0.1, 0.1)
    lon = -74.0060 + random.uniform(-0.1, 0.1)
    
    return {
        'name': f"Test{random.randint(1000,9999)}",
        'age': age,
        'gender': gender,
        'location': {'lat': lat, 'lon': lon},
        'bio': random.choice([
            "Test profile - please ignore",
            "Automated test user",
            "Quick test profile",
            "Dev test account"
        ]),
        'interests': random.sample([
            'testing', 'debugging', 'coding', 'automation', 
            'quality', 'development'
        ], k=random.randint(3, 5)),
        'preferences': {
            'gender': looking_for,
            'min_age': age - 5,
            'max_age': age + 5,
            'max_distance': 25,
            'relationship_type': 'test'
        }
    }

def quick_test(num_users=5):
    api = TestAPI()
    print(c("\n💕 LOVE MATCHER QUICK TEST 💕", 'love'))
    
    try:
        # Verify API health
        r = api.verify_health()
        if r.status_code != 200:
            print(c("❌ API not responding!", 'alert'))
            return
        print(c("✅ API responding", 'match'))
        
        # Clean previous test data
        print(c("\n[ CLEANING TEST DATA ]", 'love'))
        api.cleanup_test_data()
        
        # Create test profiles
        print(c("\n[ CREATING TEST PROFILES ]", 'love'))
        users = []
        for i in range(num_users):
            profile = generate_test_profile()
            r = api.create_profile(profile)
            if r.status_code == 200:
                user_id = r.json()['user_id']
                users.append((user_id, profile))
                print(f"{c('✅', 'match')} {profile['name']} "
                      f"({profile['age']}{profile['gender']})")
            else:
                print(c(f"❌ Profile creation failed: {r.text}", 'alert'))
        
        if not users:
            print(c("No test profiles created!", 'alert'))
            return
        
        # Test matching
        print(c("\n[ TESTING MATCHES ]", 'love'))
        matches = []
        for user_id, profile in users:
            r = api.find_matches(user_id, user_id)  # Use ID as auth token
            if r.status_code == 200:
                data = r.json()
                if data['status'] == 'success' and data['matches']:
                    match = data['matches'][0]
                    print(f"{c('👥', 'match')} {profile['name']} matched "
                          f"score: {match['score']}%")
                    
                    r = api.propose_match(user_id, match['user_id'], user_id)
                    if r.status_code == 200:
                        match_id = r.json()['match_id']
                        matches.append((match_id, user_id, match['user_id']))
                        print(f"{c('💘', 'match')} Match proposed!")
            
            time.sleep(0.5)

        # Test interactions
        print(c("\n[ TESTING INTERACTIONS ]", 'love'))
        for match_id, user1_id, user2_id in matches:
            # Both accept
            for user_id in [user1_id, user2_id]:
                r = api.respond_to_match(match_id, user_id, 'accepted', user_id)
                if r.status_code == 200:
                    print(f"{c('✅', 'match')} User {user_id[-4:]} accepted")
                
                time.sleep(0.5)

            # Exchange messages
            messages = [
                "Test message 1", 
                "Test response 1",
                "Test message 2", 
                "Test response 2"
            ]
            
            for i, msg in enumerate(messages):
                sender_id = user1_id if i % 2 == 0 else user2_id
                r = api.send_message(match_id, msg, sender_id)
                if r.status_code == 200:
                    print(f"{c('💌', 'chat')} Test message sent")
                
                time.sleep(0.5)
            
            # Verify messages
            r = api.get_messages(match_id, user1_id)
            if r.status_code == 200:
                msg_count = len(r.json())
                print(f"{c('📝', 'chat')} Message count: {msg_count}")

        # Final stats
        print(c("\n[ TEST SUMMARY ]", 'love'))
        print(f"✨ Created {len(users)} test profiles")
        print(f"💘 Made {len(matches)} test matches")
        print(f"💌 Exchanged {len(messages)} test messages")
        
        # Cleanup
        print(c("\n[ CLEANING UP ]", 'love'))
        api.cleanup_test_data()
        print(c("✨ All test data removed", 'match'))

    except Exception as e:
        print(c(f"\n❌ Test failed: {str(e)}", 'alert'))
        # Ensure cleanup even on failure
        api.cleanup_test_data()

if __name__ == '__main__':
    quick_test(num_users=int(sys.argv[1]) if len(sys.argv) > 1 else 5)
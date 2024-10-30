import unittest, random, time, json, redis
from concurrent.futures import ThreadPoolExecutor, as_completed
from test_api import TestAPI
from datetime import datetime, timedelta

"""
🤔 Love Matcher Integration Tests
- Complete test isolation
- Nilpotent test cases
- Redis test database
- Cleanup guaranteed
<Tests>
1. Profile management
2. Match engine
3. Messaging system
4. Location services
5. Concurrency
"""

def generate_test_profile(age_range=(25,35), location_variance=0.1):
    """Generate an explicitly marked test profile"""
    age = random.randint(*age_range)
    gender = random.choice(['M', 'F'])
    looking_for = 'F' if gender == 'M' else 'M'
    
    # Test location near NYC
    lat = 40.7128 + random.uniform(-location_variance, location_variance)
    lon = -74.0060 + random.uniform(-location_variance, location_variance)
    
    test_id = random.randint(1000,9999)
    return {
        'name': f"TestUser_{test_id}",
        'age': age,
        'gender': gender,
        'location': {'lat': lat, 'lon': lon},
        'bio': f"Integration test profile {test_id}",
        'interests': random.sample([
            'test_hiking', 'test_reading', 'test_travel', 
            'test_music', 'test_cooking', 'test_art'
        ], k=random.randint(3, 5)),
        'preferences': {
            'gender': looking_for,
            'min_age': age - 5,
            'max_age': age + 5,
            'max_distance': 25,
            'relationship_type': 'test'
        }
    }

class TestLoveMatcherAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialize test environment"""
        cls.api = TestAPI()
        cls.redis = redis.Redis(port=6378, db=9)  # Use separate test DB
        
        # Verify API is running
        try:
            r = cls.api.verify_health()
            assert r.status_code == 200, "API server not responding"
        except:
            raise unittest.SkipTest("API server not available")
            
        # Clean any leftover test data
        cls.api.cleanup_test_data()

    def setUp(self):
        """Create fresh test users for each test"""
        self.test_users = []
        for _ in range(2):
            profile = generate_test_profile()
            r = self.api.create_profile(profile)
            self.assertEqual(r.status_code, 200)
            user_id = r.json()['user_id']
            self.test_users.append((user_id, profile))

    def tearDown(self):
        """Clean up test data after each test"""
        self.api.cleanup_test_data()

    @classmethod
    def tearDownClass(cls):
        """Final cleanup"""
        cls.api.cleanup_test_data()
        cls.redis.flushdb()  # Clear test database

    def test_profile_lifecycle(self):
        """Test complete profile lifecycle"""
        # Create
        profile = generate_test_profile()
        r = self.api.create_profile(profile)
        self.assertEqual(r.status_code, 200)
        user_id = r.json()['user_id']
        
        # Read
        r = self.api.get_profile(user_id, user_id)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('test_' in r.json()['interests'][0])
        
        # Update
        profile['bio'] = "Updated test bio"
        r = self.api.update_profile(user_id, profile, user_id)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['user']['bio'], "Updated test bio")
        
        # Verify separation from production
        prod_redis = redis.Redis(port=6378, db=0)
        self.assertIsNone(prod_redis.hget('love:users', user_id))

    def test_matching_lifecycle(self):
        """Test complete matching flow between test users"""
        user1_id, profile1 = self.test_users[0]
        user2_id, profile2 = self.test_users[1]
        
        # Find matches
        r = self.api.find_matches(user1_id, user1_id)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'success')
        
        # Propose match
        r = self.api.propose_match(user1_id, user2_id, user1_id)
        self.assertEqual(r.status_code, 200)
        match_id = r.json()['match_id']
        
        # Both accept
        for user_id in [user1_id, user2_id]:
            r = self.api.respond_to_match(
                match_id, user_id, 'accepted', user_id
            )
            self.assertEqual(r.status_code, 200)
        
        # Verify match in test DB
        match_data = self.redis.hget('love:test:matches', match_id)
        self.assertIsNotNone(match_data)
        match = json.loads(match_data)
        self.assertEqual(match['status'], 'active')

    def test_messaging(self):
        """Test message exchange between test users"""
        user1_id, _ = self.test_users[0]
        user2_id, _ = self.test_users[1]
        
        # Create and accept match
        r = self.api.propose_match(user1_id, user2_id, user1_id)
        match_id = r.json()['match_id']
        
        for user_id in [user1_id, user2_id]:
            self.api.respond_to_match(match_id, user_id, 'accepted', user_id)
        
        # Exchange test messages
        messages = [
            "Test message 1", "Test response 1", 
            "Test message 2", "Test response 2"
        ]
        
        for i, msg in enumerate(messages):
            sender = user1_id if i % 2 == 0 else user2_id
            r = self.api.send_message(match_id, msg, sender)
            self.assertEqual(r.status_code, 200)
        
        # Verify messages
        r = self.api.get_messages(match_id, user1_id)
        self.assertEqual(r.status_code, 200)
        msgs = r.json()
        self.assertEqual(len(msgs), len(messages))
        self.assertTrue(all('Test' in m['content'] for m in msgs))

    def test_location_matching(self):
        """Test location-based matching with test profiles"""
        # Create profiles at different distances
        test_distances = [1, 5, 10, 20, 30]  # km
        center_id = None
        test_users = []
        
        # Center profile
        profile = generate_test_profile(location_variance=0)
        r = self.api.create_profile(profile)
        center_id = r.json()['user_id']
        
        # Profiles at distances
        for dist in test_distances:
            # Convert km to rough lat/lon difference
            delta = dist / 111.0  # ~111km per degree
            profile = generate_test_profile(location_variance=delta)
            r = self.api.create_profile(profile)
            test_users.append((r.json()['user_id'], dist))
        
        # Find matches
        r = self.api.find_matches(center_id, center_id)
        matches = r.json()['matches']
        
        # Verify distance ordering
        distances = [m['distance'] for m in matches]
        self.assertEqual(distances, sorted(distances))

    def test_concurrent_operations(self):
        """Test concurrent operations with test profiles"""
        NUM_USERS = 10
        MAX_WORKERS = 5
        
        # Create test users
        users = []
        for _ in range(NUM_USERS):
            profile = generate_test_profile()
            r = self.api.create_profile(profile)
            users.append((r.json()['user_id'], profile))
        
        def concurrent_matches(user_id):
            """Propose matches to random test users"""
            other_users = [u[0] for u in users if u[0] != user_id]
            targets = random.sample(other_users, min(3, len(other_users)))
            results = []
            
            for target_id in targets:
                r = self.api.propose_match(user_id, target_id, user_id)
                if r.status_code == 200:
                    results.append(r.json()['match_id'])
            return results
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(concurrent_matches, user_id)
                for user_id, _ in users
            ]
            
            all_matches = []
            for future in as_completed(futures):
                all_matches.extend(future.result())
        
        # Verify match integrity
        match_data = self.redis.hgetall('love:test:matches')
        self.assertTrue(all(
            match_id.decode() in str(match_data) 
            for match_id in all_matches
        ))

    def test_error_handling(self):
        """Test error conditions with test data"""
        user_id = self.test_users[0][0]
        
        # Invalid auth
        r = self.api.get_profile(user_id, 'invalid_token')
        self.assertEqual(r.status_code, 401)
        
        # Invalid profile
        r = self.api.create_profile({})
        self.assertEqual(r.status_code, 400)
        
        # Non-existent user
        r = self.api.get_profile('fake_id', user_id)
        self.assertEqual(r.status_code, 404)
        
        # Invalid match proposal
        r = self.api.propose_match(user_id, 'fake_id', user_id)
        self.assertEqual(r.status_code, 400)
        
        # Message without match
        r = self.api.send_message('fake_match', 'test', user_id)
        self.assertEqual(r.status_code, 404)

    def test_performance(self):
        """Performance tests with test data"""
        SAMPLE_SIZE = 20
        MAX_RESPONSE_TIME = 1.0  # seconds
        timings = defaultdict(list)
        
        def time_operation(operation, *args):
            start = time.time()
            result = operation(*args)
            return time.time() - start, result
        
        # Profile creation timing
        for _ in range(SAMPLE_SIZE):
            elapsed, response = time_operation(
                self.api.create_profile,
                generate_test_profile()
            )
            timings['create_profile'].append(elapsed)
            self.assertEqual(response.status_code, 200)
            time.sleep(0.1)  # Rate limit
        
        # Match finding timing
        user_id = self.test_users[0][0]
        for _ in range(SAMPLE_SIZE):
            elapsed, response = time_operation(
                self.api.find_matches,
                user_id, user_id
            )
            timings['find_matches'].append(elapsed)
            self.assertEqual(response.status_code, 200)
            time.sleep(0.1)
        
        # Verify performance
        for operation, times in timings.items():
            avg_time = sum(times) / len(times)
            max_time = max(times)
            self.assertLess(avg_time, MAX_RESPONSE_TIME, 
                          f"{operation} too slow")
            print(f"{operation}: avg={avg_time:.3f}s max={max_time:.3f}s")

if __name__ == '__main__':
    unittest.main(verbosity=2)
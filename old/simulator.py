import random, time, json, logging, threading, queue
from datetime import datetime
from collections import defaultdict
from test_api import TestAPI

"""
🤔 Love Matcher Load Simulator
- Uses test-only channel
- Cleans up after itself
- Realistic traffic patterns
- Geographic distribution
<Flow>
1. Clean previous test data
2. Generate test profiles
3. Run simulated traffic
4. Track metrics
5. Clean up on exit
"""

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Test cities with realistic coordinates
TEST_CITIES = {
    'NYC_Test': (40.7128, -74.0060),
    'LA_Test': (34.0522, -118.2437),
    'CHI_Test': (41.8781, -87.6298),
    'HOU_Test': (29.7604, -95.3698),
    'PHX_Test': (33.4484, -112.0740)
}

# Test personas with behavior patterns
TEST_PERSONAS = {
    'active_tester': {
        'login_freq': 0.8,      # 80% chance to login
        'swipe_rate': 20,       # Profiles per session
        'message_rate': 0.7,    # Message chance
        'response_time': 1,     # Hour delay
        'session_length': 10    # Minutes
    },
    'casual_tester': {
        'login_freq': 0.4,
        'swipe_rate': 10,
        'message_rate': 0.4,
        'response_time': 4,
        'session_length': 5
    },
    'batch_tester': {
        'login_freq': 0.9,
        'swipe_rate': 30,
        'message_rate': 0.8,
        'response_time': 0.5,
        'session_length': 15
    }
}

class UserSimulator(threading.Thread):
    def __init__(self, user_queue, stats_queue):
        super().__init__(daemon=True)
        self.api = TestAPI()
        self.user_queue = user_queue
        self.stats_queue = stats_queue
        self.running = True

    def generate_test_profile(self):
        """Generate a test profile with clear test markers"""
        city = random.choice(list(TEST_CITIES.keys()))
        base_lat, base_lon = TEST_CITIES[city]
        
        # Add small random offset to prevent clustering
        lat = base_lat + random.uniform(-0.05, 0.05)
        lon = base_lon + random.uniform(-0.05, 0.05)
        
        age = random.randint(21, 45)
        gender = random.choice(['M', 'F'])
        looking_for = 'F' if gender == 'M' else 'M'
        
        # Use test-specific interests
        interests = random.sample([
            'test_hiking', 'test_reading', 'test_travel', 
            'test_music', 'test_cooking', 'test_art', 
            'test_movies', 'test_sports', 'test_yoga'
        ], k=random.randint(3, 6))
        
        return {
            'profile': {
                'name': f"TestUser_{random.randint(1000,9999)}",
                'age': age,
                'gender': gender,
                'location': {'lat': lat, 'lon': lon},
                'bio': f"Test profile in {city}",
                'interests': interests,
                'preferences': {
                    'gender': looking_for,
                    'min_age': age - 5,
                    'max_age': age + 5,
                    'max_distance': random.randint(10, 30),
                    'relationship_type': 'test'
                }
            },
            'persona': random.choices(
                list(TEST_PERSONAS.keys()),
                weights=[0.4, 0.3, 0.3]
            )[0],
            'city': city
        }

    def simulate_session(self, user_id, profile, persona):
        """Run a simulated user session"""
        try:
            behavior = TEST_PERSONAS[persona]
            matches_viewed = 0
            messages_sent = 0
            
            # Find matches
            r = self.api.find_matches(user_id, user_id)
            if r.status_code == 200:
                data = r.json()
                if data['status'] == 'success' and data['matches']:
                    matches_viewed = len(data['matches'])
                    
                    # Process potential matches
                    for match in data['matches'][:behavior['swipe_rate']]:
                        if random.random() < 0.3:  # 30% match rate
                            r = self.api.propose_match(
                                user_id, 
                                match['user_id'],
                                user_id
                            )
                            
                            if r.status_code == 200:
                                match_id = r.json()['match_id']
                                
                                # Simulate match response
                                if random.random() < 0.7:  # 70% accept
                                    r = self.api.respond_to_match(
                                        match_id,
                                        match['user_id'],
                                        'accepted',
                                        match['user_id']
                                    )
                                    
                                    if r.status_code == 200 and \
                                       random.random() < behavior['message_rate']:
                                        # Send test message
                                        msg = f"Test message {random.randint(1000,9999)}"
                                        r = self.api.send_message(
                                            match_id,
                                            msg,
                                            user_id
                                        )
                                        if r.status_code == 200:
                                            messages_sent += 1
                        
                        time.sleep(random.uniform(0.5, 1.5))
            
            return matches_viewed, messages_sent
            
        except Exception as e:
            logger.error(f"Session error: {e}")
            return 0, 0

    def run(self):
        """Main simulation loop"""
        while self.running:
            try:
                # Get or create test user
                if random.random() < 0.7 and not self.user_queue.empty():
                    user_id, profile, persona = self.user_queue.get_nowait()
                else:
                    # Create new test user
                    data = self.generate_test_profile()
                    r = self.api.create_profile(data['profile'])
                    if r.status_code == 200:
                        user_id = r.json()['user_id']
                        profile = data['profile']
                        persona = data['persona']
                        logger.info(
                            f"Created test {persona} user {profile['name']}"
                        )
                    else:
                        continue

                # Run test session
                matches, messages = self.simulate_session(
                    user_id, profile, persona)
                
                # Report stats
                self.stats_queue.put({
                    'timestamp': time.time(),
                    'user_id': user_id,
                    'persona': persona,
                    'matches_viewed': matches,
                    'messages_sent': messages
                })
                
                # Maybe requeue user
                if random.random() < TEST_PERSONAS[persona]['login_freq']:
                    self.user_queue.put((user_id, profile, persona))
                
                # Random delay
                time.sleep(random.uniform(1, 3))
                
            except queue.Empty:
                time.sleep(1)
            except Exception as e:
                logger.error(f"Simulation error: {e}")
                time.sleep(5)

class StatsCollector(threading.Thread):
    def __init__(self, stats_queue):
        super().__init__(daemon=True)
        self.stats_queue = stats_queue
        self.running = True
        self.stats = defaultdict(int)
        self.users_by_persona = defaultdict(int)
        self.start_time = time.time()

    def run(self):
        """Collect and report simulation stats"""
        last_report = time.time()
        
        while self.running:
            try:
                while not self.stats_queue.empty():
                    stat = self.stats_queue.get_nowait()
                    self.stats['total_matches'] += stat['matches_viewed']
                    self.stats['total_messages'] += stat['messages_sent']
                    self.users_by_persona[stat['persona']] += 1
                    
                now = time.time()
                if now - last_report >= 60:  # Report every minute
                    runtime = (now - self.start_time) / 3600.0
                    
                    print("\n=== Love Matcher Test Statistics ===")
                    print(f"Test Runtime: {runtime:.1f} hours")
                    print(f"\nTest Activity:")
                    print(f"Matches Viewed: {self.stats['total_matches']}")
                    print(f"Messages Sent: {self.stats['total_messages']}")
                    
                    print(f"\nTest User Distribution:")
                    total_users = sum(self.users_by_persona.values())
                    for persona, count in self.users_by_persona.items():
                        pct = (count/total_users*100) if total_users else 0
                        print(f"{persona}: {count} ({pct:.1f}%)")
                    
                    print("\nTest Rates (per hour):")
                    print(f"Matches: {self.stats['total_matches']/runtime:.1f}")
                    print(f"Messages: {self.stats['total_messages']/runtime:.1f}")
                    print("===================================\n")
                    
                    last_report = now
                    
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Stats error: {e}")
                time.sleep(5)

def run_simulator(num_threads=3):
    """Run the load simulation"""
    print("\n🚀 Starting Love Matcher Test Simulator")
    api = TestAPI()
    
    # Verify API health
    try:
        r = api.verify_health()
        if r.status_code != 200:
            print("❌ API appears to be offline!")
            return
    except:
        print("❌ Cannot connect to API!")
        return

    # Clean any existing test data
    print("\n🧹 Cleaning previous test data...")
    api.cleanup_test_data()

    # Initialize queues
    user_queue = queue.Queue()
    stats_queue = queue.Queue()
    
    # Start stats collector
    stats = StatsCollector(stats_queue)
    stats.start()
    
    # Start simulators
    simulators = []
    for _ in range(num_threads):
        sim = UserSimulator(user_queue, stats_queue)
        sim.start()
        simulators.append(sim)
    
    try:
        print(f"\n✨ Simulation running with {num_threads} threads")
        print("Press Ctrl+C to stop...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down simulation...")
        stats.running = False
        for sim in simulators:
            sim.running = False
        
        # Wait for threads to finish
        stats.join()
        for sim in simulators:
            sim.join()
            
        # Clean up test data
        print("\n🧹 Cleaning up test data...")
        api.cleanup_test_data()
        print("✨ Simulation completed")

if __name__ == '__main__':
    import sys
    threads = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run_simulator(threads)
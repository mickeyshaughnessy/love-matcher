from models import User, Match
import random

def calculate_compatibility_score(user1, user2):
    score = 0
    
    # Age preference
    age_diff = abs(user1.age - user2.age)
    if age_diff <= user1.preferences['max_age_difference']:
        score += 20
    
    # Interests
    common_interests = set(user1.preferences['interests']) & set(user2.preferences['interests'])
    score += len(common_interests) * 10
    
    # Location
    if user1.preferences['location'] == user2.preferences['location']:
        score += 20
    
    # Relationship goals
    if user1.preferences['relationship_goal'] == user2.preferences['relationship_goal']:
        score += 30
    
    # Education level
    if user1.preferences['education_level'] == user2.preferences['education_level']:
        score += 10
    
    return score

def create_match(redis_client, user_id):
    user = User.get(redis_client, user_id)
    if not user:
        return None

    potential_matches = User.get_all(redis_client, include_simulated=user.is_simulated)
    potential_matches = [u for u in potential_matches if u.id != user.id]
    
    if not potential_matches:
        return None
    
    compatibility_scores = [
        (match, calculate_compatibility_score(user, match))
        for match in potential_matches
    ]
    
    compatibility_scores.sort(key=lambda x: x[1], reverse=True)
    top_matches = compatibility_scores[:3]
    selected_match, score = random.choice(top_matches)
    
    new_match = Match(user.id, selected_match.id, score, is_simulated=user.is_simulated)
    new_match.save(redis_client)
    
    return new_match.to_dict()
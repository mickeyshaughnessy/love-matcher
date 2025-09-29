"""
🤔 Match Making Engine Tests
<Features>
- AI-generated profiles with examples
- Location-based testing
- Gender matching
- Red flag detection
"""

import json, random, llm
import match_engine
from datetime import datetime, timedelta

TEST_PROFILE_PROMPT = """Return JSON for male/female matching. Examples:

{
    "summary": "Successful architect who enjoys outdoor adventure and fine dining.",
    "sex": "M",
    "location": "Seattle, WA",
    "age": 35,
    "interests": ["architecture", "hiking", "wine tasting", "travel"],
    "values": ["ambition", "adventure", "culture"],
    "dealbreakers": ["smoking", "lack of career"]
}

{
    "summary": "Creative interior designer with passion for art and healthy living.",
    "sex": "F",
    "location": "Portland, OR",
    "age": 31,
    "interests": ["design", "yoga", "art galleries", "cooking"],
    "values": ["creativity", "health", "growth"],
    "dealbreakers": ["laziness", "rudeness"]
}

Generate a unique profile matching the given sex (M or F)."""

CITIES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"),
    ("Houston", "TX"), ("Phoenix", "AZ"), ("Philadelphia", "PA"),
    ("San Antonio", "TX"), ("San Diego", "CA"), ("Dallas", "TX")
]

def generate_test_profile(profile_type="normal", sex=None):
    # Ensure opposite sex for matching
    if sex is None:
        sex = random.choice(['M', 'F'])
    
    # Add sex to prompt for targeted generation
    targeted_prompt = TEST_PROFILE_PROMPT + f"\nGenerate profile for sex: {sex}"
    response = llm.completion(targeted_prompt)
    
    try:
        profile = json.loads(response)
        profile['sex'] = sex  # Ensure correct sex even if LLM ignores instruction
        
        # Adjust age based on sex (men slightly older on average)
        if sex == 'M':
            profile['age'] = random.randint(28, 45)
        else:
            profile['age'] = random.randint(25, 40)
            
        profile['relationship_history'] = {
            'past_relationships': random.randint(1, 5),
            'longest_duration': f"{random.randint(1,5)} years"
        }
        
        if profile_type == "red_flag":
            profile.update(_generate_red_flags())
        return profile
    except json.JSONDecodeError:
        print(f"⚠️ Error parsing generated profile for {sex}, using fallback")
        return generate_fallback_profile(profile_type, sex)

def _generate_red_flags():
    recent_dates = [(datetime.now() - timedelta(days=x)).strftime("%Y-%m-%d") 
                    for x in range(1, 30)]
    return {
        'profile_history': [
            f"{random.choice(['Harassment', 'Spam', 'Fake photos'])} reported",
            f"Multiple {random.choice(['accounts', 'complaints', 'warnings'])}"
        ],
        'message_samples': [
            random.choice(['hey sexy', 'why u ignore me??', 'send pics', '$$$?']),
            random.choice(['ur loss', 'whatever loser', 'blocked!', 'cash only'])
        ],
        'reported_issues': [
            random.choice(['aggressive messages', 'misleading photos', 'scam']),
            random.choice(['spam behavior', 'solicitation', 'harassment'])
        ]
    }

def generate_fallback_profile(profile_type):
    city, state = random.choice(CITIES)
    base_profile = {
        'summary': "Product manager at a tech startup. Love trying new restaurants and staying active.",
        'sex': random.choice(['M', 'F']),
        'location': f"{city}, {state}",
        'age': random.randint(25, 45),
        'interests': random.sample([
            'hiking', 'photography', 'restaurants', 'yoga', 
            'music', 'travel', 'reading', 'art'
        ], random.randint(3, 4)),
        'values': random.sample([
            'honesty', 'growth', 'family', 'adventure', 'creativity'
        ], random.randint(3, 4)),
        'dealbreakers': random.sample([
            'smoking', 'lack of ambition', 'poor communication'
        ], random.randint(2, 3)),
        'relationship_history': {
            'past_relationships': random.randint(1, 5),
            'longest_duration': f"{random.randint(1,5)} years"
        }
    }
    if profile_type == "red_flag":
        base_profile.update(_generate_red_flags())
    return base_profile

def generate_test_messages(quality="good"):
    if quality == "good":
        topics = ['interests', 'travel', 'career', 'local']
        selected = random.choice(topics)
        return [
            {'sender': 'person1', 'content': f"I noticed we both love {selected}! What got you into that?"},
            {'sender': 'person2', 'content': f"Yes! I've been into {selected} for years. Started when..."},
            {'sender': 'person1', 'content': "That's fascinating! Would you like to share experiences sometime?"},
            {'sender': 'person2', 'content': "Sure! I'd love to hear more about your adventures too."},
            {'sender': 'person1', 'content': "Great! Let's plan something next week?"}
        ]
    else:
        return [
            {'sender': 'person1', 'content': random.choice(['hey', 'sup', 'u up?', 'pics?'])},
            {'sender': 'person2', 'content': random.choice(['who?', 'no', 'bye', 'blocked'])},
            {'sender': 'person1', 'content': "wanna meet up?"},
            {'sender': 'person2', 'content': "I prefer to chat first"},
            {'sender': 'person1', 'content': random.choice(['whatever', 'ur loss', 'blocked'])}
        ]

def format_profile(profile):
    return f"""
📋 {profile['summary']}

👤 {profile['sex']}, {profile['age']} • {profile['location']}
🎯 {', '.join(profile['interests'])}
💭 {', '.join(profile['values'])}
🚫 {', '.join(profile['dealbreakers'])}
💝 {profile['relationship_history']['past_relationships']} past relationships, 
   longest: {profile['relationship_history']['longest_duration']}"""

def main():
    print("\n💕 Love Matcher Analysis Tests\n")
    
    # Test 1: Ideal Heterosexual Match (Similar Age)
    print("\n🔄 Test 1: Ideal Match (Similar Age)")
    male = generate_test_profile(sex='M')
    female = generate_test_profile(sex='F')
    # Ensure similar age
    female['age'] = male['age'] - random.randint(1, 3)
    female['location'] = male['location']  # Same location for ideal match
    
    print("\nMale Profile:", format_profile(male))
    print("\nFemale Profile:", format_profile(female))
    score, analysis = match_engine.generate_match_analysis(male, female)
    print(f"\nMatch Score: {score:.1f}/100")
    print(f"Analysis:\n{analysis}")

    # Test 2: Age Gap Test
    print("\n🔄 Test 2: Age Gap Test")
    older_male = generate_test_profile(sex='M')
    younger_female = generate_test_profile(sex='F')
    older_male['age'] = 42
    younger_female['age'] = 27
    
    print("\nMale Profile:", format_profile(older_male))
    print("\nFemale Profile:", format_profile(younger_female))
    score, analysis = match_engine.generate_match_analysis(older_male, younger_female)
    print(f"\nMatch Score: {score:.1f}/100")
    print(f"Analysis:\n{analysis}")

    # Test 3: Location Mismatch
    print("\n🔄 Test 3: Location Distance Test")
    west_coast_male = generate_test_profile(sex='M')
    east_coast_female = generate_test_profile(sex='F')
    west_coast_male['location'] = "Seattle, WA"
    east_coast_female['location'] = "New York, NY"
    
    print("\nMale Profile:", format_profile(west_coast_male))
    print("\nFemale Profile:", format_profile(east_coast_female))
    score, analysis = match_engine.generate_match_analysis(west_coast_male, east_coast_female)
    print(f"\nMatch Score: {score:.1f}/100")
    print(f"Analysis:\n{analysis}")

    # Test 4: Incompatible Values
    print("\n🔄 Test 4: Value Mismatch Test")
    career_male = generate_test_profile(sex='M')
    family_female = generate_test_profile(sex='F')
    career_male['values'] = ["ambition", "wealth", "success", "adventure"]
    family_female['values'] = ["family", "tradition", "stability", "spirituality"]
    
    print("\nMale Profile:", format_profile(career_male))
    print("\nFemale Profile:", format_profile(family_female))
    score, analysis = match_engine.generate_match_analysis(career_male, family_female)
    print(f"\nMatch Score: {score:.1f}/100")
    print(f"Analysis:\n{analysis}")

    # Test 5: Red Flag Detection
    print("\n🔄 Test 5: Red Flag Detection")
    normal_female = generate_test_profile(sex='F')
    red_flag_male = generate_test_profile("red_flag", sex='M')
    
    print("\nNormal Profile:", format_profile(normal_female))
    print("\nRed Flag Profile:", format_profile(red_flag_male))
    print("\n⚠️ Red Flags:")
    for flag in red_flag_male['profile_history']:
        print(f"• {flag}")
    for msg in red_flag_male['message_samples']:
        print(f"• Message: {msg}")
    
    risk_score, risk_analysis = match_engine.check_red_flags(red_flag_male)
    print(f"\nRisk Score: {risk_score:.1f}/100")
    print(f"Analysis: {risk_analysis}")

    # Test 6: Communication Patterns
    print("\n🔄 Test 6: Communication Analysis")
    good_msgs = generate_test_messages("good")
    bad_msgs = generate_test_messages("bad")

    print("\n📱 Healthy Communication:")
    for msg in good_msgs:
        print(f"{'→ M:' if msg['sender']=='person1' else '← F:'} {msg['content']}")
    score1, analysis1 = match_engine.analyze_conversation(good_msgs)
    print(f"\nScore: {score1:.1f}/100")
    print(f"Analysis: {analysis1}")

    print("\n📱 Problematic Communication:")
    for msg in bad_msgs:
        print(f"{'→ M:' if msg['sender']=='person1' else '← F:'} {msg['content']}")
    score2, analysis2 = match_engine.analyze_conversation(bad_msgs)
    print(f"\nScore: {score2:.1f}/100")
    print(f"Analysis: {analysis2}")

if __name__ == "__main__":
    main()
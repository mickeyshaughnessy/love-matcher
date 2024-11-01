"""
🤔 Match Making Engine Prompts
Focus areas:
- Initial compatibility assessment
- Communication style analysis 
- Relationship goals alignment
- Red flag detection
- Long-term potential scoring
"""

import json, random, re, llm

COMPATIBILITY_PROMPT = """Analyze the compatibility between these two people for a potential long-term relationship match:

Person 1: {person1_summary}
Age: {person1_age}
Interests: {person1_interests}
Values: {person1_values}
Relationship Goals: {person1_goals}

Person 2: {person2_summary} 
Age: {person2_age}
Interests: {person2_interests}
Values: {person2_values}
Relationship Goals: {person2_goals}

Consider:
1. Core values alignment (40%)
2. Life goals compatibility (30%) 
3. Interest overlap (20%)
4. Age compatibility (10%)

Score each category 0-100 and provide a weighted total.
Highlight potential areas of strong compatibility and possible challenges.
Only recommend proceeding if the weighted score exceeds 70.
"""

COMMUNICATION_ANALYSIS_PROMPT = """Analyze the initial message exchange between these potential matches:

Messages:
{message_history}

Evaluate:
1. Engagement level (Do both parties ask questions and show interest?)
2. Communication style match (Formal vs casual, detailed vs brief)
3. Red flags (Pushy behavior, inappropriate content, misaligned expectations)
4. Emotional intelligence indicators

Provide a conversation health score 0-100 and recommendation to:
A) Continue naturally
B) Provide conversation prompts
C) Flag for review
D) Discontinue matching
"""

RELATIONSHIP_GOALS_PROMPT = """Assess the alignment of relationship intentions and timelines:

Person 1 Goals: {person1_goals}
Person 1 Timeline: {person1_timeline}
Person 1 Deal Breakers: {person1_dealbreakers}

Person 2 Goals: {person2_goals}
Person 2 Timeline: {person2_timeline}
Person 2 Deal Breakers: {person2_dealbreakers}

Score alignment 0-100 on:
1. Ultimate relationship goals
2. Timeline compatibility
3. Deal breaker conflicts
4. Life stage alignment

Provide specific areas of alignment and potential conflict.
Only recommend proceeding if no deal breakers are triggered and score exceeds 75.
"""

RED_FLAGS_PROMPT = """Analyze user behavior patterns for potential red flags:

Profile History: {profile_history}
Message Samples: {message_samples}
Reported Issues: {reported_issues}

Check for:
1. Inconsistent information
2. Manipulation patterns
3. Aggressive or inappropriate behavior
4. Spam or commercial intent
5. Identity concerns

Rate risk level 0-100 where:
0-20: Proceed normally
21-50: Monitor closely
51-80: Review required
81-100: Immediate action needed
"""

STABILITY_SCORE_PROMPT = """Evaluate the potential for a stable, long-term match:

Relationship History:
Person 1: {person1_history}
Person 2: {person2_history}

Consider:
1. Past relationship duration
2. Growth from previous relationships
3. Current life stability
4. Shared future vision
5. Support system compatibility

Score stability potential 0-100 and identify:
- Key stability indicators
- Areas needing growth
- Recommended pace of relationship development
- Support resources that may help
"""

def generate_match_analysis(person1, person2):
    """Generate comprehensive match analysis using all prompts"""
    compatibility_input = COMPATIBILITY_PROMPT.format(
        person1_summary=person1['summary'],
        person1_age=person1['age'],
        person1_interests=", ".join(person1['interests']),
        person1_values=", ".join(person1['values']),
        person1_goals=person1['relationship_goals'],
        person2_summary=person2['summary'],
        person2_age=person2['age'],
        person2_interests=", ".join(person2['interests']),
        person2_values=", ".join(person2['values']), 
        person2_goals=person2['relationship_goals']
    )
    
    compatibility_result = llm.completion(compatibility_input)
    compatibility_score = _extract_score(compatibility_result)

    goals_input = RELATIONSHIP_GOALS_PROMPT.format(
        person1_goals=person1['relationship_goals'],
        person1_timeline=person1['timeline'],
        person1_dealbreakers=person1['dealbreakers'],
        person2_goals=person2['relationship_goals'],
        person2_timeline=person2['timeline'],
        person2_dealbreakers=person2['dealbreakers']
    )
    
    goals_result = llm.completion(goals_input)
    goals_score = _extract_score(goals_result)

    analysis = f"""Match Analysis Results:
Compatibility Score: {compatibility_score}
Goals Alignment Score: {goals_score}
Overall Match Score: {(compatibility_score + goals_score) / 2}

Compatibility Insights:
{compatibility_result}

Goals Alignment Details:
{goals_result}
"""
    
    return (compatibility_score + goals_score) / 2, analysis

def analyze_conversation(messages):
    """Analyze message exchange between potential matches"""
    message_history = "\n".join([
        f"{msg['sender']}: {msg['content']}" 
        for msg in messages
    ])
    
    analysis_input = COMMUNICATION_ANALYSIS_PROMPT.format(
        message_history=message_history
    )
    
    result = llm.completion(analysis_input)
    score = _extract_score(result)
    
    return score, result

def check_red_flags(user_data):
    """Analyze user data for potential red flags"""
    red_flags_input = RED_FLAGS_PROMPT.format(
        profile_history=json.dumps(user_data['profile_history']),
        message_samples=json.dumps(user_data['message_samples']),
        reported_issues=json.dumps(user_data['reported_issues'])
    )
    
    result = llm.completion(red_flags_input)
    risk_score = _extract_score(result)
    
    return risk_score, result

def evaluate_stability(person1, person2):
    """Evaluate potential match stability"""
    stability_input = STABILITY_SCORE_PROMPT.format(
        person1_history=json.dumps(person1['relationship_history']),
        person2_history=json.dumps(person2['relationship_history'])
    )
    
    result = llm.completion(stability_input)
    stability_score = _extract_score(result)
    
    return stability_score, result

def _extract_score(result):
    """Extract numerical score from LLM response"""
    try:
        scores = re.findall(r'(\d+)%|Score:\s*(\d+)', result)
        if scores:
            score = next(int(n) for n in scores[0] if n)
            return min(100, max(0, score))
    except Exception:
        pass
    return 50.0  # Default middle score if parsing fails

if __name__ == "__main__":
    print("\n💕 Love Matcher Analysis Tests\n")
    
    # Test Case 1: High Compatibility Match
    ideal_person1 = {
        'summary': "Outgoing software engineer who loves hiking and photography",
        'age': 28,
        'interests': ['hiking', 'photography', 'coding', 'travel'],
        'values': ['honesty', 'adventure', 'growth', 'family'],
        'relationship_goals': 'long-term partnership leading to marriage',
        'timeline': '2-3 years',
        'dealbreakers': ['smoking', 'lack of ambition'],
        'relationship_history': {'past_relationships': 2, 'longest_duration': '2 years'}
    }
    
    ideal_person2 = {
        'summary': "Creative photographer looking for genuine connection",
        'age': 30,
        'interests': ['photography', 'hiking', 'art', 'yoga'],
        'values': ['creativity', 'honesty', 'health', 'family'],
        'relationship_goals': 'marriage and family',
        'timeline': '2-3 years',
        'dealbreakers': ['drugs', 'lack of career'],
        'relationship_history': {'past_relationships': 3, 'longest_duration': '3 years'}
    }

    # Test Case 2: Mismatched Goals
    casual_person = {
        'summary': "Free spirit looking for fun and adventure",
        'age': 25,
        'interests': ['parties', 'travel', 'music', 'surfing'],
        'values': ['freedom', 'spontaneity', 'fun'],
        'relationship_goals': 'casual dating',
        'timeline': 'no specific timeline',
        'dealbreakers': ['commitment pressure', 'traditional values'],
        'relationship_history': {'past_relationships': 5, 'longest_duration': '6 months'}
    }

    # Test Case 3: Red Flag Profile
    red_flag_person = {
        'summary': "Just looking to have a good time",
        'age': 35,
        'interests': ['nightlife', 'luxury', 'shopping'],
        'values': ['success', 'wealth', 'status'],
        'relationship_goals': 'undefined',
        'timeline': 'flexible',
        'dealbreakers': [],
        'relationship_history': {'past_relationships': 12, 'longest_duration': '3 months'},
        'profile_history': ['multiple reports', 'inconsistent info'],
        'message_samples': ['hey beautiful', 'why no response??', 'your loss'],
        'reported_issues': ['aggressive messages', 'misleading photos']
    }

    print("🔄 Test 1: High Compatibility Match")
    score, analysis = generate_match_analysis(ideal_person1, ideal_person2)
    print(f"Match Score: {score:.1f}/100")
    print(f"Analysis Preview: {analysis.split('\\n')[0]}...\n")

    print("🔄 Test 2: Mismatched Goals")
    score, analysis = generate_match_analysis(ideal_person1, casual_person)
    print(f"Match Score: {score:.1f}/100")
    print(f"Analysis Preview: {analysis.split('\\n')[0]}...\n")

    print("🔄 Test 3: Red Flag Detection")
    risk_score, risk_analysis = check_red_flags(red_flag_person)
    print(f"Risk Score: {risk_score:.1f}/100")
    print(f"Risk Analysis Preview: {risk_analysis.split('\\n')[0]}...\n")

    print("🔄 Test 4: Conversation Analysis")
    # Good conversation
    good_messages = [
        {'sender': 'person1', 'content': "Hi! I noticed you're into photography too. What kind of shots do you like taking?"},
        {'sender': 'person2', 'content': "Hey! Yes, I love landscape and street photography. I saw your hiking photos - they're amazing! What's your favorite trail?"},
        {'sender': 'person1', 'content': "Thanks! I love the Crystal Lakes trail. Would you be interested in doing a photo hike sometime?"}
    ]
    
    # Problematic conversation
    bad_messages = [
        {'sender': 'person1', 'content': "hey"},
        {'sender': 'person2', 'content': "hi"},
        {'sender': 'person1', 'content': "wanna meet up?"},
        {'sender': 'person2', 'content': "I prefer to chat first"},
        {'sender': 'person1', 'content': "whatever, ur loss"}
    ]

    score1, _ = analyze_conversation(good_messages)
    score2, _ = analyze_conversation(bad_messages)
    print(f"Good Conversation Score: {score1:.1f}/100")
    print(f"Bad Conversation Score: {score2:.1f}/100\n")
"""
🤔 Match Making Engine
<Features>
- Heterosexual relationship matching
- Location and lifestyle compatibility
- Age and life stage alignment
- Values and interests analysis
"""

import json, random, re, llm
from prompts import (COMPATIBILITY_PROMPT, COMMUNICATION_ANALYSIS_PROMPT,
                    RED_FLAGS_PROMPT, STABILITY_SCORE_PROMPT)

def _extract_score(result):
    try:
        scores = re.findall(r'(\d+)%|Score:\s*(\d+)', result)
        if scores:
            score = next(int(n) for n in scores[0] if n)
            return min(100, max(0, score))
    except Exception:
        pass
    return 50.0

def _calculate_location_score(loc1, loc2):
    city1, state1 = loc1.split(", ")
    city2, state2 = loc2.split(", ")
    if city1 == city2: return 100
    if state1 == state2: return 75
    return 50

def _calculate_age_compatibility(age1, age2):
    age_gap = abs(age1 - age2)
    if age_gap <= 5: return 100
    if age_gap <= 10: return 80
    if age_gap <= 15: return 60
    return max(0, 100 - (age_gap * 5))

def _check_basic_compatibility(person1, person2):
    # Check for heterosexual match
    if person1['sex'] == person2['sex']:
        return False, "Same sex match not supported"
        
    # Check for reasonable age gap (max 20 years)
    age_gap = abs(person1['age'] - person2['age'])
    if age_gap > 20:
        return False, "Age gap too large"

    # Make sure male isn't significantly younger
    male = person1 if person1['sex'] == 'M' else person2
    female = person2 if person1['sex'] == 'M' else person1
    if male['age'] < female['age'] - 5:
        return False, "Male significantly younger than female"
        
    return True, "Basic compatibility checks passed"

def _calculate_interests_score(interests1, interests2):
    common = set(interests1) & set(interests2)
    total = set(interests1) | set(interests2)
    return (len(common) / len(total)) * 100

def _calculate_values_score(values1, values2):
    common = set(values1) & set(values2)
    total = set(values1) | set(values2)
    return (len(common) / len(total)) * 100

def generate_match_analysis(person1, person2):
    # Check basic compatibility first
    is_compatible, reason = _check_basic_compatibility(person1, person2)
    if not is_compatible:
        return 0, f"Match failed: {reason}"

    # Calculate component scores
    location_score = _calculate_location_score(person1['location'], person2['location'])
    age_score = _calculate_age_compatibility(person1['age'], person2['age'])
    interests_score = _calculate_interests_score(person1['interests'], person2['interests'])
    values_score = _calculate_values_score(person1['values'], person2['values'])

    # Get LLM analysis for personality compatibility
    compatibility_input = COMPATIBILITY_PROMPT.format(
        person1_summary=person1['summary'],
        person1_age=person1['age'],
        person1_sex=person1['sex'],
        person1_location=person1['location'],
        person1_interests=", ".join(person1['interests']),
        person1_values=", ".join(person1['values']),
        person2_summary=person2['summary'],
        person2_age=person2['age'],
        person2_sex=person2['sex'],
        person2_location=person2['location'],
        person2_interests=", ".join(person2['interests']),
        person2_values=", ".join(person2['values'])
    )
    
    compatibility_result = llm.completion(compatibility_input)
    personality_score = _extract_score(compatibility_result)
    
    # Check dealbreakers
    dealbreaker_match = any(d in person2['values'] for d in person1['dealbreakers']) or \
                       any(d in person1['values'] for d in person2['dealbreakers'])
    
    if dealbreaker_match:
        return 0, "Match failed due to dealbreaker conflict."

    # Calculate weighted final score
    final_score = (
        location_score * 0.2 +
        age_score * 0.15 +
        interests_score * 0.25 +
        values_score * 0.25 +
        personality_score * 0.15
    )

    analysis = f"""Match Analysis Results:

Basic Compatibility:
• {person1['sex']}/{person2['sex']} Match
• Age Gap: {abs(person1['age'] - person2['age'])} years
• Location: {"Same City" if location_score == 100 else "Same State" if location_score == 75 else "Different State"}

Component Scores:
• Location Compatibility: {location_score:.1f}/100
• Age Compatibility: {age_score:.1f}/100
• Shared Interests: {interests_score:.1f}/100
• Value Alignment: {values_score:.1f}/100
• Personality Match: {personality_score:.1f}/100

Overall Match Score: {final_score:.1f}/100

Compatibility Insights:
{compatibility_result}

Location Details:
• Person 1: {person1['location']} ({person1['sex']}, {person1['age']})
• Person 2: {person2['location']} ({person2['sex']}, {person2['age']})

Common Ground:
• Interests: {', '.join(set(person1['interests']) & set(person2['interests']))}
• Values: {', '.join(set(person1['values']) & set(person2['values']))}
"""
    
    return final_score, analysis

def analyze_conversation(messages):
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
    red_flags_input = RED_FLAGS_PROMPT.format(
        profile_history=json.dumps(user_data.get('profile_history', [])),
        message_samples=json.dumps(user_data.get('message_samples', [])),
        reported_issues=json.dumps(user_data.get('reported_issues', []))
    )
    
    result = llm.completion(red_flags_input)
    risk_score = _extract_score(result)
    
    return risk_score, result

def evaluate_stability(person1, person2):
    stability_input = STABILITY_SCORE_PROMPT.format(
        person1_history=json.dumps(person1['relationship_history']),
        person2_history=json.dumps(person2['relationship_history'])
    )
    
    result = llm.completion(stability_input)
    stability_score = _extract_score(result)
    
    return stability_score, result
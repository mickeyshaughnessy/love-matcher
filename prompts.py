"""
🤔 Match Making Engine Prompts
<Prompts>
- Compatibility assessment
- Conversation analysis
- Safety checks
- Stability evaluation
"""

COMPATIBILITY_PROMPT = """Analyze match compatibility:

Person 1:
Summary: {person1_summary}
Age: {person1_age}
Sex: {person1_sex}
Location: {person1_location}
Interests: {person1_interests}
Values: {person1_values}

Person 2:
Summary: {person2_summary}
Age: {person2_age}
Sex: {person2_sex}
Location: {person2_location}
Interests: {person2_interests}
Values: {person2_values}

Consider:
1. Age gap (15%)
2. Common interests (35%)
3. Value alignment (35%)
4. Communication style from summaries (15%)

Score 0-100. Highlight key compatibilities and concerns."""

COMMUNICATION_ANALYSIS_PROMPT = """Analyze conversation quality:

Messages:
{message_history}

Rate 0-100 on:
1. Engagement
2. Communication style match
3. Red flags
4. Emotional intelligence

Recommend: Continue/Guide/Review/Stop"""

RED_FLAGS_PROMPT = """Analyze safety concerns:

History: {profile_history}
Messages: {message_samples}
Reports: {reported_issues}

Check for:
1. Inconsistency
2. Manipulation
3. Aggression
4. Spam/scams
5. Identity issues

Rate risk 0-100"""

STABILITY_SCORE_PROMPT = """Evaluate relationship stability potential:

Person 1 History: {person1_history}
Person 2 History: {person2_history}

Rate 0-100 based on:
1. Past relationship patterns
2. Growth indicators
3. Stability signals
4. Compatibility factors"""
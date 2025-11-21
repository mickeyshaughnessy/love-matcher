# Matching System Implementation

## Overview
This document describes the complete matching system implementation for Love-Matcher, including LLM-powered compatibility scoring, match acceptance workflow, and private chat functionality.

## Key Features Implemented

### 1. LLM-Based Match Compatibility Scoring
**Location**: `prompts.py` (line 395-479), `run_matching.py` (line 68-222)

- Added `MATCH_COMPATIBILITY_PROMPT` that instructs the LLM to analyze two profiles
- Evaluates matches across 10 categories:
  - Critical: Values alignment, family/children, life stage, relationship fundamentals
  - Important: Lifestyle, social energy, health/wellbeing, financial/career
  - Enhancement: Shared interests, practical alignment
- Returns JSON with score (0-100), reasoning, strengths, and concerns
- Uses OpenRouter `/completion` endpoint with temperature=0.3 for consistency
- Includes fallback to rule-based scoring if LLM fails

### 2. Match Acceptance Workflow
**Location**: `handlers.py` (line 588-653), Profile JSON structure

#### Match States:
- **Pending**: Match created by algorithm, neither user has accepted
- **User Accepted**: One user accepted, waiting for other user
- **Mutual Acceptance**: Both users accepted - chat enabled

#### Profile Fields Added:
- `match_accepted`: Boolean indicating if user accepted current match
- `match_accepted_at`: Timestamp of acceptance
- `match_analysis`: LLM analysis object (score, reasoning, strengths, concerns)

#### API Endpoints:
- `POST /match/accept` - Accept current match
- `POST /match/reject` - Decline match (returns both users to matching pool)
- `GET /match` - Returns match with acceptance status

### 3. Gender-Based Matching
**Location**: `prompts.py` (line 22, 219, 230), `handlers.py` (line 422-431), `run_matching.py` (line 272-283)

- Added `gender` as a dimension in the 29-dimension profile framework
- Chat AI asks about gender early in profile building
- Gender stored both in `dimensions` and at profile level for matching efficiency
- Matching algorithm enforces heterosexual matching (male with female only)
- Validates gender values are in valid set: `{male, female, m, f}`

### 4. Private Chat After Mutual Acceptance
**Location**: `handlers.py` (line 676-764), `index.html` (line 1805-1876)

#### Chat Access Control:
- **Before Acceptance**: Users see match preview (age, location, completion %)
- **After Acceptance**: Users see waiting message if other hasn't accepted
- **Mutual Acceptance**: Full profile JSON visible + private chat enabled

#### Backend Changes:
- `send_match_message()`: Requires mutual acceptance (403 if not met)
- `get_match_messages()`: Returns empty array if not mutually accepted
- `get_current_match()`: Returns different data based on acceptance state

#### Frontend Changes:
- Match card shows accept/decline buttons when pending
- Shows "waiting for match response" when user accepted but match hasn't
- Shows full profile JSON and chat interface after mutual acceptance
- Displays LLM compatibility analysis (reasoning, strengths, concerns)

### 5. Run Matching Script Updates
**Location**: `run_matching.py` (line 300-469)

#### Key Changes:
- Replaced `calculate_compatibility_score()` with LLM-based version
- Returns tuple: `(score, analysis)` instead of just `score`
- Stores `match_accepted=False` when creating new matches
- Stores `match_analysis` object with LLM reasoning
- Only matches active, eligible, opposite-gender profiles
- Gender validation: skips candidates without valid gender or same gender

#### Match Creation Process:
1. Load all active, unmatched profiles
2. Filter by eligibility (age 18+, payment status, gender specified)
3. For each user, find best compatible opposite-gender match using LLM
4. Create mutual match with `match_accepted=False` for both users
5. Initialize match chat with analysis stored

### 6. Frontend Updates
**Location**: `index.html` (line 1758-1876, 1913-1969, 2118-2173)

#### Match Display:
- Shows compatibility percentage from LLM
- Displays LLM analysis (reasoning, strengths, considerations)
- Shows acceptance status for both users
- Preview mode (limited info) vs full profile mode (after acceptance)

#### User Actions:
- "Accept Match" button - triggers `/match/accept` endpoint
- "Decline Match" button - triggers `/match/reject` endpoint
- Chat interface only shown after mutual acceptance
- Real-time message loading when chat is available

## API Endpoints Summary

### Matching Endpoints:
- `GET /match` - Get current match with acceptance status
- `POST /match/accept` - Accept current match
- `POST /match/reject` - Decline and clear match
- `POST /match/toggle` - Toggle active/inactive status

### Chat Endpoints (Mutual Acceptance Required):
- `GET /match/messages` - Get messages with current match
- `POST /match/messages` - Send message to match
  - Returns 403 if not mutually accepted

### Admin Endpoints:
- `POST /admin/run-matching` - Manually trigger matching algorithm
- `GET /admin/matching-logs` - View matching run history

## Database Schema Changes

### Profile JSON Structure:
```json
{
  "user_id": "email_domain_com",
  "email": "user@domain.com",
  "gender": "male",  // NEW: Stored at profile level
  "age": 25,
  "dimensions": {
    "gender": "male",  // Also stored in dimensions
    "location": "New York",
    // ... 27 other dimensions
  },
  "current_match_id": "match_user_id",
  "match_score": 85,
  "match_accepted": false,  // NEW
  "match_accepted_at": "2025-11-07T...",  // NEW
  "match_analysis": {  // NEW
    "score": 85,
    "reasoning": "Strong values alignment...",
    "strengths": "Shared religion, compatible life goals",
    "concerns": "Different social energy levels"
  },
  "matched_at": "2025-11-07T...",
  "rejected_matches": ["user1_id", "user2_id"],
  "matching_active": true,
  "matching_eligible": true
}
```

### Match Chat JSON Structure:
```json
{
  "user1_id": "user_a",
  "user2_id": "user_b",
  "created_at": "2025-11-07T...",
  "match_score": 85,  // NEW
  "match_analysis": {},  // NEW
  "messages": [
    {
      "from": "user_a",
      "message": "Hi!",
      "timestamp": "2025-11-07T..."
    }
  ]
}
```

## Crontab Setup

To run matching daily at 3 AM:
```bash
0 3 * * * cd /path/to/love-matcher && python3 run_matching.py >> /var/log/lovedashmatcher_matching.log 2>&1
```

For testing (dry run):
```bash
python3 run_matching.py --dry-run
```

## Testing the Flow

### 1. Create Two Test Users:
```bash
# User 1 (Male)
curl -X POST http://localhost:5009/register \
  -H "Content-Type: application/json" \
  -d '{"email":"male@test.com","password":"test123","age":25}'

# User 2 (Female)
curl -X POST http://localhost:5009/register \
  -H "Content-Type: application/json" \
  -d '{"email":"female@test.com","password":"test123","age":24}'
```

### 2. Build Profiles:
- Chat with AI to fill out dimensions
- Make sure to specify gender early (male/female)
- Fill at least 15-20 dimensions for good matching

### 3. Run Matching:
```bash
# Dry run first to see what would happen
python3 run_matching.py --dry-run

# Actual matching
python3 run_matching.py
```

### 4. Test Acceptance Flow:
1. Login as User 1, go to /match tab
2. See match card with LLM analysis
3. Click "Accept Match"
4. See "waiting for match response" message
5. Login as User 2, go to /match tab
6. Click "Accept Match"
7. Both users now see full profile JSON and can chat

### 5. Test Chat:
- After mutual acceptance, send messages
- Messages appear in real-time for both users
- Both can see each other's full 29-dimension profile

## Key Design Decisions

### 1. Why LLM-Based Matching?
- Traditional rule-based matching can't understand nuanced compatibility
- LLM can reason about trade-offs (e.g., different hobbies but aligned values)
- Provides human-readable explanations for matches
- Can adapt to complex multi-dimensional relationships

### 2. Why Acceptance Workflow?
- Prevents one-sided matches where only one person is interested
- Protects privacy - full profile only visible after mutual interest
- Reduces ghost matches and improves engagement
- Enables cleaner rejection flow without exposing personal info

### 3. Why Store Gender at Profile Level?
- Matching algorithm needs fast gender filtering (no need to parse dimensions)
- Also stored in dimensions for completeness and LLM context
- Enables efficient database queries in future scaling

### 4. Why OpenRouter /completion endpoint?
- Simpler than chat endpoint for single-turn scoring tasks
- Lower latency and cost
- Better for consistent structured output (JSON)
- No conversation history needed

## Future Enhancements

1. **Notification System**: Email/push notifications when match accepts
2. **Match Expiration**: Matches expire after 7 days if not accepted
3. **Rematch Timer**: Wait 30 days before re-matching rejected pairs
4. **Batch Scoring**: Score top N candidates then pick best (avoid sequential LLM calls)
5. **Profile Photos**: Add photo upload and display after acceptance
6. **Match History**: View past accepted/rejected matches
7. **Matching Preferences**: Let users set age range, location radius preferences
8. **Read Receipts**: Show when match has read messages
9. **Video Chat**: Integrate video calling after X messages exchanged

## Troubleshooting

### Match not created:
- Check both users have `matching_active=true`
- Verify both users have `matching_eligible=true` (age 18+)
- Ensure genders are specified and opposite
- Check matching logs: `GET /admin/matching-logs`

### Chat not working:
- Verify `match_accepted=true` for BOTH users
- Check match_messages endpoint returns `mutual_acceptance=true`
- Look for 403 errors indicating acceptance required

### LLM scoring fails:
- Check OpenRouter API key is valid
- Verify model is available (fallback to rule-based if LLM fails)
- Check matching logs for error messages
- Increase timeout if needed (currently 30s)

### Gender not extracted:
- Ensure chat AI asks about gender early
- Check dimension parsing in chat logs
- Verify gender normalization logic catches edge cases
- Gender stored as lowercase 'male' or 'female'

## Monitoring

### Key Metrics to Track:
- Daily match success rate (% of eligible users matched)
- Match acceptance rate (% of matches accepted)
- Mutual acceptance rate (% reaching chat stage)
- Message engagement after mutual acceptance
- LLM scoring success rate vs fallback usage
- Average compatibility scores
- Time to acceptance after match creation

### Logs to Monitor:
- `/var/log/lovedashmatcher_matching.log` - Daily matching runs
- Server logs for API endpoint errors
- OpenRouter API usage and costs
- S3 read/write operations

## Conclusion

The matching system is now fully functional with:
- ✅ LLM-powered compatibility scoring
- ✅ Male-female heterosexual matching
- ✅ Accept/decline workflow
- ✅ Privacy-protected profiles until acceptance
- ✅ Private chat after mutual acceptance
- ✅ Gender collection and validation
- ✅ Daily cron job support
- ✅ Comprehensive error handling and fallbacks

The system prioritizes traditional marriage compatibility while providing modern UX through AI-powered insights and mutual consent mechanisms.

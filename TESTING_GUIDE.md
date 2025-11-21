# Love-Matcher Testing Guide

## Quick Testing Checklist

### 1. Server Startup Test
```bash
cd /Users/michaelshaughnessy/Repos/love-matcher
python3 api_server.py
```
Expected output:
```
🔷 Love-Matcher API Server Starting
S3 Bucket: mithrilmedia
S3 Prefix: lovedashmatcher/
LLM Model: meta-llama/llama-3.2-3b-instruct:free
Server: http://0.0.0.0:5009
```

### 2. Create Test Users

#### User 1 (Male, 25 years old)
```bash
curl -X POST http://localhost:5009/register \
  -H "Content-Type: application/json" \
  -d '{"email":"testmale@example.com","password":"test123","age":25}'
```

Expected response:
```json
{
  "token": "eyJ...",
  "user_id": "testmale_example_com",
  "member_number": 1,
  "matching_eligible": true,
  "is_free_member": true,
  "message": "Welcome! You're member #1 with free lifetime access..."
}
```

#### User 2 (Female, 24 years old)
```bash
curl -X POST http://localhost:5009/register \
  -H "Content-Type: application/json" \
  -d '{"email":"testfemale@example.com","password":"test123","age":24}'
```

### 3. Build Profiles via Chat

#### Login and Get Token
```bash
# Login as male user
curl -X POST http://localhost:5009/login \
  -H "Content-Type: application/json" \
  -d '{"email":"testmale@example.com","password":"test123"}'
```

Save the token from response: `export TOKEN1="eyJ..."`

#### Chat to Build Profile (Example sequence)
```bash
# Set gender (IMPORTANT - required for matching)
curl -X POST http://localhost:5009/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1" \
  -d '{"message":"I am male"}'

# Add location
curl -X POST http://localhost:5009/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1" \
  -d '{"message":"I live in New York"}'

# Add religion
curl -X POST http://localhost:5009/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1" \
  -d '{"message":"I am Christian and it is important to me"}'

# Continue for 10-15 more dimensions...
```

Repeat for User 2 (female user) with different values.

### 4. Test Matching Algorithm

#### Dry Run (No changes made)
```bash
python3 run_matching.py --dry-run
```

Expected output:
```
🎯 Love-Matcher Daily Matching (DRY RUN)
Run time: 2025-11-07T...
📂 Loading profiles from S3...
✓ Found 2 total profile files in S3
✓ Loaded 2 valid profiles
...
💡 LLM Match Score: 75% - Strong values alignment...
✅ Matched testmale_example_com with testfemale_example_com (score: 75%)
✓ Matching complete: 1 new matches created
```

#### Actual Matching
```bash
python3 run_matching.py
```

### 5. Test Match Acceptance Flow

#### Get Current Match (User 1)
```bash
curl -X GET http://localhost:5009/match \
  -H "Authorization: Bearer $TOKEN1"
```

Expected response:
```json
{
  "match": {
    "match_id": "testfemale_example_com",
    "age": 24,
    "match_score": 75,
    "matched_at": "2025-11-07T...",
    "user_accepted": false,
    "match_accepted": false,
    "mutual_acceptance": false,
    "match_analysis": {
      "score": 75,
      "reasoning": "Strong values alignment with compatible life goals",
      "strengths": "Shared religious values, similar age and location",
      "concerns": "May need to discuss career priorities"
    },
    "preview": {
      "age": 24,
      "location": "New York",
      "completion_percentage": 52
    }
  }
}
```

#### Accept Match (User 1)
```bash
curl -X POST http://localhost:5009/match/accept \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1"
```

Expected response:
```json
{
  "success": true,
  "match_accepted": true,
  "mutual_acceptance": false,
  "message": "Match accepted! Chat will be enabled when both users accept."
}
```

#### Check Status (User 1)
```bash
curl -X GET http://localhost:5009/match \
  -H "Authorization: Bearer $TOKEN1"
```

Should show `"user_accepted": true, "mutual_acceptance": false`

#### Accept Match (User 2)
```bash
# Login as user 2 first
curl -X POST http://localhost:5009/login \
  -H "Content-Type: application/json" \
  -d '{"email":"testfemale@example.com","password":"test123"}'

export TOKEN2="<token_from_response>"

# Accept match
curl -X POST http://localhost:5009/match/accept \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN2"
```

Expected response:
```json
{
  "success": true,
  "match_accepted": true,
  "mutual_acceptance": true,
  "message": "Match accepted! You can now chat with your match."
}
```

### 6. Test Private Chat

#### Send Message (User 1 to User 2)
```bash
curl -X POST http://localhost:5009/match/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1" \
  -d '{"message":"Hi! Nice to meet you!"}'
```

Expected response:
```json
{
  "success": true,
  "timestamp": "2025-11-07T..."
}
```

#### Get Messages (User 2)
```bash
curl -X GET http://localhost:5009/match/messages \
  -H "Authorization: Bearer $TOKEN2"
```

Expected response:
```json
{
  "messages": [
    {
      "from": "testmale_example_com",
      "message": "Hi! Nice to meet you!",
      "timestamp": "2025-11-07T..."
    }
  ],
  "match_id": "testmale_example_com",
  "mutual_acceptance": true
}
```

#### Send Reply (User 2 to User 1)
```bash
curl -X POST http://localhost:5009/match/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN2" \
  -d '{"message":"Hello! Excited to get to know you!"}'
```

### 7. Test Match Rejection

#### Decline Match (User 1)
```bash
curl -X POST http://localhost:5009/match/reject \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1"
```

Expected response:
```json
{
  "message": "Match declined. You will be matched with someone new in the next matching cycle.",
  "matching_active": true
}
```

This will clear the match for both users and add to rejected list.

### 8. Frontend Testing

1. **Open browser**: `http://localhost:5009` (or your server URL)
2. **Register new user** via signup form
3. **Go to Chat tab** - chat with AI to build profile
4. **Make sure to mention gender early** (e.g., "I'm a woman" or "I'm male")
5. **Fill 10-15 dimensions** for good matching
6. **Check Profile & Match tab** to see progress
7. **Run matching** (via cron or manually)
8. **Return to Profile & Match tab**:
   - Should see match card with compatibility score
   - See LLM analysis (reasoning, strengths, concerns)
   - See accept/decline buttons
9. **Click Accept Match**
10. **Login as second user** (opposite gender) and accept their match
11. **Return to first user**:
    - Should see "Match Accepted!" message
    - Chat interface now visible
    - Full profile JSON visible
12. **Test chat** - send messages back and forth

### 9. Test Edge Cases

#### Chat Before Mutual Acceptance (Should Fail)
```bash
# User 1 accepted, User 2 hasn't
curl -X POST http://localhost:5009/match/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1" \
  -d '{"message":"Test"}'
```

Expected: `403 Forbidden` with error message about needing mutual acceptance

#### Same Gender Matching (Should Not Match)
Create two male users or two female users, run matching - they should NOT be matched together.

#### No Gender Specified (Should Not Match)
Create user without specifying gender dimension, run matching - should not be matched.

#### Under 18 (Should Not Match)
```bash
curl -X POST http://localhost:5009/register \
  -H "Content-Type: application/json" \
  -d '{"email":"young@example.com","password":"test123","age":16}'
```

This user should not appear in matching pool (`matching_eligible: false`).

### 10. Admin Endpoints

#### Run Matching via API
```bash
curl -X POST http://localhost:5009/admin/run-matching
```

#### Get Matching Logs
```bash
curl -X GET http://localhost:5009/admin/matching-logs
```

Expected response:
```json
{
  "last_run": "2025-11-07T...",
  "total_runs": 5,
  "recent_runs": [
    {
      "timestamp": "2025-11-07T...",
      "total_profiles": 10,
      "active_users": 8,
      "matches_created": 3,
      "matches": [
        {
          "user1": "user1_id",
          "user2": "user2_id",
          "score": 82,
          "reasoning": "Excellent compatibility..."
        }
      ]
    }
  ]
}
```

### 11. Monitoring Tests

#### Check S3 Objects
```bash
# List profiles
aws s3 ls s3://mithrilmedia/lovedashmatcher/profiles/

# Check specific profile
aws s3 cp s3://mithrilmedia/lovedashmatcher/profiles/testmale_example_com.json - | python3 -m json.tool

# List match chats
aws s3 ls s3://mithrilmedia/lovedashmatcher/match_chats/
```

#### Check Logs
```bash
# Server logs
tail -f server.log

# Cron logs
tail -f /tmp/lovematcher_cron.log

# Matching logs
cat ~/.aws/lovedashmatcher/matching_logs.json | python3 -m json.tool
```

## Common Issues

### Issue: "Gender not found" during matching
**Solution**: Ensure users specify gender in chat. Check with:
```bash
curl -X GET http://localhost:5009/profile -H "Authorization: Bearer $TOKEN"
```
Look for `"gender": "male"` at profile level (not just in dimensions).

### Issue: LLM scoring returns fallback
**Check**: OpenRouter API key in config.py, model availability, internet connection
**Debug**: Look for "⚠️ OpenRouter error" in matching output

### Issue: Match not created
**Check**:
- Both users have `matching_active: true`
- Both users have `matching_eligible: true`
- Genders are opposite
- Neither user already has a match
- Neither user has rejected the other before

### Issue: Chat 403 error
**Check**:
- Both users must have `match_accepted: true`
- Verify with `GET /match` for both users
- Look for `"mutual_acceptance": true`

## Performance Benchmarks

Expected performance for typical operations:

- **User Registration**: < 500ms
- **Profile Chat Message**: 1-3s (depends on LLM)
- **Get Match**: < 200ms
- **Accept Match**: < 300ms
- **Send Chat Message**: < 200ms
- **Run Matching (10 users)**: 5-15s (depends on LLM scoring)
- **Run Matching (100 users)**: 30-90s

## Success Criteria

✅ **Matching System Working** if:
1. Opposite-gender users with profiles get matched
2. Match score between 30-100 returned from LLM
3. LLM analysis has reasoning, strengths, concerns
4. Same-gender users do NOT match
5. Users without gender do NOT match

✅ **Acceptance Flow Working** if:
1. Match starts with `match_accepted: false` for both
2. One user accepting shows "waiting" state
3. Both accepting enables chat (mutual_acceptance: true)
4. Profile preview before acceptance, full profile after

✅ **Chat Working** if:
1. Chat blocked until mutual acceptance (403 error)
2. Messages sent after acceptance appear for both users
3. Messages timestamped and ordered correctly
4. Chat persists across page reloads

✅ **Frontend Working** if:
1. Match card displays compatibility percentage
2. LLM analysis visible (reasoning, strengths, concerns)
3. Accept/decline buttons appear when pending
4. Chat interface appears after mutual acceptance
5. Full profile JSON visible after acceptance

## Next Steps After Testing

1. **Deploy to production server**
2. **Set up crontab** for daily matching
3. **Configure monitoring** (logs, metrics)
4. **Add real user data** (replace test accounts)
5. **Monitor match acceptance rates**
6. **Adjust matching threshold** if needed (currently 30%)
7. **Fine-tune LLM prompt** based on match quality feedback
8. **Scale infrastructure** as user base grows

## Support

For issues or questions:
1. Check logs: `tail -f server.log`
2. Review MATCHING_IMPLEMENTATION.md for system details
3. Test with `--dry-run` flag first
4. Verify S3 data integrity
5. Check OpenRouter API status

#!/usr/bin/env python3
"""
Daily matching script for Love-Matcher
Run via crontab to assign matches to active profiles
"""

import boto3
import json
from datetime import datetime
import random
import sys
import requests

try:
    import config
except ImportError:
    print("ERROR: config.py not found")
    sys.exit(1)

try:
    import prompts
except ImportError:
    print("ERROR: prompts.py not found")
    sys.exit(1)

# AWS S3 Setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    region_name=config.AWS_REGION
)

S3_BUCKET = config.S3_BUCKET
S3_PREFIX = config.S3_PREFIX

def s3_get(key):
    """Get object from S3"""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}{key}")
        return json.loads(response['Body'].read())
    except:
        return None

def s3_put(key, data):
    """Put object to S3"""
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_PREFIX}{key}",
        Body=json.dumps(data),
        ContentType='application/json'
    )

def s3_list_profiles():
    """List all profile keys in S3"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_PREFIX}profiles/"
        )
        if 'Contents' not in response:
            return []
        return [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.json')]
    except Exception as e:
        print(f"Error listing profiles: {e}")
        return []

def call_openrouter_completion(prompt, temperature=0.3, max_tokens=500):
    """
    Call OpenRouter completion endpoint for match scoring
    Uses lower temperature for more consistent scoring
    """
    try:
        headers = {
            'Authorization': f"Bearer {config.OPENROUTER_API_KEY}",
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://love-matcher.com',
            'X-Title': 'Love-Matcher-Matching'
        }
        
        payload = {
            'model': config.OPENROUTER_MODEL,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        response = requests.post(
            config.OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code >= 400:
            print(f"⚠️ OpenRouter error {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        
        return None
        
    except Exception as e:
        print(f"❌ Error calling OpenRouter: {e}")
        return None

def calculate_compatibility_score(profile1, profile2):
    """
    LLM-based compatibility scoring using OpenRouter /completion endpoint
    Returns a score between 0-100 and analysis details
    """
    # Build compatibility analysis prompt
    prompt = prompts.build_match_compatibility_prompt(profile1, profile2)
    
    # Call LLM
    llm_response = call_openrouter_completion(prompt, temperature=0.3, max_tokens=500)
    
    if not llm_response:
        print(f"  ⚠️ LLM scoring failed for {profile1.get('user_id')} x {profile2.get('user_id')}, using fallback")
        return calculate_compatibility_score_fallback(profile1, profile2)
    
    # Parse JSON response
    try:
        # Extract JSON from response (might have markdown code blocks)
        json_str = llm_response
        if '```json' in llm_response:
            json_str = llm_response.split('```json')[1].split('```')[0].strip()
        elif '```' in llm_response:
            json_str = llm_response.split('```')[1].split('```')[0].strip()
        
        analysis = json.loads(json_str)
        score = int(analysis.get('score', 0))
        
        # Validate score range
        if score < 0 or score > 100:
            print(f"  ⚠️ Invalid score {score}, using fallback")
            return calculate_compatibility_score_fallback(profile1, profile2)
        
        print(f"  💡 LLM Match Score: {score}% - {analysis.get('reasoning', 'N/A')[:60]}...")
        return score, analysis
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠️ Failed to parse LLM response: {e}, using fallback")
        return calculate_compatibility_score_fallback(profile1, profile2)

def calculate_compatibility_score_fallback(profile1, profile2):
    """
    Simple rule-based compatibility scoring as fallback
    Returns a score between 0-100
    """
    score = 0
    max_score = 0
    
    dims1 = profile1.get('dimensions', {})
    dims2 = profile2.get('dimensions', {})
    
    # Age compatibility (within 5 years = good)
    if 'age' in profile1 and 'age' in profile2:
        age_diff = abs(profile1['age'] - profile2['age'])
        if age_diff <= 5:
            score += 10
        elif age_diff <= 10:
            score += 5
        max_score += 10
    
    # Location compatibility
    if 'location' in dims1 and 'location' in dims2:
        if isinstance(dims1['location'], str) and isinstance(dims2['location'], str):
            if dims1['location'].lower() == dims2['location'].lower():
                score += 15
            elif any(word in dims1['location'].lower() for word in dims2['location'].lower().split()):
                score += 8
        max_score += 15
    
    # Religion compatibility (high weight for traditional marriage focus)
    if 'religion' in dims1 and 'religion' in dims2:
        if isinstance(dims1['religion'], str) and isinstance(dims2['religion'], str):
            if dims1['religion'].lower() == dims2['religion'].lower():
                score += 20
            elif 'none' in dims1['religion'].lower() and 'none' in dims2['religion'].lower():
                score += 15
        max_score += 20
    
    # Children desires
    if 'children' in dims1 and 'children' in dims2:
        children1 = str(dims1['children']).lower()
        children2 = str(dims2['children']).lower()
        if ('yes' in children1 and 'yes' in children2) or ('no' in children1 and 'no' in children2):
            score += 15
        elif 'maybe' in children1 or 'maybe' in children2:
            score += 8
        max_score += 15
    
    # Education compatibility
    if 'education' in dims1 and 'education' in dims2:
        score += 5
        max_score += 5
    
    # Career/Finances alignment
    if 'career' in dims1 and 'career' in dims2:
        score += 5
        max_score += 5
    
    # Lifestyle dimensions
    lifestyle_dims = ['social_energy', 'domestic', 'cleanliness', 'food', 'travel', 
                      'hobbies', 'culture', 'humor', 'pets', 'substances']
    
    for dim in lifestyle_dims:
        if dim in dims1 and dim in dims2:
            score += 2
            max_score += 2
    
    # Calculate percentage
    if max_score == 0:
        return 60, {'reasoning': 'Insufficient profile data for accurate matching', 'strengths': 'Unknown', 'concerns': 'Incomplete profiles'}
    
    final_score = int((score / max_score) * 100)
    return final_score, {'reasoning': 'Rule-based fallback scoring', 'strengths': 'Basic compatibility', 'concerns': 'Limited analysis'}

def normalize_gender(g):
    if not g:
        return None
    g = g.lower()
    if g in ('m', 'male'):
        return 'male'
    if g in ('f', 'female'):
        return 'female'
    return g


def find_top_matches_for_user(user_profile, all_profiles, n=3, verbose=False):
    """
    Find up to n compatible matches for a user, sorted by score descending.
    Returns list of (profile, score, analysis).
    """
    user_id = user_profile['user_id']
    user_gender_n = normalize_gender(user_profile.get('gender'))
    user_seeking_n = normalize_gender(user_profile.get('seeking_gender'))

    pool_ids = {e['user_id'] for e in user_profile.get('match_pool', [])}
    rejected_ids = set(user_profile.get('rejected_matches', []))

    if verbose:
        print(f"\n  🔎 Finding matches for: {user_id}")
        print(f"     Pool slots available: {n}  |  Rejected: {len(rejected_ids)}")

    if not user_gender_n or not user_seeking_n:
        if verbose:
            print(f"     ⚠️  Missing gender/seeking — skipping")
        return []

    scored = []

    for candidate in all_profiles:
        cid = candidate['user_id']
        if cid == user_id:
            continue
        if not candidate.get('matching_active', False):
            continue
        if cid in pool_ids:
            continue
        if cid in rejected_ids:
            continue
        if user_id in candidate.get('rejected_matches', []):
            continue

        cg = normalize_gender(candidate.get('gender'))
        cs = normalize_gender(candidate.get('seeking_gender'))
        if not cg or not cs:
            continue
        if user_seeking_n != cg or cs != user_gender_n:
            continue

        if verbose:
            print(f"     → Scoring {cid}")

        score_result = calculate_compatibility_score(user_profile, candidate)
        score, analysis = score_result if isinstance(score_result, tuple) else (score_result, {})

        if score >= 15:
            scored.append((candidate, score, analysis))
            if verbose:
                print(f"       Score: {score}%  ✓")
        elif verbose:
            print(f"       Score: {score}%  (below threshold)")

    scored.sort(key=lambda x: x[1], reverse=True)
    result = scored[:n]

    if verbose:
        if result:
            print(f"     ✅ Top {len(result)} matches: {[r[0]['user_id'] for r in result]}")
        else:
            print(f"     ❌ No suitable matches found")

    return result

def run_matching(dry_run=False, verbose=False):
    """Main matching algorithm - runs daily
    
    Args:
        dry_run: If True, only simulate matching without saving changes
        verbose: If True, output detailed matching progress
    """
    print("\n" + "=" * 60)
    print(f"🎯 Love-Matcher Daily Matching {'(DRY RUN)' if dry_run else ''}")
    print(f"Run time: {datetime.utcnow().isoformat()}")
    print("=" * 60 + "\n")
    
    # Get all profile keys
    print("📂 Loading profiles from S3...")
    profile_keys = s3_list_profiles()
    print(f"✓ Found {len(profile_keys)} total profile files in S3")
    
    # Load all profiles
    print("\n📊 Loading and validating profiles...")
    all_profiles = []
    invalid_profiles = []
    for key in profile_keys:
        # Extract just the filename part after the prefix
        filename = key.replace(f"{S3_PREFIX}profiles/", "")
        profile = s3_get(f"profiles/{filename}")
        if profile and isinstance(profile, dict):
            all_profiles.append(profile)
        else:
            invalid_profiles.append(filename)
            print(f"  ⚠️  Skipping invalid profile: {filename}")
    
    print(f"✓ Loaded {len(all_profiles)} valid profiles")
    if invalid_profiles:
        print(f"✗ Skipped {len(invalid_profiles)} invalid profiles")
    
    # Data checking - profile status breakdown
    print("\n📈 Profile Status Breakdown:")
    total_users = len(all_profiles)
    active_matching = sum(1 for p in all_profiles if p.get('matching_active', False))
    pools_full = sum(1 for p in all_profiles if len(p.get('match_pool', [])) >= 3)
    free_members = sum(1 for p in all_profiles if p.get('is_free_member', False))

    print(f"  Total profiles: {total_users}")
    print(f"  Active in matching pool: {active_matching}")
    print(f"  Pools already full (3 matches): {pools_full}")
    print(f"  Free members: {free_members}")
    print(f"  Paid members: {total_users - free_members}")

    # Users who are active and whose pool has fewer than 3 entries
    print("\n🔍 Filtering users needing matches...")
    users_needing_matches = [
        p for p in all_profiles
        if p.get('matching_active', False)
        and len(p.get('match_pool', [])) < 3
    ]
    users_needing_matches.sort(key=lambda p: len(p.get('dimensions', {})), reverse=True)

    print(f"  Users with room for more matches: {len(users_needing_matches)}")

    if len(users_needing_matches) < 2:
        print("\n⚠️  Not enough users needing matches")
        return {
            'success': True,
            'pool_additions': 0,
            'reason': 'Not enough users needing matches',
            'total_profiles': len(all_profiles),
        }

    # Track all pool additions made this run
    pool_additions = []
    profiles_to_save = set()

    # Build quick lookup map (we modify profiles in-place so candidates see updates)
    profile_map = {p['user_id']: p for p in all_profiles}

    print("\n💑 Starting match-pool filling...")
    if verbose:
        print(f"   Verbose mode enabled\n")

    for idx, user in enumerate(users_needing_matches, 1):
        user_id = user['user_id']
        slots = 3 - len(user.get('match_pool', []))
        if slots <= 0:
            continue

        if verbose:
            print(f"\n{'='*60}")
            print(f"User {idx}/{len(users_needing_matches)}: {user_id} (needs {slots} more)")
            print(f"{'='*60}")

        top = find_top_matches_for_user(user, all_profiles, n=slots, verbose=verbose)

        now = datetime.utcnow().isoformat()

        for candidate, score, analysis in top:
            cid = candidate['user_id']

            # Add to user's pool
            if 'match_pool' not in user:
                user['match_pool'] = []
            user['match_pool'].append({
                'user_id': cid,
                'score': score,
                'analysis': analysis or {},
                'matched_at': now,
            })
            profiles_to_save.add(user_id)

            # Add user to candidate's pool (if they still have room and not already there)
            cand = profile_map[cid]
            cand_pool = cand.get('match_pool', [])
            if len(cand_pool) < 3 and not any(e['user_id'] == user_id for e in cand_pool):
                if 'match_pool' not in cand:
                    cand['match_pool'] = []
                cand['match_pool'].append({
                    'user_id': user_id,
                    'score': score,
                    'analysis': analysis or {},
                    'matched_at': now,
                })
                profiles_to_save.add(cid)

            pool_additions.append({'user1': user_id, 'user2': cid, 'score': score})
            reasoning = (analysis or {}).get('reasoning', '')
            print(f"  ✅ Added {cid} → {user_id}'s pool (score: {score}%){' — ' + reasoning[:50] if reasoning else ''}")

    # Save all modified profiles
    if not dry_run:
        print(f"\n💾 Saving {len(profiles_to_save)} updated profiles...")
        for uid in profiles_to_save:
            s3_put(f"profiles/{uid}.json", profile_map[uid])
    else:
        print(f"\n🔸 DRY RUN — would save {len(profiles_to_save)} profiles")

    unfilled = sum(1 for p in users_needing_matches if len(p.get('match_pool', [])) < 3)
    if unfilled:
        print(f"\n  ⚠️  {unfilled} users still have fewer than 3 matches (pool exhausted)")
    
    print("\n" + "=" * 60)
    print(f"✓ Matching complete: {len(pool_additions)} pool additions")
    print("=" * 60 + "\n")

    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_profiles': len(all_profiles),
        'users_needing_matches': len(users_needing_matches),
        'pool_additions': len(pool_additions),
        'additions': pool_additions,
        'dry_run': dry_run,
    }

    if not dry_run:
        logs = s3_get('matching_logs.json') or {'runs': [], 'created_at': datetime.utcnow().isoformat()}
        logs['runs'].append(log_entry)
        logs['last_run'] = datetime.utcnow().isoformat()
        s3_put('matching_logs.json', logs)

    return {
        'success': True,
        'pool_additions': len(pool_additions),
        'total_profiles': len(all_profiles),
        'users_needing_matches': len(users_needing_matches),
        'additions': pool_additions,
        'dry_run': dry_run,
    }

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run daily matching for Love-Matcher')
    parser.add_argument('--dry-run', action='store_true', help='Simulate matching without saving changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed matching progress')
    args = parser.parse_args()
    
    try:
        result = run_matching(dry_run=args.dry_run, verbose=args.verbose)
        if result:
            print(f"\n✅ Result: {result}")
            sys.exit(0)
        else:
            print("\n⚠️ No result returned")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error running matching: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Daily matching script for LoveDashMatcher
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
            'HTTP-Referer': 'https://lovedashmatcher.com',
            'X-Title': 'LoveDashMatcher-Matching'
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

def find_match_for_user(user_profile, all_profiles, verbose=False):
    """
    Find best available match for a user
    Returns (matched_profile, score, analysis) or (None, 0, None)
    """
    user_id = user_profile['user_id']
    user_gender = user_profile.get('gender')
    user_age = user_profile.get('age', 'N/A')
    user_location = user_profile.get('dimensions', {}).get('location', 'N/A')
    
    if verbose:
        print(f"\n  🔎 Finding match for: {user_id}")
        print(f"     Gender: {user_gender} | Age: {user_age} | Location: {user_location}")
        print(f"     Dimensions filled: {len(user_profile.get('dimensions', {}))}/29")
    
    # Get user's current match and rejected users
    current_match = user_profile.get('current_match_id')
    rejected_users = set(user_profile.get('rejected_matches', []))
    
    if verbose and rejected_users:
        print(f"     Previously rejected: {len(rejected_users)} users")
    
    # If user already has a match, skip
    if current_match:
        if verbose:
            print(f"     ⚠️  Already has match: {current_match}")
        return None, 0, None
    
    best_match = None
    best_score = 0
    best_analysis = None
    
    candidates_considered = 0
    skip_reasons = {
        'self': 0,
        'inactive': 0,
        'not_eligible': 0,
        'already_matched': 0,
        'rejected_by_user': 0,
        'rejected_user': 0,
        'same_gender': 0,
        'invalid_gender': 0,
        'no_gender': 0,
        'low_score': 0
    }
    
    for candidate in all_profiles:
        candidate_id = candidate['user_id']
        candidate_gender = candidate.get('gender')
        
        # Skip self
        if candidate_id == user_id:
            skip_reasons['self'] += 1
            continue
        
        # Skip if not active
        if not candidate.get('matching_active', True):
            skip_reasons['inactive'] += 1
            continue
        
        # Skip if already matched
        if candidate.get('current_match_id'):
            skip_reasons['already_matched'] += 1
            continue
        
        # Skip if previously rejected
        if candidate_id in rejected_users:
            skip_reasons['rejected_by_user'] += 1
            continue
        
        # Skip if candidate rejected this user
        if user_id in candidate.get('rejected_matches', []):
            skip_reasons['rejected_user'] += 1
            continue
        
        # Traditional heterosexual matching - only match males with females
        if user_gender and candidate_gender:
            # Require opposite gender for matching
            if user_gender.lower() == candidate_gender.lower():
                skip_reasons['same_gender'] += 1
                continue
            # Ensure both are male/female (not other values)
            valid_genders = {'male', 'female', 'm', 'f'}
            if user_gender.lower() not in valid_genders or candidate_gender.lower() not in valid_genders:
                skip_reasons['invalid_gender'] += 1
                continue
        else:
            # If gender not specified, skip to ensure heterosexual matching
            skip_reasons['no_gender'] += 1
            continue
        
        candidates_considered += 1
        
        candidate_age = candidate.get('age', 'N/A')
        candidate_location = candidate.get('dimensions', {}).get('location', 'N/A')

        # Calculate compatibility using LLM
        if verbose:
            print(f"     → Evaluating {candidate_id}")
            print(f"       Gender: {candidate_gender} | Age: {candidate_age} | Location: {candidate_location}")
            print(f"       Dims: {len(candidate.get('dimensions', {}))}")
        
        score_result = calculate_compatibility_score(user_profile, candidate)
        if isinstance(score_result, tuple):
            score, analysis = score_result
        else:
            score = score_result
            analysis = None
        
        if score > best_score:
            best_score = score
            best_match = candidate
            best_analysis = analysis
            if verbose:
                print(f"       ✨ New best match! Score: {score}%")
        elif verbose:
            print(f"       Score: {score}% (not better than {best_score}%)")
    
    if verbose:
        print(f"\n     📊 Matching summary for {user_id}:")
        print(f"        Candidates considered: {candidates_considered}")
        if skip_reasons['self'] > 0:
            print(f"        Skipped - self: {skip_reasons['self']}")
        if skip_reasons['inactive'] > 0:
            print(f"        Skipped - inactive: {skip_reasons['inactive']}")
        if skip_reasons['not_eligible'] > 0:
            print(f"        Skipped - not eligible: {skip_reasons['not_eligible']}")
        if skip_reasons['already_matched'] > 0:
            print(f"        Skipped - already matched: {skip_reasons['already_matched']}")
        if skip_reasons['rejected_by_user'] > 0:
            print(f"        Skipped - rejected by user: {skip_reasons['rejected_by_user']}")
        if skip_reasons['rejected_user'] > 0:
            print(f"        Skipped - rejected user: {skip_reasons['rejected_user']}")
        if skip_reasons['same_gender'] > 0:
            print(f"        Skipped - same gender: {skip_reasons['same_gender']}")
        if skip_reasons['invalid_gender'] > 0:
            print(f"        Skipped - invalid gender: {skip_reasons['invalid_gender']}")
        if skip_reasons['no_gender'] > 0:
            print(f"        Skipped - no gender: {skip_reasons['no_gender']}")
        
        if best_match:
            print(f"        ✅ Best match: {best_match['user_id']} with score {best_score}%")
        else:
            print(f"        ❌ No suitable match found")
    
    return best_match, best_score, best_analysis

def run_matching(dry_run=False, verbose=False):
    """Main matching algorithm - runs daily
    
    Args:
        dry_run: If True, only simulate matching without saving changes
        verbose: If True, output detailed matching progress
    """
    print("\n" + "=" * 60)
    print(f"🎯 LoveDashMatcher Daily Matching {'(DRY RUN)' if dry_run else ''}")
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
    already_matched = sum(1 for p in all_profiles if p.get('current_match_id'))
    active_matching = sum(1 for p in all_profiles if p.get('matching_active', True))
    inactive_matching = total_users - active_matching
    eligible = sum(1 for p in all_profiles if p.get('matching_eligible', False))
    under_18 = sum(1 for p in all_profiles if p.get('age', 0) < 18)
    free_members = sum(1 for p in all_profiles if p.get('is_free_member', False))
    paid_members = total_users - free_members
    
    print(f"  Total profiles: {total_users}")
    print(f"  Already matched: {already_matched}")
    print(f"  Active in matching pool: {active_matching}")
    print(f"  Inactive/paused: {inactive_matching}")
    print(f"  Eligible (18+): {eligible}")
    print(f"  Under 18: {under_18}")
    print(f"  Free members: {free_members}")
    print(f"  Paid members: {paid_members}")
    
    # Filter for active users without matches (removed eligibility and payment requirements)
    # Note: matching_active defaults to True if not set
    # Now includes ALL profiles, even incomplete ones
    print("\n🔍 Filtering users for matching...")
    active_users = [
        p for p in all_profiles 
        if p.get('matching_active', True) 
        and not p.get('current_match_id')
    ]
    
    print(f"  Active users seeking matches: {len(active_users)}")
    
    # Use all active users - no eligibility, payment, or completion filtering
    # This allows incomplete profiles to be matched
    eligible_active_users = active_users
    
    print(f"  Users available for matching: {len(eligible_active_users)}")
    
    if len(eligible_active_users) < 2:
        print("\n⚠️  Not enough eligible active users for matching")
        print(f"   Need at least 2 users, have {len(eligible_active_users)}")
        return {
            'success': True,
            'matches_created': 0,
            'reason': 'Not enough eligible users',
            'eligible_users': len(eligible_active_users),
            'total_profiles': len(all_profiles),
            'already_matched': already_matched
        }
    
    # Track matches created
    matches_created = []
    
    # Sort by profile completeness (prioritize complete profiles)
    print("\n🔄 Sorting users by profile completeness...")
    eligible_active_users.sort(key=lambda p: len(p.get('dimensions', {})), reverse=True)
    
    # Show profile completion stats
    if eligible_active_users:
        completions = [len(p.get('dimensions', {})) for p in eligible_active_users]
        avg_completion = sum(completions) / len(completions)
        print(f"  Average profile completion: {avg_completion:.1f}/29 dimensions")
        print(f"  Most complete: {max(completions)}/29, Least complete: {min(completions)}/29")
    
    # Match users
    print("\n💑 Starting matching process...")
    if verbose:
        print(f"   Verbose mode enabled - showing detailed matching logic\n")
    matched_user_ids = set()
    
    for idx, user in enumerate(eligible_active_users, 1):
        user_id = user['user_id']
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Processing user {idx}/{len(eligible_active_users)}: {user_id}")
            print(f"{'='*60}")
        
        # Skip if already matched in this run
        if user_id in matched_user_ids:
            if verbose:
                print(f"   ⏭️  Skipping - already matched in this run")
            continue
        
        # Find best match
        match, score, analysis = find_match_for_user(user, all_profiles, verbose=verbose)
        
        if match and score >= 15:  # Minimum 15% compatibility (relaxed from 30%)
            match_id = match['user_id']
            
            # Skip if match already matched in this run
            if match_id in matched_user_ids:
                if verbose:
                    print(f"   ⏭️  Match candidate {match_id} already matched in this run")
                continue
            
            # Create mutual match with pending acceptance status
            user['current_match_id'] = match_id
            user['match_score'] = score
            user['matched_at'] = datetime.utcnow().isoformat()
            user['match_accepted'] = False  # Pending acceptance
            if analysis:
                user['match_analysis'] = analysis
            
            match['current_match_id'] = user_id
            match['match_score'] = score
            match['matched_at'] = datetime.utcnow().isoformat()
            match['match_accepted'] = False  # Pending acceptance
            if analysis:
                match['match_analysis'] = analysis
            
            # Save updated profiles (unless dry run)
            if not dry_run:
                if verbose:
                    print(f"\n   💾 Saving match to S3...")
                s3_put(f"profiles/{user_id}.json", user)
                s3_put(f"profiles/{match_id}.json", match)
                
                # Initialize match chat (use sorted IDs for consistent key)
                chat_ids = sorted([user_id, match_id])
                match_chat = {
                    'user1_id': chat_ids[0],
                    'user2_id': chat_ids[1],
                    'created_at': datetime.utcnow().isoformat(),
                    'messages': [],
                    'match_score': score,
                    'match_analysis': analysis if analysis else {}
                }
                s3_put(f"match_chats/{chat_ids[0]}_{chat_ids[1]}.json", match_chat)
                if verbose:
                    print(f"   ✅ Saved profiles and initialized chat")
            elif verbose:
                print(f"\n   🔸 DRY RUN - Not saving to S3")
            
            matched_user_ids.add(user_id)
            matched_user_ids.add(match_id)
            
            match_entry = {
                'user1': user_id,
                'user2': match_id,
                'score': score
            }
            if analysis:
                match_entry['reasoning'] = analysis.get('reasoning', '')
            
            matches_created.append(match_entry)
            
            reasoning_preview = analysis.get('reasoning', 'N/A')[:50] + "..." if analysis else "N/A"
            print(f"  ✅ Matched {user_id} with {match_id} (score: {score}%) - {reasoning_preview}")
        elif verbose:
            if match:
                print(f"\n   ❌ Match score too low: {score}% (minimum: 15%)")
            else:
                print(f"\n   ❌ No suitable match found for {user_id}")
    
    # Report unmatched users
    unmatched_count = len(eligible_active_users) - (len(matches_created) * 2)
    if unmatched_count > 0:
        print(f"\n  ⚠️  {unmatched_count} eligible users remain unmatched this round")
    
    print("\n" + "=" * 60)
    print(f"✓ Matching complete: {len(matches_created)} new matches created")
    print("=" * 60 + "\n")
    
    # Save matching run log (unless dry run)
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_profiles': len(all_profiles),
        'active_users': len(eligible_active_users),
        'matches_created': len(matches_created),
        'matches': matches_created,
        'dry_run': dry_run
    }
    
    if not dry_run:
        # Append to log file
        logs = s3_get('matching_logs.json') or {'runs': [], 'created_at': datetime.utcnow().isoformat()}
        logs['runs'].append(log_entry)
        logs['last_run'] = datetime.utcnow().isoformat()
        s3_put('matching_logs.json', logs)
    
    return {
        'success': True,
        'matches_created': len(matches_created),
        'total_profiles': len(all_profiles),
        'eligible_users': len(eligible_active_users),
        'matches': matches_created,
        'dry_run': dry_run
    }

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run daily matching for LoveDashMatcher')
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

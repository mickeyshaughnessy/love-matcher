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

try:
    import config
except ImportError:
    print("ERROR: config.py not found")
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

def calculate_compatibility_score(profile1, profile2):
    """
    Simple rule-based compatibility scoring
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
        return 0
    
    return int((score / max_score) * 100)

def find_match_for_user(user_profile, all_profiles):
    """
    Find best available match for a user
    Returns (matched_profile, score) or (None, 0)
    """
    user_id = user_profile['user_id']
    user_gender = user_profile.get('gender')
    
    # Get user's current match and rejected users
    current_match = user_profile.get('current_match_id')
    rejected_users = set(user_profile.get('rejected_matches', []))
    
    # If user already has a match, skip
    if current_match:
        return None, 0
    
    best_match = None
    best_score = 0
    
    for candidate in all_profiles:
        candidate_id = candidate['user_id']
        candidate_gender = candidate.get('gender')
        
        # Skip self
        if candidate_id == user_id:
            continue
        
        # Skip if not active
        if not candidate.get('matching_active', True):
            continue
        
        # Skip if not eligible
        if not candidate.get('matching_eligible', False):
            continue
        
        # Skip if already matched
        if candidate.get('current_match_id'):
            continue
        
        # Skip if previously rejected
        if candidate_id in rejected_users:
            continue
        
        # Skip if candidate rejected this user
        if user_id in candidate.get('rejected_matches', []):
            continue
        
        # Traditional heterosexual matching (if gender specified)
        if user_gender and candidate_gender:
            if user_gender == candidate_gender:
                continue
        
        # Calculate compatibility
        score = calculate_compatibility_score(user_profile, candidate)
        
        if score > best_score:
            best_score = score
            best_match = candidate
    
    return best_match, best_score

def run_matching(dry_run=False):
    """Main matching algorithm - runs daily
    
    Args:
        dry_run: If True, only simulate matching without saving changes
    """
    print("=" * 60)
    print(f"🎯 LoveDashMatcher Daily Matching {'(DRY RUN)' if dry_run else ''}")
    print(f"Run time: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    # Get all profile keys
    profile_keys = s3_list_profiles()
    print(f"Found {len(profile_keys)} total profiles")
    
    # Load all profiles
    all_profiles = []
    for key in profile_keys:
        # Extract just the filename part after the prefix
        filename = key.replace(f"{S3_PREFIX}profiles/", "")
        profile = s3_get(f"profiles/{filename}")
        if profile and isinstance(profile, dict):
            all_profiles.append(profile)
        else:
            print(f"⚠️ Skipping invalid profile: {filename}")
    
    print(f"Loaded {len(all_profiles)} profiles successfully")
    
    # Filter for active, eligible users without matches
    # Note: matching_active defaults to True if not set
    # Note: matching_eligible must be True (age >= 18 and payment status OK)
    active_users = [
        p for p in all_profiles 
        if p.get('matching_active', True) 
        and p.get('matching_eligible', False)
        and not p.get('current_match_id')
        and p.get('payment_status') in ['free', 'completed', 'free_pending_age']
    ]
    
    print(f"Active users seeking matches: {len(active_users)}")
    
    # Filter only those who are actually eligible (18+)
    eligible_active_users = [
        u for u in active_users
        if u.get('matching_eligible', False) and u.get('payment_status') in ['free', 'completed']
    ]
    
    print(f"Eligible active users (18+, paid/free): {len(eligible_active_users)}")
    
    if len(eligible_active_users) < 2:
        print("Not enough eligible active users for matching")
        return {
            'success': True,
            'matches_created': 0,
            'reason': 'Not enough eligible users',
            'eligible_users': len(eligible_active_users)
        }
    
    # Track matches created
    matches_created = []
    
    # Sort by profile completeness (prioritize complete profiles)
    eligible_active_users.sort(key=lambda p: len(p.get('dimensions', {})), reverse=True)
    
    # Match users
    matched_user_ids = set()
    
    for user in eligible_active_users:
        user_id = user['user_id']
        
        # Skip if already matched in this run
        if user_id in matched_user_ids:
            continue
        
        # Find best match
        match, score = find_match_for_user(user, all_profiles)
        
        if match and score >= 30:  # Minimum 30% compatibility
            match_id = match['user_id']
            
            # Skip if match already matched in this run
            if match_id in matched_user_ids:
                continue
            
            # Create mutual match
            user['current_match_id'] = match_id
            user['match_score'] = score
            user['matched_at'] = datetime.utcnow().isoformat()
            
            match['current_match_id'] = user_id
            match['match_score'] = score
            match['matched_at'] = datetime.utcnow().isoformat()
            
            # Save updated profiles (unless dry run)
            if not dry_run:
                s3_put(f"profiles/{user_id}.json", user)
                s3_put(f"profiles/{match_id}.json", match)
                
                # Initialize match chat (use sorted IDs for consistent key)
                chat_ids = sorted([user_id, match_id])
                match_chat = {
                    'user1_id': chat_ids[0],
                    'user2_id': chat_ids[1],
                    'created_at': datetime.utcnow().isoformat(),
                    'messages': []
                }
                s3_put(f"match_chats/{chat_ids[0]}_{chat_ids[1]}.json", match_chat)
            
            matched_user_ids.add(user_id)
            matched_user_ids.add(match_id)
            
            matches_created.append({
                'user1': user_id,
                'user2': match_id,
                'score': score
            })
            
            print(f"✅ Matched {user_id} with {match_id} (score: {score}%)")
    
    print("=" * 60)
    print(f"Matching complete: {len(matches_created)} new matches created")
    print("=" * 60)
    
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
    args = parser.parse_args()
    
    try:
        result = run_matching(dry_run=args.dry_run)
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

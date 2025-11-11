#!/usr/bin/env python3
"""
Profile Management Script for Love Matcher
Inspect and manage member profiles stored in S3
"""

import boto3
import json
from datetime import datetime
import config

# Initialize S3 client
s3 = boto3.client(
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
        response = s3.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}{key}")
        return json.loads(response['Body'].read())
    except Exception as e:
        print(f"Error reading {key}: {e}")
        return None

def s3_put(key, data):
    """Put object to S3"""
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"{S3_PREFIX}{key}",
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        print(f"✓ Saved {key}")
    except Exception as e:
        print(f"Error saving {key}: {e}")

def s3_list_profiles():
    """List all profile files in S3"""
    try:
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_PREFIX}profiles/"
        )
        if 'Contents' in response:
            return [obj['Key'].replace(S3_PREFIX, '') for obj in response['Contents']]
        return []
    except Exception as e:
        print(f"Error listing profiles: {e}")
        return []

def list_members():
    """List all members from member_list.json"""
    print("\n=== MEMBER LIST ===")
    member_list = s3_get('member_list.json')
    if not member_list:
        print("No member list found")
        return
    
    members = member_list.get('members', [])
    print(f"\nTotal members: {len(members)}")
    print(f"Created: {member_list.get('created_at', 'Unknown')}")
    print(f"Updated: {member_list.get('updated_at', 'Unknown')}\n")
    
    for member in members:
        free_status = "FREE" if member.get('is_free', False) else "PAID"
        print(f"#{member.get('member_number'):4d} | {free_status:4s} | {member.get('email'):30s} | Age: {member.get('age', 'N/A'):2} | ID: {member.get('user_id')}")

def list_profiles():
    """List all profile files"""
    print("\n=== PROFILE FILES ===")
    profiles = s3_list_profiles()
    print(f"\nTotal profiles: {len(profiles)}\n")
    for profile_key in sorted(profiles):
        user_id = profile_key.replace('profiles/', '').replace('.json', '')
        print(f"  - {user_id}")

def show_profile(user_id):
    """Show detailed profile information"""
    print(f"\n=== PROFILE: {user_id} ===")
    profile = s3_get(f"profiles/{user_id}.json")
    if not profile:
        print(f"Profile not found: {user_id}")
        return
    
    print(json.dumps(profile, indent=2))

def search_profiles(query):
    """Search profiles by email or user_id"""
    print(f"\n=== SEARCHING FOR: {query} ===")
    member_list = s3_get('member_list.json')
    if not member_list:
        print("No member list found")
        return
    
    matches = [m for m in member_list.get('members', []) 
               if query.lower() in m.get('email', '').lower() or query in m.get('user_id', '')]
    
    if not matches:
        print("No matches found")
        return
    
    for member in matches:
        print(f"\n#{member.get('member_number')} - {member.get('email')}")
        print(f"  User ID: {member.get('user_id')}")
        print(f"  Age: {member.get('age')}")
        print(f"  Registration: {member.get('registration_time')}")
        print(f"  Free Member: {member.get('is_free', False)}")

def update_profile_field(user_id, field_path, value):
    """Update a specific field in a profile (use dot notation for nested fields)"""
    profile = s3_get(f"profiles/{user_id}.json")
    if not profile:
        print(f"Profile not found: {user_id}")
        return
    
    # Handle nested fields with dot notation
    fields = field_path.split('.')
    current = profile
    for field in fields[:-1]:
        if field not in current:
            current[field] = {}
        current = current[field]
    
    current[fields[-1]] = value
    
    s3_put(f"profiles/{user_id}.json", profile)
    print(f"✓ Updated {field_path} = {value}")

def delete_profile(user_id, confirm=False):
    """Delete a profile (requires confirmation)"""
    if not confirm:
        print(f"⚠️  To delete profile {user_id}, call with confirm=True")
        return
    
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}profiles/{user_id}.json")
        print(f"✓ Deleted profile: {user_id}")
    except Exception as e:
        print(f"Error deleting profile: {e}")

def scan_profiles():
    """Scan all profiles and collect detailed statistics"""
    print("\n=== SCANNING PROFILES ===")
    print("Loading profiles from S3...\n")
    
    profile_keys = s3_list_profiles()
    
    stats = {
        'total_profiles': 0,
        'matching_eligible': 0,
        'not_eligible': 0,
        'profile_complete': 0,
        'profile_incomplete': 0,
        'currently_matched': 0,
        'unmatched': 0,
        'conversation_count_total': 0,
        'age_distribution': {},
        'gender_distribution': {},
        'dimension_counts': {},
    }
    
    profiles_data = []
    
    for profile_key in profile_keys:
        user_id = profile_key.replace(f"{S3_PREFIX}profiles/", "").replace(".json", "")
        profile = s3_get(f"profiles/{user_id}.json")
        
        if not profile:
            continue
        
        stats['total_profiles'] += 1
        profiles_data.append(profile)
        
        # Matching eligibility
        if profile.get('matching_eligible', False):
            stats['matching_eligible'] += 1
        else:
            stats['not_eligible'] += 1
        
        # Profile completion
        if profile.get('profile_complete', False):
            stats['profile_complete'] += 1
        else:
            stats['profile_incomplete'] += 1
        
        # Current match status
        if profile.get('current_match_id'):
            stats['currently_matched'] += 1
        else:
            stats['unmatched'] += 1
        
        # Conversation count
        stats['conversation_count_total'] += profile.get('conversation_count', 0)
        
        # Age distribution
        age = profile.get('age')
        if age and isinstance(age, int) and age < 150:  # Filter out bad data
            age_group = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}"
            stats['age_distribution'][age_group] = stats['age_distribution'].get(age_group, 0) + 1
        
        # Gender distribution
        dimensions = profile.get('dimensions', {})
        gender = dimensions.get('gender', 'Unknown')
        if gender:
            stats['gender_distribution'][gender] = stats['gender_distribution'].get(gender, 0) + 1
        
        # Dimension completion
        for dim_key in dimensions.keys():
            stats['dimension_counts'][dim_key] = stats['dimension_counts'].get(dim_key, 0) + 1
    
    # Print statistics
    print(f"{'='*60}")
    print(f"PROFILE STATISTICS")
    print(f"{'='*60}\n")
    
    print(f"Total Profiles: {stats['total_profiles']}\n")
    
    print("MATCHING STATUS:")
    print(f"  ✓ Eligible for matching:     {stats['matching_eligible']:4d} ({stats['matching_eligible']/max(stats['total_profiles'],1)*100:5.1f}%)")
    print(f"  ✗ Not eligible:              {stats['not_eligible']:4d} ({stats['not_eligible']/max(stats['total_profiles'],1)*100:5.1f}%)")
    print(f"  ❤ Currently matched:         {stats['currently_matched']:4d} ({stats['currently_matched']/max(stats['total_profiles'],1)*100:5.1f}%)")
    print(f"  ○ Unmatched:                 {stats['unmatched']:4d} ({stats['unmatched']/max(stats['total_profiles'],1)*100:5.1f}%)\n")
    
    print("PROFILE COMPLETION:")
    print(f"  ✓ Complete profiles:         {stats['profile_complete']:4d} ({stats['profile_complete']/max(stats['total_profiles'],1)*100:5.1f}%)")
    print(f"  ○ Incomplete profiles:       {stats['profile_incomplete']:4d} ({stats['profile_incomplete']/max(stats['total_profiles'],1)*100:5.1f}%)\n")
    
    print(f"CONVERSATIONS:")
    print(f"  Total conversation count:    {stats['conversation_count_total']}")
    if stats['total_profiles'] > 0:
        print(f"  Average per profile:         {stats['conversation_count_total']/stats['total_profiles']:.1f}\n")
    
    if stats['age_distribution']:
        print("AGE DISTRIBUTION:")
        for age_group in sorted(stats['age_distribution'].keys()):
            count = stats['age_distribution'][age_group]
            print(f"  {age_group}: {count:3d} ({count/max(stats['total_profiles'],1)*100:5.1f}%)")
        print()
    
    if stats['gender_distribution']:
        print("GENDER DISTRIBUTION:")
        for gender, count in sorted(stats['gender_distribution'].items()):
            print(f"  {gender}: {count:3d} ({count/max(stats['total_profiles'],1)*100:5.1f}%)")
        print()
    
    if stats['dimension_counts']:
        print("PROFILE DIMENSIONS FILLED:")
        for dim, count in sorted(stats['dimension_counts'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {dim}: {count:3d} ({count/max(stats['total_profiles'],1)*100:5.1f}%)")
    
    return stats, profiles_data

def get_stats():
    """Show overall statistics"""
    print("\n=== STATISTICS ===")
    
    member_list = s3_get('member_list.json')
    profiles = s3_list_profiles()
    
    if member_list:
        members = member_list.get('members', [])
        free_count = sum(1 for m in members if m.get('is_free', False))
        paid_count = len(members) - free_count
        
        print(f"\nTotal registered members: {len(members)}")
        print(f"  - Free members: {free_count}")
        print(f"  - Paid members: {paid_count}")
    
    print(f"\nTotal profile files: {len(profiles)}")

# Interactive menu
def menu():
    """Interactive menu for profile management"""
    print("\n" + "="*60)
    print("LOVE MATCHER - PROFILE MANAGEMENT")
    print("="*60)
    print("\nCommands:")
    print("  1. List all members")
    print("  2. List all profile files")
    print("  3. Show basic statistics")
    print("  4. Scan profiles (detailed stats)")
    print("  5. Show profile (by user_id)")
    print("  6. Search profiles (by email or user_id)")
    print("  q. Quit")
    print()
    
    while True:
        choice = input("Enter command: ").strip()
        
        if choice == '1':
            list_members()
        elif choice == '2':
            list_profiles()
        elif choice == '3':
            get_stats()
        elif choice == '4':
            scan_profiles()
        elif choice == '5':
            user_id = input("Enter user_id: ").strip()
            show_profile(user_id)
        elif choice == '6':
            query = input("Enter search query: ").strip()
            search_profiles(query)
        elif choice.lower() == 'q':
            print("Goodbye!")
            break
        else:
            print("Invalid command")

if __name__ == '__main__':
    import sys
    
    # If arguments provided, run as CLI tool
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'list':
            list_members()
        elif cmd == 'profiles':
            list_profiles()
        elif cmd == 'stats':
            get_stats()
        elif cmd == 'scan':
            scan_profiles()
        elif cmd == 'show' and len(sys.argv) > 2:
            show_profile(sys.argv[2])
        elif cmd == 'search' and len(sys.argv) > 2:
            search_profiles(sys.argv[2])
        else:
            print("Usage:")
            print("  python manage_profiles.py list              # List all members")
            print("  python manage_profiles.py profiles          # List profile files")
            print("  python manage_profiles.py stats             # Show basic statistics")
            print("  python manage_profiles.py scan              # Scan profiles (detailed)")
            print("  python manage_profiles.py show <user_id>    # Show profile")
            print("  python manage_profiles.py search <query>    # Search profiles")
            print("  python manage_profiles.py                   # Interactive menu")
    else:
        # Run interactive menu
        menu()

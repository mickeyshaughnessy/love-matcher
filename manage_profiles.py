#!/usr/bin/env python3
"""
Profile Management Script for Love Matcher
Inspect and manage member profiles stored in S3
"""

import boto3
import json
from datetime import datetime
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET, S3_PREFIX

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

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
    print("  3. Show statistics")
    print("  4. Show profile (by user_id)")
    print("  5. Search profiles (by email or user_id)")
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
            user_id = input("Enter user_id: ").strip()
            show_profile(user_id)
        elif choice == '5':
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
        elif cmd == 'show' and len(sys.argv) > 2:
            show_profile(sys.argv[2])
        elif cmd == 'search' and len(sys.argv) > 2:
            search_profiles(sys.argv[2])
        else:
            print("Usage:")
            print("  python manage_profiles.py list              # List all members")
            print("  python manage_profiles.py profiles          # List profile files")
            print("  python manage_profiles.py stats             # Show statistics")
            print("  python manage_profiles.py show <user_id>    # Show profile")
            print("  python manage_profiles.py search <query>    # Search profiles")
            print("  python manage_profiles.py                   # Interactive menu")
    else:
        # Run interactive menu
        menu()

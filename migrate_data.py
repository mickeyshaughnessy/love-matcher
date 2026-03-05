import boto3
import os
import sys
import mimetypes
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---

# Source (AWS S3) - User must provide these in .env
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
SOURCE_BUCKET = 'mithrilmedia'
SOURCE_PREFIX = 'lovedashmatcher/'  # Source folder in S3

# Destination (Digital Ocean Spaces)
DO_SPACES_KEY = os.getenv('DO_SPACES_KEY')
DO_SPACES_SECRET = os.getenv('DO_SPACES_SECRET')
# Default to SF03 if not set, or parse from URL
DO_SPACES_URL = os.getenv('DO_SPACES_URL', 'https://mithril-media.sfo3.digitaloceanspaces.com')
# Destination Prefix: App uses 'Love-Matcher/' (config.S3_PREFIX)
DEST_PREFIX = os.getenv('S3_PREFIX', 'Love-Matcher/')

def get_do_bucket_and_region(url):
    """Extract bucket, region, and endpoint from DO Spaces URL"""
    url = url.replace('https://', '').replace('http://', '')
    parts = url.split('.')
    if len(parts) < 3:
         # Fallback or assume path style? 
         # Assuming mithril-media.sfo3.digitaloceanspaces.com style
         print(f"Warning: Could not parse DO URL '{url}'. assuming defaults.")
         return 'mithril-media', 'sfo3', 'https://sfo3.digitaloceanspaces.com'
         
    bucket = parts[0]
    region = parts[1]
    endpoint = f"https://{region}.digitaloceanspaces.com"
    return bucket, region, endpoint

def migrate():
    print("="*60)
    print("🚀 Starting S3 -> DO Spaces Migration")
    print("="*60)
    
    # 1. Validation
    missing_vars = []
    if not AWS_ACCESS_KEY_ID: missing_vars.append('AWS_ACCESS_KEY_ID')
    if not AWS_SECRET_ACCESS_KEY: missing_vars.append('AWS_SECRET_ACCESS_KEY')
    if not DO_SPACES_KEY: missing_vars.append('DO_SPACES_KEY')
    if not DO_SPACES_SECRET: missing_vars.append('DO_SPACES_SECRET')
    
    if missing_vars:
        print("❌ Error: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease update your .env file with these credentials.")
        return

    # 2. Setup Clients
    try:
        source_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        # Verify source access
        print(f"Testing access to source bucket: {SOURCE_BUCKET}...")
        source_client.head_bucket(Bucket=SOURCE_BUCKET)
        print("✅ Source access verified.")
    except Exception as e:
        print(f"❌ Failed to connect to source bucket: {e}")
        return

    try:
        dest_bucket, dest_region, dest_endpoint = get_do_bucket_and_region(DO_SPACES_URL)
        dest_client = boto3.client(
            's3',
            aws_access_key_id=DO_SPACES_KEY,
            aws_secret_access_key=DO_SPACES_SECRET,
            endpoint_url=dest_endpoint,
            region_name=dest_region
        )
        print(f"Testing access to destination bucket: {dest_bucket} ({dest_region})...")
        dest_client.head_bucket(Bucket=dest_bucket)
        print("✅ Destination access verified.")
    except Exception as e:
        print(f"❌ Failed to connect to destination bucket: {e}")
        return

    # 3. List Objects
    print(f"\nScanning source: s3://{SOURCE_BUCKET}/{SOURCE_PREFIX}")
    try:
        paginator = source_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=SOURCE_BUCKET, Prefix=SOURCE_PREFIX)
        
        objects_to_copy = []
        total_size = 0
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Skip the folder object itself if it exists
                    if key == SOURCE_PREFIX:
                        continue
                    objects_to_copy.append(obj)
                    total_size += obj['Size']
        
        print(f"Found {len(objects_to_copy)} objects ({total_size / 1024 / 1024:.2f} MB)")
        
        if not objects_to_copy:
            print("Nothing to migrate.")
            return

    except Exception as e:
        print(f"❌ Error listing source objects: {e}")
        return

    # 4. Perform Migration
    print("\nStarting Copy...")
    success_count = 0
    fail_count = 0
    
    for i, obj in enumerate(objects_to_copy, 1):
        source_key = obj['Key']
        
        # Calculate destination key
        # Remove SOURCE_PREFIX from the start
        relative_path = source_key[len(SOURCE_PREFIX):] if source_key.startswith(SOURCE_PREFIX) else source_key
        # Prepend DEST_PREFIX
        dest_key = f"{DEST_PREFIX}{relative_path}"
        
        print(f"[{i}/{len(objects_to_copy)}] {source_key} -> {dest_key} ...", end=" ")
        sys.stdout.flush()
        
        try:
            # Download stream
            response = source_client.get_object(Bucket=SOURCE_BUCKET, Key=source_key)
            content = response['Body'].read()
            content_type = response['ContentType']
            metadata = response.get('Metadata', {})
            
            # Upload stream
            # We explicitly set ContentType and keep it private (default)
            dest_client.put_object(
                Bucket=dest_bucket,
                Key=dest_key,
                Body=content,
                ContentType=content_type,
                Metadata=metadata,
                ACL='private'
            )
            print("✅ OK")
            success_count += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            fail_count += 1

    print("\n" + "="*60)
    print(f"Migration Complete!")
    print(f"Successful: {success_count}")
    print(f"Failed:     {fail_count}")
    print("="*60)

if __name__ == "__main__":
    migrate()

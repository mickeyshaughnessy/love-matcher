#!/usr/bin/env python3
"""One-time script: set all user passwords to a given value."""
import json
import boto3
import bcrypt
import sys

import config

NEW_PASSWORD = sys.argv[1] if len(sys.argv) > 1 else '11111111'

DO_BUCKET = 'mithril-media'
DO_REGION = 'sfo3'
DO_ENDPOINT = f"https://{DO_REGION}.digitaloceanspaces.com"
S3_PREFIX = config.S3_PREFIX

s3 = boto3.client(
    's3',
    aws_access_key_id=config.DO_SPACES_KEY,
    aws_secret_access_key=config.DO_SPACES_SECRET,
    endpoint_url=DO_ENDPOINT,
    region_name=DO_REGION
)

def s3_get(key):
    try:
        r = s3.get_object(Bucket=DO_BUCKET, Key=f"{S3_PREFIX}{key}")
        return json.loads(r['Body'].read())
    except:
        return None

def s3_put(key, data):
    s3.put_object(Bucket=DO_BUCKET, Key=f"{S3_PREFIX}{key}",
                  Body=json.dumps(data), ContentType='application/json')

member_list = s3_get('member_list.json') or {'members': []}
members = member_list.get('members', [])
print(f"Found {len(members)} members. Setting password to '{NEW_PASSWORD}'...")

pw_hash = bcrypt.hashpw(NEW_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

for m in members:
    uid = m.get('user_id')
    profile = s3_get(f"profiles/{uid}.json")
    if not profile:
        print(f"  SKIP {uid} — no profile")
        continue
    profile['password_hash'] = pw_hash
    profile.pop('password_reset_token', None)
    s3_put(f"profiles/{uid}.json", profile)
    print(f"  OK   {uid} ({profile.get('email', '')})")

print("Done.")

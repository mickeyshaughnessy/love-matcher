from flask import Flask
from flask_cors import CORS
import boto3
import os

try:
    import config
except ImportError:
    print("ERROR: config.py not found. Please create it from config.example.py")
    exit(1)

app = Flask(__name__)
CORS(app)

# Config from config.py
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['JWT_SECRET'] = config.JWT_SECRET_KEY

# AWS S3 Setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    region_name=config.AWS_REGION
)

# S3 Configuration
S3_BUCKET = config.S3_BUCKET
S3_PREFIX = config.S3_PREFIX

# OpenRouter Configuration
OPENROUTER_CONFIG = {
    'api_url': config.OPENROUTER_API_URL,
    'api_key': config.OPENROUTER_API_KEY,
    'model': config.OPENROUTER_MODEL,
    'temperature': config.LLM_TEMPERATURE,
    'max_tokens': config.LLM_MAX_TOKENS
}

# Import handlers after app is configured
from handlers import register_routes

# Register all routes with OpenRouter config
register_routes(app, s3_client, S3_BUCKET, S3_PREFIX, OPENROUTER_CONFIG)

if __name__ == '__main__':
    print("=" * 60)
    print("🔷 LoveDashMatcher API Server Starting")
    print("=" * 60)
    print(f"S3 Bucket: {S3_BUCKET}")
    print(f"S3 Prefix: {S3_PREFIX}")
    print(f"LLM Model: {config.OPENROUTER_MODEL}")
    print(f"Server: http://0.0.0.0:5009")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5009)
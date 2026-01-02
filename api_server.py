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

# Parse Digital Ocean Spaces URL to extract bucket and region
def _parse_do_url(url):
    """Extract bucket name and region from Digital Ocean Spaces URL."""
    url = url.replace('https://', '').replace('http://', '')
    parts = url.split('.')
    if len(parts) >= 3 and 'digitaloceanspaces' in url:
        bucket = parts[0]
        region = parts[1]
        return bucket, region
    raise ValueError(f"Invalid Digital Ocean Spaces URL: {url}")

DO_BUCKET, DO_REGION = _parse_do_url(config.DO_SPACES_URL)
DO_ENDPOINT = f"https://{DO_REGION}.digitaloceanspaces.com"

# Digital Ocean Spaces Setup (S3-compatible)
s3_client = boto3.client(
    's3',
    aws_access_key_id=config.DO_SPACES_KEY,
    aws_secret_access_key=config.DO_SPACES_SECRET,
    endpoint_url=DO_ENDPOINT,
    region_name=DO_REGION
)

# S3 Configuration
S3_BUCKET = DO_BUCKET
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
    print("🔷 Love-Matcher API Server Starting")
    print("=" * 60)
    print(f"Storage: Digital Ocean Spaces")
    print(f"Bucket: {S3_BUCKET}")
    print(f"Region: {DO_REGION}")
    print(f"Prefix: {S3_PREFIX}")
    print(f"LLM Model: {config.OPENROUTER_MODEL}")
    print(f"Server: http://0.0.0.0:5009")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5009)
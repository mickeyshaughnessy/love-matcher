from flask import Flask
from flask_cors import CORS
import boto3
import os
import sys

try:
    import config
except ImportError:
    print("WARNING: config.py not found. Using environment variables only.")
    config = None

app = Flask(__name__)
CORS(app)

# Config from config.py or environment
app.config['SECRET_KEY'] = getattr(config, 'SECRET_KEY', None) or os.getenv('SECRET_KEY', 'default-secret-key-change-me')
app.config['JWT_SECRET'] = getattr(config, 'JWT_SECRET_KEY', None) or os.getenv('JWT_SECRET_KEY', 'default-jwt-secret-change-me')

# AWS S3 Setup - prioritize environment variables on Linux
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID') or (getattr(config, 'AWS_ACCESS_KEY_ID', None) if config else None)
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or (getattr(config, 'AWS_SECRET_ACCESS_KEY', None) if config else None)
aws_region = os.getenv('AWS_REGION') or (getattr(config, 'AWS_REGION', None) if config else None) or 'us-east-1'

if not aws_access_key or not aws_secret_key:
    print("ERROR: AWS credentials not found!")
    print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in environment or config.py")
    sys.exit(1)

s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region
)

S3_BUCKET = os.getenv('S3_BUCKET', 'mithrilmedia')
S3_PREFIX = os.getenv('S3_PREFIX', 'lovedashmatcher/')

# Import handlers after app is configured
try:
    from handlers import register_routes
    register_routes(app, s3_client, S3_BUCKET, S3_PREFIX)
except ImportError:
    print("ERROR: handlers.py not found. Please ensure it exists in the same directory.")
    sys.exit(1)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5009))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Flask app on port {port}")
    print(f"Debug mode: {debug_mode}")
    print(f"AWS Region: {aws_region}")
    print(f"S3 Bucket: {S3_BUCKET}")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
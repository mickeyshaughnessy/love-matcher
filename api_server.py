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

S3_BUCKET = 'mithrilmedia'
S3_PREFIX = 'lovedashmatcher/'

# Import handlers after app is configured
from handlers import register_routes

# Register all routes
register_routes(app, s3_client, S3_BUCKET, S3_PREFIX)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5009)
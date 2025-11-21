# Photo Upload Feature Specification

## Overview
Users can upload up to 3 photos of themselves. Photos are stored in S3 and URLs are saved in the user's profile JSON. Photos are only displayed to matches after both parties accept the match.

## Frontend Implementation (index.html)

### UI Components

1. **Profile View - Photo Upload Section**
   - Location: In profile-container, above or below profile stats
   - Shows current photos (if any) as thumbnails with delete option
   - Upload button (disabled if 3 photos already uploaded)
   - File input (hidden, accepts image/*, max 5MB per file)
   - Upload progress indicator

2. **Match View - Photo Display**
   - Only shown after `mutual_acceptance === true`
   - Display match's photos as a gallery
   - Click to enlarge

### API Endpoints Needed (Backend)

#### 1. Upload Photo
```
POST /profile/photos
Headers: Authorization: Bearer <token>
Content-Type: multipart/form-data
Body: { photo: <file> }

Response:
{
  "success": true,
  "photo_url": "https://s3.amazonaws.com/bucket/user_123_photo_1.jpg",
  "photos": ["url1", "url2", "url3"]  // All user's photos
}
```

#### 2. Delete Photo
```
DELETE /profile/photos
Headers: Authorization: Bearer <token>
Body: { photo_url: "https://..." }

Response:
{
  "success": true,
  "photos": ["url1", "url2"]  // Remaining photos
}
```

#### 3. Profile Structure Update
The profile JSON should include:
```json
{
  "user_id": "user@example.com",
  "name": "John Doe",
  "age": 28,
  "photos": [
    "https://s3.amazonaws.com/bucket/user_123_photo_1.jpg",
    "https://s3.amazonaws.com/bucket/user_123_photo_2.jpg",
    "https://s3.amazonaws.com/bucket/user_123_photo_3.jpg"
  ],
  "dimensions": { ... },
  ...
}
```

## Backend Implementation Needed

### S3 Configuration
- Bucket: Create dedicated bucket for user photos
- Path structure: `{user_id}/photo_{timestamp}.{ext}`
- Permissions: Private (not public)
- Pre-signed URLs: Generate for viewing (expire in 24 hours)

### API Handler (api_server.py)

```python
@app.route('/profile/photos', methods=['POST'])
@require_auth
def upload_photo():
    user_id = get_user_id_from_token(request.headers['Authorization'])
    profile = get_profile(user_id)
    
    # Check photo limit
    current_photos = profile.get('photos', [])
    if len(current_photos) >= 3:
        return jsonify({'error': 'Maximum 3 photos allowed'}), 400
    
    # Get uploaded file
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo provided'}), 400
    
    file = request.files['photo']
    
    # Validate file
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    if file_size_too_large(file):
        return jsonify({'error': 'File too large (max 5MB)'}), 400
    
    # Upload to S3
    timestamp = int(time.time())
    filename = f"{user_id}/photo_{timestamp}.{get_extension(file.filename)}"
    s3_url = upload_to_s3(file, filename)
    
    # Update profile
    current_photos.append(s3_url)
    profile['photos'] = current_photos
    save_profile(user_id, profile)
    
    return jsonify({
        'success': True,
        'photo_url': s3_url,
        'photos': current_photos
    })

@app.route('/profile/photos', methods=['DELETE'])
@require_auth
def delete_photo():
    user_id = get_user_id_from_token(request.headers['Authorization'])
    profile = get_profile(user_id)
    
    data = request.json
    photo_url = data.get('photo_url')
    
    if not photo_url:
        return jsonify({'error': 'No photo_url provided'}), 400
    
    current_photos = profile.get('photos', [])
    
    if photo_url not in current_photos:
        return jsonify({'error': 'Photo not found'}), 404
    
    # Delete from S3
    delete_from_s3(photo_url)
    
    # Update profile
    current_photos.remove(photo_url)
    profile['photos'] = current_photos
    save_profile(user_id, profile)
    
    return jsonify({
        'success': True,
        'photos': current_photos
    })
```

### S3 Helper Functions

```python
import boto3
from werkzeug.utils import secure_filename

s3_client = boto3.client('s3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

BUCKET_NAME = 'lovedash matcher-photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_extension(filename):
    return filename.rsplit('.', 1)[1].lower()

def file_size_too_large(file):
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size > MAX_FILE_SIZE

def upload_to_s3(file, filename):
    """Upload file to S3 and return URL"""
    s3_client.upload_fileobj(
        file,
        BUCKET_NAME,
        filename,
        ExtraArgs={'ContentType': file.content_type}
    )
    
    # Return S3 URL (or use CloudFront if configured)
    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"

def delete_from_s3(photo_url):
    """Delete file from S3 given its URL"""
    # Extract filename from URL
    filename = photo_url.split(f"{BUCKET_NAME}.s3.amazonaws.com/")[1]
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=filename)

def generate_presigned_url(photo_url, expiration=86400):
    """Generate presigned URL for private photo access"""
    filename = photo_url.split(f"{BUCKET_NAME}.s3.amazonaws.com/")[1]
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': filename},
        ExpiresIn=expiration
    )
```

## Security Considerations

1. **Validation**
   - Verify file is actually an image (check magic bytes, not just extension)
   - Limit file size to 5MB
   - Sanitize filename
   - Check user hasn't exceeded photo limit

2. **Access Control**
   - Photos should NOT be publicly accessible
   - Use pre-signed URLs for viewing (expire after 24h)
   - Only show photos to mutually accepted matches

3. **Content Moderation**
   - Consider implementing automated content moderation (AWS Rekognition)
   - Flag inappropriate content
   - Report mechanism for users

## Testing Checklist

- [ ] Upload single photo
- [ ] Upload 3 photos (hit limit)
- [ ] Try uploading 4th photo (should fail)
- [ ] Delete photo
- [ ] Upload after delete (should work)
- [ ] Try uploading invalid file types
- [ ] Try uploading file > 5MB
- [ ] Verify photos only shown after mutual acceptance
- [ ] Verify photos hidden if match rejected
- [ ] Test on mobile devices
- [ ] Test S3 permissions (photos should be private)

## Cost Considerations

### S3 Storage
- Average photo: ~2MB
- 3 photos per user: ~6MB
- 10,000 users: ~60GB
- Cost: ~$1.40/month

### S3 Bandwidth
- Photo views per match: ~6-10 views
- Average transfer: 10MB per mutual match
- 1,000 matches/month: ~10GB transfer
- Cost: ~$0.90/month

**Total estimated: ~$2.30/month for 10,000 users**

## Future Enhancements

1. **Image Processing**
   - Auto-resize to standard dimensions
   - Create thumbnails for faster loading
   - Strip EXIF data for privacy

2. **Advanced Features**
   - Photo verification (ensure photo is of user)
   - Photo ordering (primary photo)
   - Photo captions
   - Profile video (15-30 seconds)

3. **CDN Integration**
   - Use CloudFront for faster global delivery
   - Cache photos at edge locations

# LoveDashMatcher

## One Perfect Match at a Time

LoveDashMatcher is a relationship matchmaking service that analyzes 29 dimensions of compatibility to find your ideal partner. Unlike traditional dating apps with endless swiping, we provide **one carefully selected match at a time** for meaningful connections.

---

## 🚀 Quick Start

### For Users
1. Visit the site and click "Get Started Free"
2. Sign up with email and age
3. Build your profile through natural conversation
4. Upload up to 3 photos
5. Get matched with one compatible person
6. Accept or decline - then connect and chat

### For Developers

#### Run Locally
```bash
# Start API server
python3 api_server.py

# Open index.html in browser
open index.html
```

#### Deploy to Production
```bash
git add index.html
git commit -m "Your changes"
git push origin main

# Deploy to AWS
ssh -i ~/.ssh/mickey_2024.pem ubuntu@ec2-100-26-236-1.compute-1.amazonaws.com
cd ~/love-matcher && git pull
```

---

## 📁 Key Files

### Frontend
- `index.html` - Complete single-page application (3,092 lines)

### Backend
- `api_server.py` - Flask API server
- `handlers.py` - API request handlers
- `prompts.py` - AI matchmaking prompts
- `run_matching.py` - Matching algorithm (cron job)
- `manage_profiles.py` - Profile management tool
- `config.py` - Configuration

### Documentation
- **FINAL_CHANGES_SUMMARY.md** - Latest changes and implementation details
- **PHOTO_UPLOAD_SPEC.md** - Photo feature backend specification
- **DEPLOYMENT.md** - Deployment procedures
- **TESTING_GUIDE.md** - Testing procedures
- **MATCHING_IMPLEMENTATION.md** - Matching algorithm details
- **IMPLEMENTATION_SUMMARY.md** - System architecture

---

## 🎨 Navigation Structure

### Public Views (Not Logged In)
- **Home** - Landing page with hero, stats, about section
- **Privacy Policy** - Liberal privacy policy
- **Terms of Service** - Comprehensive terms

### Member Views (Logged In)
- **Home** - Return to landing page
- **Build Profile** - Chat to build profile, upload photos
- **Connect with Match** - View profile, basic info, matches
- **Logout** - Clear session

---

## 🔑 Key Features

### Profile Building
- Natural conversation-based
- 29-dimension compatibility analysis
- Name, age, location, custom about section
- Up to 3 photo uploads
- JSON profile viewer

### Matching
- One match at a time
- Deep compatibility scoring
- Privacy-first (profiles hidden until mutual acceptance)
- Accept/decline workflow
- Private chat after mutual acceptance

### Privacy
- Photos and full profiles hidden until mutual acceptance
- Optional passwords
- localStorage session management
- Liberal privacy policy (no guarantees)

---

## 🛠️ Backend TODO

### Required for Photo Upload
1. Implement `POST /profile/photos` endpoint
2. Implement `DELETE /profile/photos` endpoint
3. Set up S3 bucket for photo storage
4. Add `photos: []` array to profile JSON
5. See **PHOTO_UPLOAD_SPEC.md** for details

### Required for Basic Info
1. Add `name`, `location`, `about` fields to profile JSON
2. Update chat prompts to capture these first
3. Display in Connect view (already implemented in frontend)

### Estimated Work
- Photo upload backend: 2-4 hours
- Basic info fields: 1-2 hours
- Total: 3-6 hours

---

## 💎 Free Lifetime Membership

First 10,000 members get free lifetime access. Current API tracks member numbers automatically.

---

## 📞 Contact

**Email**: mickeyshaughnessy@gmail.com
**Support**: Available via email

---

## 📝 Recent Changes (Nov 11, 2025)

### Major Redesign
- Renamed "Chat with AI" → "Build Profile"
- Renamed "Profile & Match" → "Connect with Match"
- Removed Dashboard entirely
- Added photo upload feature (frontend complete)
- Added basic info section (name, location, about)
- Revised homepage to emphasize "one match at a time"
- De-emphasized AI, focused on user benefits
- Added Privacy Policy and Terms of Service
- Cleaned up documentation

### All Changes
See **FINAL_CHANGES_SUMMARY.md** for complete details.

---

## 🧪 Testing

Run integration tests:
```bash
python3 int_tests.py
```

Manual testing checklist in **TESTING_GUIDE.md**

---

## 📦 Tech Stack

- **Frontend**: Vanilla JavaScript, CSS3, HTML5
- **Backend**: Python 3, Flask
- **AI**: OpenAI API (via prompts.py)
- **Storage**: AWS S3 (profiles in JSON files, photos in S3 bucket)
- **Matching**: Custom algorithm (run_matching.py)
- **Deployment**: AWS EC2

---

## 🔒 Security Notes

- Liberal privacy policy (no guarantees)
- Optional passwords
- Photos stored in private S3 bucket
- No background checks or verification
- Use at your own risk (see Terms of Service)

---

## 📈 Architecture

### Profile Flow
1. User signs up → Creates profile JSON in S3
2. User chats → Profile updated with dimensions
3. User uploads photos → URLs added to profile JSON
4. User gets matched → Matching algorithm finds best fit
5. User accepts → Full profiles revealed
6. Users chat → Private messages stored

### Matching Flow
1. Cron job runs (run_matching.py)
2. Finds active users with sufficient profile completion
3. Calculates compatibility scores (29 dimensions)
4. Creates one match per user
5. Users notified in Connect view

---

## 🎯 Project Goals

1. **Quality over Quantity**: One match at a time, not endless options
2. **Deep Compatibility**: 29 dimensions, not superficial swipes
3. **Privacy First**: Full profiles hidden until mutual interest
4. **Real Connections**: Encourage meaningful relationships
5. **Free Access**: First 10,000 members get lifetime free access

---

**Version**: 2.0 (Major Redesign)
**Last Updated**: November 11, 2025
**Status**: Production Ready ✅

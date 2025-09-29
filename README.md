# LoveDashMatcher - AI-Powered Lifetime Matching Service

## Overview
LoveDashMatcher is an AI-powered dating service that uses conversational profiling to create deep, meaningful matches. Users pay a one-time lifetime fee via XMoney and engage with an AI chatbot to build a comprehensive personality profile across 29 dimensions.

## Architecture
- **Backend**: Flask API server with JWT authentication
- **Storage**: AWS S3 bucket (mithrilmedia/lovedashmatcher)
- **Frontend**: Single-page responsive web application
- **Payments**: XMoney integration for lifetime access
- **Matching**: Daily algorithm execution with push notifications

## Quick Start

### Prerequisites
```bash
# Python 3.8+
python --version

# Node.js 14+ (for frontend development)
node --version
```

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/lovedashmatcher.git
cd lovedashmatcher

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables (.env)
```
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET=mithrilmedia/lovedashmatcher
XMONEY_API_KEY=your-xmoney-api-key
XMONEY_SECRET=your-xmoney-secret
OPENAI_API_KEY=your-openai-api-key
JWT_SECRET_KEY=your-jwt-secret
PUSH_NOTIFICATION_KEY=your-push-key
```

### Local Development
```bash
# Start Flask API server
python api_server.py

# In another terminal, serve the frontend
python -m http.server 8080 --directory frontend

# Access application at http://localhost:8080
```

## API Endpoints

### Authentication
- `POST /api/register` - Create new user account
- `POST /api/login` - Authenticate and receive JWT token

### Profile Management
- `GET /api/profile` - Retrieve user profile
- `PUT /api/profile` - Update profile data
- `POST /api/chat` - Conversational profile building

### Matching
- `GET /api/matches` - Get current matches
- `GET /api/matches/history` - View match history

### Payment
- `POST /api/payment/initiate` - Start XMoney payment
- `GET /api/payment/status` - Check payment status

### System
- `GET /api/ping` - Health check
- `POST /api/notifications/subscribe` - Enable push notifications

## User Journey Flow

1. **Registration**: User provides basic info and verifies age (18+)
2. **Payment**: One-time lifetime fee via XMoney ($49.99)
3. **Profile Building**: AI-guided chat to build comprehensive profile
4. **Daily Matching**: Algorithm runs daily at 2 AM UTC
5. **Notifications**: Push alerts for new matches
6. **Communication**: In-app messaging with matches

## Project Structure
```
lovedashmatcher/
├── api_server.py           # Flask application entry point
├── handlers.py             # API endpoint implementations
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── frontend/
│   ├── index.html         # Single-page application
│   ├── app.js            # Frontend JavaScript
│   └── styles.css        # Application styles
├── docs/
│   └── api_docs.html     # Interactive API documentation
└── scripts/
    ├── setup_s3.py       # S3 bucket initialization
    └── daily_matcher.py  # Matching algorithm cron job
```

## S3 Storage Structure
```
mithrilmedia/lovedashmatcher/
├── profiles/
│   ├── {userId}.json              # User profiles
│   └── {userId}_history.json      # Chat logs
├── matches/
│   └── {userId}_matches.json      # Match data
├── payments/
│   └── {userId}_payment.json      # Payment records
├── system/
│   ├── active_users.json          # Matchable users
│   └── daily_logs/                # Algorithm logs
└── notifications/
    └── {userId}_queue.json        # Push queue
```

## Profile Dimensions (29 Total)
1. Core Values
2. Life Goals
3. Communication Style
4. Conflict Resolution
5. Love Language
6. Attachment Style
7. Emotional Intelligence
8. Financial Philosophy
9. Career Ambition
10. Family Planning
11. Religious/Spiritual Beliefs
12. Political Alignment
13. Lifestyle Preferences
14. Social Energy
15. Hobbies & Interests
16. Travel Preferences
17. Health & Fitness
18. Diet & Food
19. Entertainment Preferences
20. Humor Style
21. Risk Tolerance
22. Decision Making
23. Time Management
24. Cleanliness Standards
25. Pet Preferences
26. Cultural Background
27. Education Level
28. Geographic Flexibility
29. Relationship Experience

## Deployment

### AWS Setup
```bash
# Configure AWS CLI
aws configure

# Create S3 bucket
aws s3 mb s3://mithrilmedia
aws s3api put-bucket-policy --bucket mithrilmedia --policy file://bucket-policy.json

# Initialize S3 structure
python scripts/setup_s3.py
```

### Production Deployment (Heroku)
```bash
# Create Heroku app
heroku create lovedashmatcher

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-production-secret
# ... set all other env vars

# Deploy
git push heroku main

# Scale dynos
heroku ps:scale web=2
```

### Daily Matcher Cron Job
```bash
# Add to crontab
0 2 * * * /usr/bin/python /path/to/daily_matcher.py

# Or use Heroku Scheduler
heroku addons:create scheduler:standard
heroku addons:open scheduler
# Add job: python scripts/daily_matcher.py
```

## Security & Compliance

- **Age Verification**: Strict 18+ requirement with verification
- **Data Protection**: All user data encrypted at rest in S3
- **GDPR Compliance**: Data export and deletion capabilities
- **Payment Security**: PCI compliance via XMoney
- **Authentication**: JWT tokens with 24-hour expiration
- **HTTPS**: Required for all production endpoints

## Development Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests: `pytest tests/`
3. Run linting: `flake8 *.py`
4. Test locally with mock S3: `python -m pytest tests/ --mock-s3`
5. Submit pull request with description

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_handlers.py

# Mock S3 for local testing
pytest --mock-s3
```

## Monitoring & Analytics

- **Application Monitoring**: New Relic or DataDog integration
- **Error Tracking**: Sentry for exception monitoring
- **Analytics**: Google Analytics for user behavior
- **Uptime Monitoring**: Pingdom or UptimeRobot

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit changes with clear messages
4. Write/update tests as needed
5. Update documentation
6. Submit pull request

## Support

- **Documentation**: See `/docs/api_docs.html`
- **Issues**: GitHub Issues for bug reports
- **Email**: support@lovedashmatcher.com
- **Discord**: Join our developer community

## License

MIT License - see LICENSE file for details

## Acknowledgments

- OpenAI for GPT integration
- XMoney for payment processing
- AWS for reliable infrastructure
- Flask community for excellent framework
# Love Matcher

A public-algorithm for matchmaking to help adults find love, marry, and raise children.

[www.love-matcher.com](https://www.love-matcher.com)
## Project Structure

```
love-matcher/
│   ├── __init__.py
│   ├── api_server.py
│   ├── models.py
│   └── utils.py
│   └── int_tests.py
│   ├── gen.py
│   └── train_retention_model.py
│   ├── index.html
│   ├── styles.css
│   └── script.js
└---── README.md
```

## Key Components

1. `api_server.py`: Main Flask application with API endpoints.
2. `models.py`: Data models for User, Match, and Message, including Redis operations.
3. `utils.py`: Utility functions for matching algorithm and compatibility scoring.
4. `test_integration.py`: Integration tests for the API.
5. `generate_simulated_data.py`: Script to generate simulated user data.
6. `train_retention_model.py`: Script to train the user retention model.
7. Frontend files: `index.html`, `styles.css`, and `script.js` for the web interface.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up Redis:
   Make sure Redis is installed and running on your system.

3. Run the application:
   ```
   python api/api_server.py
   ```

## API Endpoints

- `GET /ping`: Health check
- `POST /api/users`: Create a new user
- `GET /api/users/<user_id>`: Get user profile
- `DELETE /api/users/<user_id>`: Delete user account
- `PUT /api/users/<user_id>/preferences`: Update user preferences
- `POST /api/messages`: Send a message
- `POST /api/match`: accept or decline a match 
- `GET /api/messages/<user_id>`: Get messages for a user
- `GET /api/users/<user_id>/stats`: Get user statistics

## Testing

Run integration tests using:
```
python -m pytest tests/test_integration.py
```

## Data Generation and Model Training

- Generate simulated data:
  ```
  python scripts/generate_simulated_data.py
  ```

- Train the retention model:
  ```
  python scripts/train_retention_model.py
  ```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

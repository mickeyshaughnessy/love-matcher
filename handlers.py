from flask import request, jsonify
from functools import wraps
import jwt
from datetime import datetime, timedelta
from jwt import PyJWKClient
import json
import requests
import bcrypt

import config

# Global variables to be set by api_server
s3_client = None
S3_BUCKET = None
S3_PREFIX = None
jwt_secret = None
openrouter_config = None  # Will hold OpenRouter configuration

# Clerk configuration
CLERK_JWKS_URL = "https://api.clerk.com/v1/jwks"
clerk_jwks_client = None

# Constants
FIRST_10K_FREE_LIMIT = 10000
MEMBER_LIST_KEY = "member_list.json"

# System prompt for the matchmaking AI
SYSTEM_PROMPT = """You are LoveDashMatcher, an AI matchmaking service for people seeking lasting relationships and traditional marriage. Build compatibility profiles by asking ONE question at a time in natural conversation.

## Core Process:
1. Welcome users warmly (if under 18, note matching available at 18)
2. Ask ONE focused question per response
3. Acknowledge their answer briefly (one sentence)
4. Move to the next unfilled dimension

## 29 Dimensions to Gather:
age, location, education, career, finances, family_origin, children, religion, politics, communication, conflict, health, mental_health, social_energy, domestic, cleanliness, food, travel, hobbies, culture, humor, affection, independence, decisions, time, technology, pets, substances, vision

## Response Format (REQUIRED):
[DIMENSION: dimension_name]
[VALUE: extracted_value]
[ACKNOWLEDGMENT: one sentence acknowledgment]
[NEXT_QUESTION: your next question]

For initial greetings:
[DIMENSION: none]
[VALUE: none]
[ACKNOWLEDGMENT: brief welcome]
[NEXT_QUESTION: first question]

## Communication Style:
- Be concise and natural
- One question only
- Brief acknowledgments (1 sentence max)
- Skip already-filled dimensions
- Keep it conversational, not clinical

## Policies:
- 18+ for matching pool (younger can build profiles)
- Traditional heterosexual marriage focus
- Single/unmarried users only
- Strict confidentiality
- No promises about matches
- One profile, one match per person

Your job: Understand each person deeply through focused questions, ONE AT A TIME."""

# Clerk JWT verification
def verify_clerk_token(token):
    """Verify Clerk session token and return user data"""
    try:
        # Get signing key from Clerk's JWKS
        signing_key = clerk_jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and verify token
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}  # Clerk tokens don't always have audience
        )
        
        return data
    except Exception as e:
        print(f"Clerk token verification failed: {e}")
        return None

# JWT decorator - supports both Clerk and legacy tokens
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        
        try:
            token = token.replace('Bearer ', '')
            
            # Try Clerk token first
            clerk_data = verify_clerk_token(token)
            if clerk_data:
                # Clerk token verified - extract user ID
                clerk_user_id = clerk_data.get('sub')  # Clerk uses 'sub' for user ID
                # Map Clerk user ID to our internal user ID format
                request.user_id = f"clerk_{clerk_user_id}"
                request.clerk_user_id = clerk_user_id
                request.clerk_email = clerk_data.get('email')
                return f(*args, **kwargs)
            
            # Fallback to legacy JWT for backward compatibility
            data = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            request.user_id = data['user_id']
            request.clerk_user_id = None
            request.clerk_email = None
            
        except Exception as e:
            print(f"Token verification failed: {e}")
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated

# Helper functions
def s3_get(key):
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}{key}")
        return json.loads(response['Body'].read())
    except:
        return None

def s3_put(key, data):
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_PREFIX}{key}",
        Body=json.dumps(data),
        ContentType='application/json'
    )

def get_member_count():
    """Get current member count from S3"""
    member_list = s3_get(MEMBER_LIST_KEY)
    if not member_list:
        return 0
    return len(member_list.get('members', []))

def add_to_member_list(user_id, email, age, registration_time):
    """Add new member to the member list and return member number"""
    member_list = s3_get(MEMBER_LIST_KEY) or {'members': [], 'created_at': datetime.utcnow().isoformat()}
    
    member_number = len(member_list['members']) + 1
    
    new_member = {
        'member_number': member_number,
        'user_id': user_id,
        'email': email,
        'age': age,
        'registration_time': registration_time,
        'is_free': member_number <= FIRST_10K_FREE_LIMIT
    }
    
    member_list['members'].append(new_member)
    member_list['updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(MEMBER_LIST_KEY, member_list)
    return member_number

def is_member_free(member_number):
    """Check if member gets free access based on signup order"""
    return member_number <= FIRST_10K_FREE_LIMIT

def call_openrouter_llm(messages):
    """Call OpenRouter API with configured model"""
    try:
        api_key = getattr(config, 'OPENROUTER_API_KEY', None)
        if not api_key:
            raise ValueError('OpenRouter API key not found in config.py')

        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://lovedashmatcher.com',
            'X-Title': 'LoveDashMatcher'
        }
        
        payload = {
            'model': openrouter_config['model'],
            'messages': messages,
            'temperature': openrouter_config['temperature'],
            'max_tokens': openrouter_config['max_tokens']
        }
        
        print(f"🤖 Calling OpenRouter with model: {openrouter_config['model']}")
        
        response = requests.post(
            openrouter_config['api_url'],
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📥 OpenRouter response status: {response.status_code}")
        
        try:
            result = response.json()
        except ValueError:
            result = None
        
        if response.status_code >= 400:
            error_message = None
            if isinstance(result, dict):
                error_message = (
                    result.get('error', {}).get('message')
                    or result.get('error', {}).get('details')
                    or result.get('message')
                )
            if not error_message:
                error_message = response.text.strip() or f"HTTP {response.status_code} error"
            print(f"❌ OpenRouter returned error: {error_message}")
            return {
                'error': error_message,
                'status_code': response.status_code,
                'raw_response': result if result is not None else response.text
            }
        
        if isinstance(result, dict) and 'choices' in result and len(result['choices']) > 0:
            print(f"✅ Successfully got response from {result.get('model', 'unknown model')}")
            return {
                'content': result['choices'][0]['message']['content'],
                'model': result.get('model', openrouter_config['model']),
                'usage': result.get('usage', {}),
                'raw_response': result
            }
        else:
            print(f"❌ Unexpected OpenRouter response format: {result}")
            return {
                'error': 'Unexpected OpenRouter response format',
                'raw_response': result if result is not None else response.text
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenRouter API error: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return {
            'error': str(e),
            'status_code': getattr(getattr(e, 'response', None), 'status_code', None),
            'raw_response': getattr(getattr(e, 'response', None), 'text', None)
        }
    except Exception as e:
        print(f"❌ Unexpected error calling OpenRouter: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e)
        }

def parse_llm_response(response_text):
    """Parse structured response from LLM to extract dimension data"""
    parsed = {
        'dimension': None,
        'value': None,
        'acknowledgment': '',
        'next_question': '',
        'display_text': response_text  # Fallback to full text
    }
    
    try:
        # Extract dimension
        dim_match = response_text.find('[DIMENSION:')
        if dim_match != -1:
            dim_end = response_text.find(']', dim_match)
            if dim_end != -1:
                parsed['dimension'] = response_text[dim_match+11:dim_end].strip()
        
        # Extract value
        val_match = response_text.find('[VALUE:')
        if val_match != -1:
            val_end = response_text.find(']', val_match)
            if val_end != -1:
                parsed['value'] = response_text[val_match+7:val_end].strip()
        
        # Extract acknowledgment
        ack_match = response_text.find('[ACKNOWLEDGMENT:')
        if ack_match != -1:
            ack_end = response_text.find(']', ack_match)
            if ack_end != -1:
                parsed['acknowledgment'] = response_text[ack_match+16:ack_end].strip()
        
        # Extract next question
        q_match = response_text.find('[NEXT_QUESTION:')
        if q_match != -1:
            q_end = response_text.find(']', q_match)
            if q_end != -1:
                parsed['next_question'] = response_text[q_match+15:q_end].strip()
        
        # Build display text from acknowledgment and next question
        if parsed['acknowledgment'] or parsed['next_question']:
            display_parts = []
            if parsed['acknowledgment']:
                display_parts.append(parsed['acknowledgment'])
            if parsed['next_question']:
                display_parts.append(parsed['next_question'])
            parsed['display_text'] = ' '.join(display_parts)
    
    except Exception as e:
        print(f"⚠️ Error parsing LLM response: {e}")
        # Return original text if parsing fails
    
    return parsed

def build_profile_context(profile):
    """Build context string from user profile for LLM"""
    context_parts = []
    
    if profile.get('age'):
        age = profile['age']
        context_parts.append(f"Age: {age}")
        if age < 18:
            context_parts.append(f"⚠️ User is under 18 - can explore service but matching delayed until age 18")
    
    matching_status = "Eligible for matching" if profile.get('matching_eligible') else "Not yet eligible for matching"
    context_parts.append(f"Matching Status: {matching_status}")
    
    # List dimensions already gathered
    dimensions_filled = profile.get('dimensions', {})
    dimensions_count = len(dimensions_filled)
    context_parts.append(f"\n📊 Profile Dimensions: {dimensions_count}/29 completed")
    
    if dimensions_filled:
        context_parts.append("\nDimensions already gathered:")
        for key in dimensions_filled.keys():
            context_parts.append(f"  ✓ {key}")
        
        context_parts.append("\nDimension details:")
        for key, value in dimensions_filled.items():
            if isinstance(value, dict):
                context_parts.append(f"- {key}: {json.dumps(value, indent=2)}")
            else:
                context_parts.append(f"- {key}: {value}")
    
    # List dimensions still needed
    all_dimensions = [
        'age', 'location', 'education', 'career', 'finances', 'family_origin',
        'children', 'religion', 'politics', 'communication', 'conflict', 'health',
        'mental_health', 'social_energy', 'domestic', 'cleanliness', 'food',
        'travel', 'hobbies', 'culture', 'humor', 'affection', 'independence',
        'decisions', 'time', 'technology', 'pets', 'substances', 'vision'
    ]
    
    remaining_dimensions = [d for d in all_dimensions if d not in dimensions_filled]
    if remaining_dimensions:
        context_parts.append(f"\nDimensions still needed ({len(remaining_dimensions)}):")
        context_parts.append(f"  {', '.join(remaining_dimensions[:10])}")
        if len(remaining_dimensions) > 10:
            context_parts.append(f"  ... and {len(remaining_dimensions) - 10} more")
    
    member_number = profile.get('member_number')
    if member_number:
        context_parts.append(f"\n🎫 Member #{member_number}")
    
    if profile.get('is_free_member'):
        context_parts.append("💎 Status: Free lifetime member")
    
    conversation_count = profile.get('conversation_count', 0)
    context_parts.append(f"💬 Conversations: {conversation_count}")
    
    if context_parts:
        return "\n".join(context_parts)
    return "New user - starting profile building process"

# Route handlers
def ping():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    age = data.get('age')
    
    if not all([email, password, age]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    age_int = int(age)
    matching_eligible = age_int >= 18
    
    # Check if user exists
    user_id = email.replace('@', '_').replace('.', '_')
    if s3_get(f"profiles/{user_id}.json"):
        return jsonify({'error': 'User already exists'}), 400
    
    # Hash password
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    # Add to member list and get member number
    registration_time = datetime.utcnow().isoformat()
    member_number = add_to_member_list(user_id, email, age_int, registration_time)
    is_free = is_member_free(member_number)
    
    # Determine payment status
    if is_free:
        payment_status = 'free' if matching_eligible else 'free_pending_age'
    else:
        payment_status = 'payment_required'
    
    # Create user profile
    profile = {
        'user_id': user_id,
        'email': email,
        'password_hash': password_hash,
        'age': age_int,
        'member_number': member_number,
        'created_at': registration_time,
        'payment_status': payment_status,
        'matching_eligible': matching_eligible,
        'profile_complete': False,
        'conversation_count': 0,
        'dimensions': {},
        'is_free_member': is_free
    }
    
    s3_put(f"profiles/{user_id}.json", profile)
    
    # Generate token
    token = jwt.encode(
        {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=1)},
        jwt_secret,
        algorithm='HS256'
    )
    
    response_data = {
        'token': token, 
        'user_id': user_id,
        'member_number': member_number,
        'matching_eligible': matching_eligible,
        'is_free_member': is_free
    }
    
    # Add appropriate message based on status
    if not matching_eligible:
        response_data['message'] = "Welcome! You can explore LoveDashMatcher and build your profile. Matching will be available when you turn 18."
    elif is_free:
        response_data['message'] = f"Welcome! You're member #{member_number} with free lifetime access to LoveDashMatcher!"
    else:
        response_data['message'] = f"Welcome! You're member #{member_number}. Payment required for matching services."
    
    return jsonify(response_data)

def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user_id = email.replace('@', '_').replace('.', '_')
    
    profile = s3_get(f"profiles/{user_id}.json")
    if not profile:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Verify password
    stored_hash = profile.get('password_hash')
    if not stored_hash:
        return jsonify({'error': 'Account error - please contact support'}), 500
    
    if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    token = jwt.encode(
        {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=1)},
        jwt_secret,
        algorithm='HS256'
    )
    
    return jsonify({'token': token, 'user_id': user_id})

@token_required
def sync_clerk_user():
    """Sync or create user profile from Clerk authentication"""
    data = request.json
    age = data.get('age')
    
    if not age:
        return jsonify({'error': 'Age is required'}), 400
    
    age_int = int(age)
    matching_eligible = age_int >= 18
    
    # Use Clerk user ID as primary identifier
    clerk_user_id = request.clerk_user_id
    user_id = request.user_id  # This is clerk_{clerk_user_id}
    email = request.clerk_email
    
    # Check if profile already exists
    profile = s3_get(f"profiles/{user_id}.json")
    
    if profile:
        # Update existing profile
        profile['age'] = age_int
        profile['matching_eligible'] = matching_eligible
        profile['email'] = email
        profile['updated_at'] = datetime.utcnow().isoformat()
        
        # Update payment status if age changed
        if matching_eligible and profile.get('is_free_member', False):
            profile['payment_status'] = 'free'
        
        s3_put(f"profiles/{user_id}.json", profile)
        
        return jsonify({
            'user_id': user_id,
            'member_number': profile.get('member_number'),
            'matching_eligible': matching_eligible,
            'is_free_member': profile.get('is_free_member', False),
            'message': 'Profile updated successfully'
        })
    
    # Create new profile
    registration_time = datetime.utcnow().isoformat()
    member_number = add_to_member_list(user_id, email, age_int, registration_time)
    is_free = is_member_free(member_number)
    
    # Determine payment status
    if is_free:
        payment_status = 'free' if matching_eligible else 'free_pending_age'
    else:
        payment_status = 'payment_required'
    
    profile = {
        'user_id': user_id,
        'clerk_user_id': clerk_user_id,
        'email': email,
        'age': age_int,
        'member_number': member_number,
        'created_at': registration_time,
        'payment_status': payment_status,
        'matching_eligible': matching_eligible,
        'profile_complete': False,
        'conversation_count': 0,
        'dimensions': {},
        'is_free_member': is_free,
        'auth_provider': 'clerk'
    }
    
    s3_put(f"profiles/{user_id}.json", profile)
    
    response_data = {
        'user_id': user_id,
        'member_number': member_number,
        'matching_eligible': matching_eligible,
        'is_free_member': is_free
    }
    
    # Add appropriate message based on status
    if not matching_eligible:
        response_data['message'] = "Welcome! You can explore LoveDashMatcher and build your profile. Matching will be available when you turn 18."
    elif is_free:
        response_data['message'] = f"Welcome! You're member #{member_number} with free lifetime access to LoveDashMatcher!"
    else:
        response_data['message'] = f"Welcome! You're member #{member_number}. Payment required for matching services."
    
    return jsonify(response_data)

@token_required
def get_profile():
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    return jsonify(profile)

@token_required
def update_profile():
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    data = request.json
    
    # If user is updating age and becomes 18+, update matching eligibility
    if 'age' in data:
        new_age = int(data['age'])
        if new_age >= 18 and not profile.get('matching_eligible', False):
            profile['matching_eligible'] = True
            # Update payment status if they're a free member
            if profile.get('is_free_member', False):
                profile['payment_status'] = 'free'
    
    profile.update(data)
    profile['updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(f"profiles/{request.user_id}.json", profile)
    return jsonify(profile)

@token_required
def chat():
    """Chat endpoint with OpenRouter LLM integration"""
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Load user profile
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    # Increment conversation count
    profile['conversation_count'] = profile.get('conversation_count', 0) + 1
    s3_put(f"profiles/{request.user_id}.json", profile)
    
    # Load chat history
    history_key = f"chat/{request.user_id}_history.json"
    chat_history = s3_get(history_key) or {'messages': [], 'created_at': datetime.utcnow().isoformat()}
    
    # Build profile context for system message
    profile_context = build_profile_context(profile)
    
    # Construct messages for LLM
    messages = [
        {
            'role': 'system',
            'content': f"{SYSTEM_PROMPT}\n\n{'='*60}\nCURRENT USER CONTEXT:\n{'='*60}\n{profile_context}\n{'='*60}\n\nRemember: Focus on understanding this person deeply across the 29 dimensions. Ask natural, engaging questions. Build a rich profile for the matching algorithm."
        }
    ]
    
    # Add conversation history (last 20 exchanges to keep context manageable)
    recent_messages = chat_history['messages'][-40:] if chat_history['messages'] else []
    for msg in recent_messages:
        messages.append({'role': 'user', 'content': msg['user']})
        messages.append({'role': 'assistant', 'content': msg['ai']})
    
    # Add current user message
    messages.append({'role': 'user', 'content': user_message})
    
    # Call OpenRouter LLM
    llm_response = call_openrouter_llm(messages)
    
    ai_response = "I'm sorry, I'm having trouble processing that right now. Could you try again?"
    parsed_response = None
    
    if llm_response and 'content' in llm_response:
        raw_ai_response = llm_response['content']
        # Parse the structured response
        parsed_response = parse_llm_response(raw_ai_response)
        ai_response = parsed_response['display_text']
        
        # Update profile dimensions if we extracted dimension data
        if parsed_response['dimension'] and parsed_response['dimension'] != 'none':
            if parsed_response['value'] and parsed_response['value'] != 'none':
                if 'dimensions' not in profile:
                    profile['dimensions'] = {}
                
                # Store the dimension value
                profile['dimensions'][parsed_response['dimension']] = parsed_response['value']
                
                # Calculate completion percentage
                dimensions_count = len(profile['dimensions'])
                profile['completion_percentage'] = round((dimensions_count / 29) * 100)
                
                # Mark profile as complete if all 29 dimensions filled
                if dimensions_count >= 29:
                    profile['profile_complete'] = True
                
                # Save updated profile
                s3_put(f"profiles/{request.user_id}.json", profile)
                
                print(f"✅ Updated dimension '{parsed_response['dimension']}' - Profile now {dimensions_count}/29 complete")
        
    elif llm_response and 'error' in llm_response:
        ai_response = f"LLM Error: {llm_response['error']}"
    
    # Store in chat history
    chat_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'user': user_message,
        'ai': ai_response
    }
    
    # Add parsed dimension info to chat entry for debugging
    if parsed_response:
        chat_entry['parsed_dimension'] = parsed_response['dimension']
        chat_entry['parsed_value'] = parsed_response['value']
    
    # Add model info if available
    if llm_response:
        chat_entry['model'] = llm_response.get('model', 'unknown')
        chat_entry['usage'] = llm_response.get('usage', {})
        if 'raw_response' in llm_response:
            chat_entry['raw_response'] = llm_response['raw_response']
        if 'status_code' in llm_response:
            chat_entry['status_code'] = llm_response['status_code']
    
    chat_history['messages'].append(chat_entry)
    chat_history['updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(history_key, chat_history)
    
    response_payload = {
        'response': ai_response,
        'timestamp': chat_entry['timestamp']
    }
    
    # Add profile completion info
    if profile.get('dimensions'):
        response_payload['profile_completion'] = {
            'count': len(profile['dimensions']),
            'percentage': profile.get('completion_percentage', 0),
            'complete': profile.get('profile_complete', False)
        }
    
    if llm_response:
        if 'model' in llm_response:
            response_payload['model'] = llm_response.get('model')
        if 'usage' in llm_response:
            response_payload['usage'] = llm_response.get('usage')
        if 'raw_response' in llm_response:
            response_payload['raw_response'] = llm_response.get('raw_response')
        if 'error' in llm_response:
            response_payload['error'] = llm_response.get('error')
        if 'status_code' in llm_response:
            response_payload['status_code'] = llm_response.get('status_code')
    
    return jsonify(response_payload)

@token_required
def get_chat_history():
    """Get user's chat history"""
    history_key = f"chat/{request.user_id}_history.json"
    chat_history = s3_get(history_key) or {'messages': [], 'created_at': datetime.utcnow().isoformat()}
    
    return jsonify({
        'messages': chat_history.get('messages', []),
        'total_messages': len(chat_history.get('messages', []))
    })

@token_required
def get_current_match():
    """Get user's current match (at most one)"""
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    # Check if user is eligible for matching
    if not profile.get('matching_eligible', False):
        return jsonify({
            'match': None,
            'message': 'Matching will be available when you turn 18. Keep building your profile!'
        })
    
    # Check payment status
    payment_status = profile.get('payment_status', 'payment_required')
    if payment_status not in ['free', 'completed']:
        return jsonify({
            'match': None,
            'message': 'Payment required to access matching services. Please complete your payment to continue.',
            'payment_required': True
        })
    
    # Get current match
    match_id = profile.get('current_match_id')
    if not match_id:
        return jsonify({
            'match': None,
            'matching_active': profile.get('matching_active', True),
            'message': 'No match yet. Complete your profile to improve matching!'
        })
    
    # Load match profile (limited info)
    match_profile = s3_get(f"profiles/{match_id}.json")
    if not match_profile:
        # Match profile deleted, clear the match
        profile['current_match_id'] = None
        s3_put(f"profiles/{request.user_id}.json", profile)
        return jsonify({'match': None})
    
    # Return limited match info
    match_info = {
        'match_id': match_id,
        'age': match_profile.get('age'),
        'match_score': profile.get('match_score', 0),
        'matched_at': profile.get('matched_at'),
        'dimensions': match_profile.get('dimensions', {}),
        'matching_active': profile.get('matching_active', True)
    }
    
    return jsonify({'match': match_info})

@token_required
def toggle_matching_active():
    """Toggle user's active/inactive status for matching"""
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    data = request.json
    active = data.get('active', True)
    
    profile['matching_active'] = active
    profile['matching_active_updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(f"profiles/{request.user_id}.json", profile)
    
    return jsonify({
        'matching_active': active,
        'message': 'Matching activated' if active else 'Matching paused'
    })

@token_required
def reject_match():
    """Reject current match and return to matching pool"""
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    match_id = profile.get('current_match_id')
    if not match_id:
        return jsonify({'error': 'No current match to reject'}), 400
    
    # Add to rejected list
    if 'rejected_matches' not in profile:
        profile['rejected_matches'] = []
    profile['rejected_matches'].append(match_id)
    
    # Clear current match
    profile['current_match_id'] = None
    profile['match_score'] = None
    profile['matched_at'] = None
    profile['match_rejected_at'] = datetime.utcnow().isoformat()
    
    s3_put(f"profiles/{request.user_id}.json", profile)
    
    # Update other user's profile
    match_profile = s3_get(f"profiles/{match_id}.json")
    if match_profile:
        match_profile['current_match_id'] = None
        match_profile['match_score'] = None
        match_profile['matched_at'] = None
        s3_put(f"profiles/{match_id}.json", match_profile)
    
    return jsonify({
        'message': 'Match rejected. You will be matched with someone new in the next matching cycle.',
        'matching_active': profile.get('matching_active', True)
    })

@token_required
def send_match_message():
    """Send message to current match"""
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    match_id = profile.get('current_match_id')
    if not match_id:
        return jsonify({'error': 'No current match'}), 400
    
    message = request.json.get('message')
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    # Determine chat key (consistent ordering)
    user_ids = sorted([request.user_id, match_id])
    chat_key = f"match_chats/{user_ids[0]}_{user_ids[1]}.json"
    
    # Load or create chat
    chat = s3_get(chat_key) or {
        'user1_id': user_ids[0],
        'user2_id': user_ids[1],
        'created_at': datetime.utcnow().isoformat(),
        'messages': []
    }
    
    # Add message
    chat['messages'].append({
        'from': request.user_id,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    })
    chat['updated_at'] = datetime.utcnow().isoformat()
    
    s3_put(chat_key, chat)
    
    return jsonify({
        'success': True,
        'timestamp': chat['messages'][-1]['timestamp']
    })

@token_required
def get_match_messages():
    """Get messages with current match"""
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    match_id = profile.get('current_match_id')
    if not match_id:
        return jsonify({'error': 'No current match'}), 400
    
    # Determine chat key
    user_ids = sorted([request.user_id, match_id])
    chat_key = f"match_chats/{user_ids[0]}_{user_ids[1]}.json"
    
    chat = s3_get(chat_key) or {'messages': []}
    
    return jsonify({
        'messages': chat.get('messages', []),
        'match_id': match_id
    })

@token_required
def initiate_payment():
    profile = s3_get(f"profiles/{request.user_id}.json")
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    # Check if user is a free member
    if profile.get('is_free_member', False):
        return jsonify({
            'error': 'You have free lifetime access - no payment required!',
            'member_number': profile.get('member_number'),
            'is_free_member': True
        }), 400
    
    # Placeholder for XMoney integration
    return jsonify({
        'payment_url': 'https://xmoney.example.com/pay/placeholder',
        'amount': 49.99,
        'currency': 'USD',
        'member_number': profile.get('member_number')
    })

def get_member_stats():
    """Get membership statistics - public endpoint, no auth required"""
    member_list = s3_get(MEMBER_LIST_KEY)
    if not member_list:
        return jsonify({
            'total_members': 0,
            'free_members': 0,
            'paid_members': 0,
            'spots_remaining': FIRST_10K_FREE_LIMIT
        })
    
    members = member_list.get('members', [])
    total_members = len(members)
    free_members = sum(1 for m in members if m.get('is_free', False))
    paid_members = total_members - free_members
    spots_remaining = max(0, FIRST_10K_FREE_LIMIT - total_members)
    
    return jsonify({
        'total_members': total_members,
        'free_members': free_members,
        'paid_members': paid_members,
        'spots_remaining': spots_remaining,
        'free_limit': FIRST_10K_FREE_LIMIT
    })

# Register all routes with the Flask app
def register_routes(app, s3_client_instance, s3_bucket, s3_prefix, openrouter_cfg):
    global s3_client, S3_BUCKET, S3_PREFIX, jwt_secret, openrouter_config, clerk_jwks_client
    s3_client = s3_client_instance
    S3_BUCKET = s3_bucket
    S3_PREFIX = s3_prefix
    jwt_secret = app.config['JWT_SECRET']
    openrouter_config = openrouter_cfg
    
    # Initialize Clerk JWKS client for token verification
    clerk_jwks_client = PyJWKClient(CLERK_JWKS_URL)
    
    app.add_url_rule('/ping', 'ping', ping, methods=['GET'])
    app.add_url_rule('/register', 'register', register, methods=['POST'])
    app.add_url_rule('/login', 'login', login, methods=['POST'])
    app.add_url_rule('/clerk/sync', 'sync_clerk_user', sync_clerk_user, methods=['POST'])
    app.add_url_rule('/profile', 'get_profile', get_profile, methods=['GET'])
    app.add_url_rule('/profile', 'update_profile', update_profile, methods=['PUT'])
    app.add_url_rule('/chat', 'chat', chat, methods=['POST'])
    app.add_url_rule('/chat/history', 'get_chat_history', get_chat_history, methods=['GET'])
    app.add_url_rule('/match', 'get_current_match', get_current_match, methods=['GET'])
    app.add_url_rule('/match/toggle', 'toggle_matching_active', toggle_matching_active, methods=['POST'])
    app.add_url_rule('/match/reject', 'reject_match', reject_match, methods=['POST'])
    app.add_url_rule('/match/messages', 'get_match_messages', get_match_messages, methods=['GET'])
    app.add_url_rule('/match/messages', 'send_match_message', send_match_message, methods=['POST'])
    app.add_url_rule('/payment/initiate', 'initiate_payment', initiate_payment, methods=['POST'])
    app.add_url_rule('/stats', 'get_member_stats', get_member_stats, methods=['GET'])
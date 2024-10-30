import requests, json, config, time, re, logging
from collections import Counter

"""
🤔 LLM Service Matching Module
- Fixed provider capabilities string handling
- Other functionality unchanged
<Flow> 
1. Take clean descriptions and capabilities
2. Try LLM providers in sequence
3. Fallback to keyword matching if needed
</Flow>
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_CONFIGS = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/complete",
        "default_model": "claude-3-haiku-20240307",
        "headers": lambda: {
            "Content-Type": "application/json", 
            "x-api-key": config.anthropic_API_key,
            "anthropic-version": "2024-03-01"
        }
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "mixtral-8x7b-32768",
        "headers": lambda: {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.groq_API_key}"
        }
    },
    "ollama": {
        "url": "http://localhost:11434/api/generate",
        "default_model": "mistral",
        "headers": lambda: {"Content-Type": "application/json"}
    }
}

def keyword_match(description, capabilities, threshold=0.3):
    if not description or not capabilities: return False
    words = re.findall(r'\w+', description.lower())
    capabilities = [c.lower() for c in capabilities]
    matches = sum(1 for word in words if any(cap in word or word in cap for cap in capabilities))
    if len(words) < 5: threshold = 0.2
    return (matches / len(words)) >= threshold if words else False

def generate_completion(prompt, api="anthropic", model=None, max_tokens=100):
    if api not in API_CONFIGS:
        raise ValueError(f"Invalid API: {api}")
        
    print(f"Using {api.upper()} API for completion")
    api_config = API_CONFIGS[api]
    model = model or api_config["default_model"]
    
    try:
        time.sleep(0.1)
        
        json_payload = {
            "model": model,
            "prompt": prompt if api == "ollama" else f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens": max_tokens
        }
        
        if api == "groq":
            json_payload["messages"] = [{"role": "user", "content": prompt}]
        elif api == "anthropic":
            json_payload["max_tokens_to_sample"] = max_tokens
            json_payload["stop_sequences"] = ["\n\nHuman:"]
            del json_payload["max_tokens"]
        elif api == "ollama":
            json_payload["stream"] = False
        
        response = requests.post(
            api_config["url"],
            headers=api_config["headers"](),
            json=json_payload
        )
        response.raise_for_status()
        
        if api == "anthropic": return response.json().get('completion', '')
        elif api == "groq": return response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        elif api == "ollama": return response.json().get('response', '')
        
    except requests.exceptions.RequestException as e:
        logger.error(f"{api.title()} API request error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error with {api.title()} API: {e}")
    
    return None

def matched_service(request_description="", provider_capabilities=""):
    prompt = f"""
Service request: {request_description}
Provider capabilities: {provider_capabilities}
Based only on the capabilities listed, determine if the provider can fulfill the service request.
Answer with only 'True' if there's a match, or 'False' if there isn't.
"""
    
    for api in ["ollama", "groq", "anthropic"]:
        if response := generate_completion(prompt, api=api):
            try:
                print("prompt: %s" % prompt)
                print("response: %s" % response)
                return response.strip().lower() == 'true'
            except Exception as e:
                logger.error(f"Failed to parse {api} response: {e}")
                continue
                
    logger.info("All LLM attempts failed, falling back to keyword matching")
    return keyword_match(request_description, provider_capabilities.split(' and '))

if __name__ == "__main__":
    test_cases = [
        ("Need expert Python developer for debugging", "python and debugging and testing"),
        ("Looking for dog walker", "pet care and dog walking"),
        ("Need programming help with Python", "javascript and html and css")
    ]
    
    for desc, caps in test_cases:
        result = matched_service(desc, caps)
        print(f"\nRequest: {desc}")
        print(f"Capabilities: {caps}")
        print(f"Match: {result}")
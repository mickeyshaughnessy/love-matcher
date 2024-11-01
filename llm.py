import requests, json, config, time, re, logging
from collections import Counter

"""
🤔 LLM Service Module
- Simple ALL_CAPS config format
- Streamlined API handling
- Fallback chain for providers
<Flow>
1. Try each provider in sequence
2. Use consistent response handling
3. Simple error management
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def completion(prompt, api="anthropic", model=None, max_tokens=100):
    print(f"Using {api.upper()} API for completion")
    
    try:
        time.sleep(0.1)
        
        if api == "anthropic":
            url = config.ANTHROPIC_API_URL
            headers = {
                "Content-Type": "application/json",
                "x-api-key": config.ANTHROPIC_API_KEY,
                "anthropic-version": "2024-03-01"
            }
            model = model or config.ANTHROPIC_MODEL
            json_payload = {
                "model": model,
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": max_tokens,
                "stop_sequences": ["\n\nHuman:"]
            }
            
        elif api == "groq":
            url = config.GROQ_API_URL
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.GROQ_API_KEY}"
            }
            model = model or config.GROQ_MODEL
            json_payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            
        elif api == "ollama":
            url = config.OLLAMA_API_URL
            headers = {"Content-Type": "application/json"}
            model = model or config.OLLAMA_MODEL
            json_payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "max_tokens": max_tokens
            }
            
        else:
            raise ValueError(f"Invalid API: {api}")

        response = requests.post(url, headers=headers, json=json_payload)
        response.raise_for_status()
        
        if api == "anthropic":
            return response.json().get('completion', '')
        elif api == "groq":
            return response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        elif api == "ollama":
            return response.json().get('response', '')
            
    except requests.exceptions.RequestException as e:
        logger.error(f"{api.title()} API request error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error with {api.title()} API: {e}")
    
    return None
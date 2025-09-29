import requests, json, logging, time, re
from typing import Optional, Dict, Any

"""
🤔 Multi-Provider LLM Interface
- Ollama as primary, others as fallback
- Configurable provider chain
- Unified response handling
<Flow>
1. Try Ollama first
2. Fall back to other providers
3. Extract meaningful scores
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Provider configs
OLLAMA_URL = "http://localhost:11434/api/generate"
ANTHROPIC_URL = "https://api.anthropic.com/v1/complete"
GROQ_URL = "https://api.groq.com/v1/chat/completions"

# API keys should be in config.py or env vars
try:
    from config import ANTHROPIC_API_KEY, GROQ_API_KEY
except ImportError:
    ANTHROPIC_API_KEY = ""
    GROQ_API_KEY = ""

# Default settings
DEFAULT_PROVIDER = "ollama"
DEFAULT_MODELS = {
    "ollama": "mistral",
    "anthropic": "claude-3-sonnet-20240229",
    "groq": "mixtral-8x7b-32768"
}
MAX_RETRIES = 2
RETRY_DELAY = 1

def get_provider_config(provider: str, model: Optional[str] = None) -> Dict[str, Any]:
    configs = {
        "ollama": {
            "url": OLLAMA_URL,
            "headers": {"Content-Type": "application/json"},
            "model": model or DEFAULT_MODELS["ollama"],
            "format": lambda p, m, t: {
                "model": m,
                "prompt": p,
                "stream": False,
                "max_tokens": t
            },
            "extract": lambda r: r.json().get("response", "")
        },
        "anthropic": {
            "url": ANTHROPIC_URL,
            "headers": {
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2024-03-01"
            },
            "model": model or DEFAULT_MODELS["anthropic"],
            "format": lambda p, m, t: {
                "model": m,
                "prompt": f"\n\nHuman: {p}\n\nAssistant:",
                "max_tokens_to_sample": t,
                "stop_sequences": ["\n\nHuman:"]
            },
            "extract": lambda r: r.json().get("completion", "")
        },
        "groq": {
            "url": GROQ_URL,
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },
            "model": model or DEFAULT_MODELS["groq"],
            "format": lambda p, m, t: {
                "model": m,
                "messages": [{"role": "user", "content": p}],
                "max_tokens": t
            },
            "extract": lambda r: r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        }
    }
    return configs.get(provider, configs["ollama"])

def completion(
    prompt: str,
    provider: str = DEFAULT_PROVIDER,
    model: Optional[str] = None,
    max_tokens: int = 1000
) -> str:
    providers = [provider] if provider != DEFAULT_PROVIDER else [DEFAULT_PROVIDER, "anthropic", "groq"]
    
    for prov in providers:
        config = get_provider_config(prov, model)
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    config["url"],
                    headers=config["headers"],
                    json=config["format"](prompt, config["model"], max_tokens)
                )
                response.raise_for_status()
                return config["extract"](response)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"{prov.title()} request failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                    
            except Exception as e:
                logger.error(f"Unexpected error with {prov.title()}: {e}")
                
        # Try next provider if all attempts failed
        continue
        
    return ""  # All providers failed

def extract_score(text: str) -> float:
    try:
        # Look for percentage or score patterns
        patterns = [
            r"(\d+)%",
            r"Score:\s*(\d+)",
            r"score:\s*(\d+)",
            r"rating:\s*(\d+)",
            r"[\[\(](\d+)[\]\)]"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                score = int(matches[0])
                return min(100, max(0, score))
                
        # Keyword-based scoring fallback
        text = text.lower()
        if any(word in text for word in ["excellent", "perfect", "ideal"]):
            return 90.0
        elif any(word in text for word in ["good", "strong", "high"]):
            return 75.0
        elif any(word in text for word in ["average", "moderate", "medium"]):
            return 50.0
        elif any(word in text for word in ["poor", "low", "weak"]):
            return 25.0
            
    except Exception as e:
        logger.error(f"Score extraction failed: {e}")
        
    return 50.0  # Default middle score
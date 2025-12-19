import requests, json
from typing import Optional, List, Dict, Any

from utils import add_log
from model import call_llm_api

# Cache for API responses to avoid repeated calls
_api_cache = {
    'knowledge': None,
    'advancements': None,
    'guides': None
}

def get_api_data(endpoint: str) -> Dict:
    """Fetch and cache data from API endpoints"""
    global _api_cache
    
    if _api_cache.get(endpoint) is not None:
        return _api_cache[endpoint]
    
    try:
        url = f'https://minecraft-ai-embodied-benchmark.megrez.plus/api/{endpoint}'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        _api_cache[endpoint] = data
        return data
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return {}

def prompt_enhancer(agent, provider, model, prompt, context, json_keys=None, examples=None, images=None, max_tokens=4096, temperature=0.9):
    """
    Enhanced prompt enhancer with actions, advancements, and guides
    """
    
    knowledge = get_api_data('knowledge')
    advancements_data = get_api_data('advancements')
    guides_data = get_api_data('guides')

    enhanced_prompt = prompt 
    return enhanced_prompt

def call_llm_api_with_enhancer(agent, provider, model, prompt, context, json_keys=None, examples=None, images=None, max_tokens=4096, temperature=0.9):
    """
    Call LLM API with enhanced prompt including actions, advancements, and guides
    """
    enhanced_prompt = prompt_enhancer(agent, provider, model, prompt, context, json_keys, examples, images, max_tokens, temperature)

    if context is not None and len(context) > 0:
        enhanced_prompt += "\n\n# Additional Context"
        for (title, content) in context :
            enhanced_prompt += f"{enhanced_prompt}\n##{title}\n{content}"

    add_log(title = agent.pack_message("Enhanced prompt."), content = enhanced_prompt, print = False)
    return call_llm_api(provider, model, enhanced_prompt, json_keys, examples, images, max_tokens, temperature)

# Utility function to clear cache if needed
def clear_api_cache():
    """Clear the API cache to force fresh data fetch"""
    global _api_cache
    _api_cache = {
        'knowledge': None,
        'advancements': None,
        'guides': None
    }
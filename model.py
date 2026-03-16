
import os, json, inspect, re, base64
import json5, requests

from utils import *

# Cache for benchmark API responses
_benchmark_cache = {}

def encode_file_to_base64(path):
    with open(path, 'rb') as file :
        return base64.b64encode(file.read()).decode('utf-8')

def decode_and_save_base64(base64_str, save_path):
    with open(save_path, "wb") as file :
        file.write(base64.b64decode(base64_str))

def split_content_and_code(text) :
    content, code = text, ""
    mark_pos = [m.start() for m in re.finditer("```", text)]
    for i in range(0, len(mark_pos) - 1) :
        data_start = mark_pos[i]
        data_end = mark_pos[i + 1]
        try :
            code = text[(data_start + 3) : data_end].replace("\n", "").replace("\r", "").strip()
            content = text[:data_start].strip() + "\n" + text[min(len(text), data_end + 3):].strip()
            for tag in ["html", "css", "python", "javascript", "json", "xml"] :
                if code.find(tag) == 0 :
                    code = code[len(tag):].strip()
                    break
        except Exception as e :
            content, code = text,  ""
        if len(code) > 0 :
            break
    return content, code

def split_content_and_json(text) :
    content, data = text, {}
    mark_pos = [m.start() for m in re.finditer("```", text)]
    for i in range(0, len(mark_pos) - 1) :
        data_start = mark_pos[i]
        data_end = mark_pos[i + 1]
        try :
            json_text = text[(data_start + 3) : data_end].replace("\n", "").replace("\r", "").strip()
            start = json_text.find("{")
            list_start = json_text.find("[")
            if list_start >= 0 and list_start < start :
                start = list_start
            if start >= 0 :
                json_text = json_text[start:]
            for tag in ["html", "css", "python", "javascript", "json", "xml"] :
                if json_text.find(tag) == 0 :
                    json_text = json_text[len(tag):].strip()
                    break
            data = json5.loads(json_text)
            content = text[:data_start].strip() + "\n" + text[min(len(text), data_end + 3):].strip()
        except Exception as e :
            content, data = text, {}
        if type(data) == dict and len(data) > 0 :
            break
    return content, data

def get_keys_info_list(keys) :
    keys_info = []
    if keys is not None :
        for key, value in keys.items() :
            keys_info.append("* %s" % value.get("description"))
            lst = get_keys_info_list(value.get("keys", {}))
            if len(lst) > 0 :
                keys_info[-1] += " It is a JSON dictionary containing the following keys:"
                keys_info += list(map(lambda l : "\t" + l, lst))
    return keys_info

def get_keys_info(keys) :
    return "\n".join(get_keys_info_list(keys))

def extract_data(data, keys) :
    d = {}
    for key, value in keys.items() :
        d_value = data.get(key, None)
        if d_value is not None :
            ks = value.get("keys", None)
            if ks is not None :
                if isinstance(d_value, dict) :
                    d[key] = extract_data(d_value, ks)
            else :
                d[key] = d_value
    return d

def resolve_api_key(key) :
    """Resolve API key, supporting 'env:VAR_NAME' format.

    Args:
        key: API key string, may start with 'env:' to reference environment variable

    Returns:
        Resolved API key string
    """
    if key and isinstance(key, str) and key.startswith("env:"):
        env_var = key[4:]
        return os.environ.get(env_var, "")
    return key or ""

def call_openai_compatible_api(base_url, api_key, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    """Generic caller for OpenAI-compatible APIs.

    This function calls any API that follows the OpenAI chat completions format.
    Handles special endpoints like Pollinations (/openai) and standard /chat/completions.

    Args:
        base_url: Base URL for the API (e.g., "https://api.openai.com/v1")
        api_key: API key for authentication (can be empty for free APIs like Pollinations/Ollama)
        model: Model identifier
        prompt: The prompt to send
        images: Optional list of image paths to include
        max_tokens: Maximum tokens in response
        temperature: Temperature for response generation

    Returns:
        dict with 'message', 'status', 'error' keys
    """
    result = {"message" : None, "status" : 0, "error" : None}

    # Construct URL - handle special endpoints
    url = base_url.rstrip("/")

    # Pollinations uses /openai endpoint directly (no /chat/completions suffix)
    # Standard OpenAI-compatible APIs use /chat/completions
    if not url.endswith("/openai"):
        url = url + "/chat/completions"

    payload = {
        "model" : model,
        "messages" : [{"role" : "user", "content" : prompt}],
        "max_tokens" : max_tokens,
        "temperature" : temperature,
        "stream" : False,
    }

    if images is not None :
        payload["images"] = []
        for image in images :
            payload["images"].append(encode_file_to_base64(image))

    headers = {
        "Content-Type" : "application/json",
    }
    if api_key and len(api_key.strip()) > 0:
        headers["Authorization"] = "Bearer %s" % api_key

    try :
        response = requests.post(
            url,
            headers = headers,
            json = payload,
        )

        add_log(title = "Response of OpenAI-compatible API.", content = str(response), label = "llm", print = False)

        if response.status_code == 200 :
            response_data = response.json()
            if "choices" in response_data.keys() :
                if response_data["choices"][0]["message"].get("content", None) is not None :
                    result["message"] = response_data["choices"][0]["message"]["content"]
                elif response_data["choices"][0]["message"].get("reasoning_content", None) is not None :
                    result["message"] = response_data["choices"][0]["message"]["reasoning_content"]
            if result["message"] is None :
                result["status"] = 1
                result["error"] = "[%s] Invalid response data: %s" % (
                    inspect.currentframe().f_code.co_name,
                    response_data,
                )
        else :
            result["status"] = 1
            result["error"] = "[%s] Response error: %s - %s" % (
                inspect.currentframe().f_code.co_name,
                response.status_code,
                response.text[:500] if response.text else "No response text",
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result

def call_llm_api(config, prompt, json_keys = None, examples = None, images = None, max_tokens = 4096, temperature = 0.9) :
    """Call LLM API with configuration dict.

    Args:
        config: Dict with 'base_url', 'api_key', 'model' keys
                - base_url: API endpoint (e.g., "https://api.openai.com/v1")
                - api_key: API key or "env:VAR_NAME" for environment variable
                - model: Model identifier (e.g., "gpt-4o")
        prompt: The prompt to send
        json_keys: Optional JSON schema for structured output
        examples: Optional list of example outputs
        images: Optional list of image paths
        max_tokens: Maximum tokens in response
        temperature: Temperature for generation

    Returns:
        dict with 'message', 'status', 'error', 'data' keys
    """
    keys_info = get_keys_info(json_keys)
    if len(keys_info.strip()) > 0 :
        prompt += '''
\n## Output Format
The result should be formatted in **JSON** dictionary and enclosed in **triple backticks (` ``` ` )**  without labels like 'json', 'css', or 'data'.
- **Do not** generate redundant content other than the result in JSON format.
- **Do not** use triple backticks anywhere else in your answer.
- The JSON must include the following keys and values accordingly :
%s
''' % keys_info

    examples_info = ""
    for i, example in enumerate(examples or []) :
        examples_info += '''
### Example %d
%s

''' % (i, example)
    if len(examples_info.strip()) > 0 :
        prompt += '''
\n## Output Examples
%s
''' % examples_info

    result = {"message" : None, "status" : 0, "error" : None}

    # Extract config values with defaults
    base_url = config.get("base_url", "https://api.openai.com/v1")
    api_key = resolve_api_key(config.get("api_key", ""))
    model = config.get("model", "gpt-4o")

    result = call_openai_compatible_api(base_url, api_key, model, prompt, images, max_tokens, temperature)

    if result["status"] < 1 and result["message"] is not None and json_keys is not None :
        _, data = split_content_and_json(result["message"])
        result["data"] = extract_data(data, json_keys)
    else :
        result["data"] = None
    return result


# =============================================================================
# Benchmark API Enhancer Functions
# =============================================================================

def get_benchmark_data(base_url, endpoint):
    """Fetch and cache data from benchmark API.

    Args:
        base_url: Base URL for the benchmark API (e.g., "http://localhost:5999")
        endpoint: API endpoint (e.g., "guides", "knowledge", "actions")

    Returns:
        dict: The API response data, or empty dict on error
    """
    global _benchmark_cache

    cache_key = f"{base_url}/{endpoint}"
    if cache_key in _benchmark_cache:
        return _benchmark_cache[cache_key]

    try:
        url = f"{base_url.rstrip('/')}/api/{endpoint}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        _benchmark_cache[cache_key] = data
        return data
    except Exception as e:
        add_log(
            title="Benchmark API Error",
            content=f"Failed to fetch {endpoint}: {e}",
            label="warning",
            print=False
        )
        return {}


def search_benchmark(base_url, query, endpoint="all"):
    """Search benchmark API for relevant content.

    Args:
        base_url: Base URL for the benchmark API
        query: Search query string
        endpoint: What to search - "guides", "knowledge", "actions", or "all"

    Returns:
        dict: Search results with filtered content (no positions/coordinates)
    """
    try:
        url = f"{base_url.rstrip('/')}/api/search/{endpoint}"
        response = requests.get(url, params={"q": query}, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Filter out specific positions/coordinates from results
        return _filter_positions(data)
    except Exception as e:
        add_log(
            title="Benchmark Search Error",
            content=f"Search failed for '{query}': {e}",
            label="warning",
            print=False
        )
        return {}


def _filter_positions(data):
    """Recursively filter out position coordinates from data.

    Removes:
    - action_parameters.position with x, y, z coordinates
    - Specific coordinates in text descriptions

    Args:
        data: Data structure to filter (dict, list, or primitive)

    Returns:
        Filtered data structure
    """
    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            # Skip position-related keys
            if key in ["position", "pos", "coordinates", "coords"]:
                continue
            # Skip action_parameters if it only contains position
            if key == "action_parameters":
                if isinstance(value, dict) and set(value.keys()) <= {"position", "pos"}:
                    continue
            filtered[key] = _filter_positions(value)
        return filtered
    elif isinstance(data, list):
        return [_filter_positions(item) for item in data]
    elif isinstance(data, str):
        # Remove coordinate patterns like "x: 100, y: 64, z: -200"
        import re
        # Pattern to match coordinate specifications
        coord_pattern = r'\b(?:x:\s*-?\d+\.?\d*,\s*y:\s*-?\d+\.?\d*,\s*z:\s*-?\d+\.?\d*|(?:at\s+)?\(?\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\)?)\b'
        return re.sub(coord_pattern, '[position removed]', data, flags=re.IGNORECASE)
    else:
        return data


def _extract_keywords(text):
    """Extract meaningful keywords from text for search.

    Args:
        text: Text to extract keywords from

    Returns:
        str: Space-separated keywords for search
    """
    if not text:
        return ""

    # Common Minecraft-related keywords to prioritize
    minecraft_keywords = [
        "mine", "dig", "collect", "craft", "build", "explore", "hunt",
        "farm", "fish", "cook", "smelt", "enchant", "trade", "attack",
        "defend", "follow", "lead", "ride", "tame", "breed",
        "wood", "stone", "iron", "gold", "diamond", "coal", "cobblestone",
        "oak", "birch", "spruce", "jungle", "acacia", "dark_oak",
        "creeper", "zombie", "skeleton", "spider", "enderman", "pig", "cow", "sheep", "chicken",
        "sword", "pickaxe", "axe", "shovel", "hoe", "bow", "arrow", "armor",
        "food", "bread", "meat", "apple", "wheat", "carrot", "potato",
        "house", "shelter", "base", "farm", "mine", "cave", "village",
        "nether", "end", "portal", "beacon", "anvil", "furnace", "chest",
        "bed", "torch", "ladder", "door", "fence", "wall",
        "swim", "climb", "jump", "walk", "run", "fly",
        "inventory", "health", "hunger", "experience", "level",
        "day", "night", "weather", "rain", "thunder",
        "biome", "desert", "jungle", "taiga", "savanna", "swamp", "ocean", "mountain"
    ]

    # Convert to lowercase and split
    words = text.lower().split()

    # Extract meaningful words (length > 2, not common stop words)
    stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "has", "have", "been", "will", "your", "from", "they", "would", "there", "their", "what", "about", "which", "when", "make", "like", "into", "year", "good", "some", "could", "them", "than", "then", "only", "come", "over", "such", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "need", "should", "very", "where", "each", "just", "know", "take", "person", "into", "year", "good", "some", "could", "them", "than", "other", "then", "now", "look", "only", "come", "its", "over", "think", "also", "such", "being", "back", "still", "through", "when", "may", "before", "does", "did", "done", "must", "made", "might", "must", "shall"}

    keywords = []
    for word in words:
        # Clean the word
        cleaned = ''.join(c for c in word if c.isalnum() or c == '_')
        if len(cleaned) > 2 and cleaned not in stop_words:
            keywords.append(cleaned)

    # Prioritize Minecraft keywords that appear in the text
    prioritized = []
    for kw in minecraft_keywords:
        if kw in text.lower():
            prioritized.append(kw)

    # Combine prioritized keywords with extracted ones
    all_keywords = prioritized + keywords[:10]  # Limit to avoid too long queries

    return " ".join(all_keywords[:15])  # Further limit for API query


def enhance_prompt(prompt, benchmark_url, task_description, agent=None):
    """Enhance prompt with relevant guides and knowledge from benchmark API.

    Args:
        prompt: The original prompt to enhance
        benchmark_url: Base URL for the benchmark API
        task_description: Description of the current task/goal for keyword extraction
        agent: Optional agent instance for logging

    Returns:
        str: Enhanced prompt with relevant context added
    """
    if not benchmark_url:
        return prompt

    # Extract keywords from task description
    keywords = _extract_keywords(task_description)
    if not keywords:
        return prompt

    enhancement = "\n\n# Relevant Guides (Reference Only)"
    has_content = False

    # Search for relevant guides
    try:
        guides_result = search_benchmark(benchmark_url, keywords, "guides")
        if guides_result and "results" in guides_result:
            for item in guides_result["results"][:3]:  # Limit to top 3 results
                if isinstance(item, dict):
                    title = item.get("title", item.get("name", "Guide"))
                    content = item.get("content", item.get("description", ""))
                    steps = item.get("steps", [])

                    enhancement += f"\n## {title}"
                    if content:
                        enhancement += f"\n{content}"
                    if steps:
                        for i, step in enumerate(steps[:5]):  # Limit steps
                            if isinstance(step, dict):
                                step_desc = step.get("description", step.get("step", str(step)))
                            else:
                                step_desc = str(step)
                            enhancement += f"\n- Step {i+1}: {step_desc}"
                    has_content = True
    except Exception as e:
        if agent:
            add_log(
                title=agent.pack_message("Guide search failed."),
                content=str(e),
                label="warning",
                print=False
            )

    # Search for relevant knowledge
    try:
        knowledge_result = search_benchmark(benchmark_url, keywords, "knowledge")
        if knowledge_result and "results" in knowledge_result:
            enhancement += "\n\n# Relevant Knowledge (Reference Only)"
            for item in knowledge_result["results"][:3]:  # Limit to top 3 results
                if isinstance(item, dict):
                    category = item.get("category", item.get("name", "Knowledge"))
                    description = item.get("description", "")
                    actions = item.get("actions", [])

                    enhancement += f"\n## {category}"
                    if description:
                        enhancement += f"\n{description}"
                    if actions:
                        enhancement += f"\nRelated actions: {', '.join(actions[:5])}"
                    has_content = True
    except Exception as e:
        if agent:
            add_log(
                title=agent.pack_message("Knowledge search failed."),
                content=str(e),
                label="warning",
                print=False
            )

    # Only return enhanced prompt if we found relevant content
    if has_content:
        enhanced = prompt + enhancement
        if agent:
            add_log(
                title=agent.pack_message("Prompt enhanced with benchmark data."),
                content=f"Keywords: {keywords}",
                label="action",
                print=False
            )
        return enhanced

    return prompt


def call_llm_api_with_enhancer(config, prompt, settings, context=None, json_keys=None, examples=None, images=None, max_tokens=4096, temperature=0.9, agent=None):
    """Call LLM API with optional enhancement from benchmark API.

    Enhancement is only applied when:
    1. settings["use_enhancer"] is True
    2. benchmark_api_url is configured

    Args:
        config: LLM configuration dict with 'base_url', 'api_key', 'model' keys
        prompt: The prompt to send
        settings: Global settings dict (must contain use_enhancer and benchmark_api_url)
        context: Optional list of (title, content) tuples for additional context
        json_keys: Optional JSON schema for structured output
        examples: Optional list of example outputs
        images: Optional list of image paths
        max_tokens: Maximum tokens in response
        temperature: Temperature for generation
        agent: Optional agent instance for logging

    Returns:
        dict with 'message', 'status', 'error', 'data' keys
    """
    enhanced_prompt = prompt

    # Check if enhancer is enabled
    use_enhancer = settings.get("use_enhancer", False) if settings else False
    benchmark_url = settings.get("benchmark_api_url", "http://localhost:5999") if settings else None

    if use_enhancer and benchmark_url:
        # Extract task description from context if available
        task_description = ""
        if context:
            for title, content in context:
                if title in ["Active Goal", "Current Status", "Latest Messages"]:
                    task_description += f" {content}"

        # Enhance the prompt
        enhanced_prompt = enhance_prompt(prompt, benchmark_url, task_description, agent)

    # Add context sections to prompt
    if context is not None and len(context) > 0:
        enhanced_prompt += "\n\n# Additional Context"
        for (title, content) in context:
            enhanced_prompt += f"\n## {title}\n{content}"

    # Log the enhanced prompt
    if agent and use_enhancer:
        add_log(
            title=agent.pack_message("Enhanced prompt."),
            content=enhanced_prompt,
            label="llm",
            print=False
        )

    return call_llm_api(config, enhanced_prompt, json_keys, examples, images, max_tokens, temperature)


def clear_benchmark_cache():
    """Clear the benchmark API cache to force fresh data fetch."""
    global _benchmark_cache
    _benchmark_cache = {}

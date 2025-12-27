
import os, json, inspect, re, base64
import json5, requests

from utils import *

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

def get_providers() :
    providers = read_json("model.json") 
    return providers

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

def call_llm_api(provider, model, prompt, json_keys = None, examples = None, images = None, max_tokens = 4096, temperature = 0.9) :
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
    for i, example in enumerate(examples) : 
        examples_info += '''
### Example %d 
%s

''' % (i, example)
    if len(examples_info.strip()) > 0 : 
        prompt += '''
\n## Output Examples
%s
''' % examples_info 

    providers = get_providers()
    result = {"message" : None, "status" : 0, "error" : None}
    if provider == "Ollama" :
        url = providers["Ollama"]["url"]
        result = call_ollama_api(url, model, prompt, images, max_tokens, temperature)
    elif provider == "Pollinations" :
        url = providers["Pollinations"]["url"]
        result = call_pollinations_api(url, model, prompt, images, max_tokens, temperature)
    elif provider in ["OpenAI", "Anthropic", "Google", "DeepSeek", "Doubao", "Qwen", "OpenRouter", "Airforce"] :
        url = providers[provider]["url"]
        api_key = providers[provider]["api_key"]
        if len(api_key.strip()) < 1 : 
            api_key = os.environ.get("%s_API_KEY" % provider.upper())
        if provider in ["DeepSeek", "Doubao", "Qwen", "OpenRouter", ] :
            result = call_open_api(url, api_key, model, prompt, images, max_tokens, temperature)
        elif provider == "OpenAI" : 
            result = call_openai_api(url, api_key, model, prompt, images, max_tokens, temperature)
        elif provider == "Anthropic" : 
            result = call_anthropic_api(url, api_key, model, prompt, images, max_tokens, temperature)
        elif provider == "Google" : 
            result = call_gemini_api(url, api_key, model, prompt, images, max_tokens, temperature)
    else :
        result["status"] = 1
        result["error"] = "[%s] Invalid provider: %s" % (inspect.currentframe().f_code.co_name, provider)

    if result["status"] < 1 and result["message"] is not None and json_keys is not None :
        _, data = split_content_and_json(result["message"])
        result["data"] = extract_data(data, json_keys)
    else :
        result["data"] = None
    return result

def call_ollama_api(url, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : None, "status" : 0, "error" : None}
    payload = {"model" : model, "prompt" : prompt, "max_tokens" : max_tokens, "temperature" : temperature, "stream" : False}
    if images is not None :
        payload["images"] = []
        for image in images :
            payload["images"].append(encode_file_to_base64(image))
    if len(url.strip()) > 0 :
        try :
            response = requests.post(
                url,
                headers = {"Content-Type" : "application/json"},
                json = payload,
            )

            add_log(title = "Response of Ollama API.", content = str(response), label = "llm", print = False)

            if response.status_code == 200 :
                response_data = response.json()
                result["message"] = response_data.get("response", "")
            else :
                result["status"] = 3
                result["error"] = "[%s] Reponse error: %s" % (
                    inspect.currentframe().f_code.co_name,
                    response.status_code,
                )
        except Exception as e :
            result["status"] = 2
            result["error"] = str(e)
    else :
        result["status"] = 1
        result["error"] = "[%s] Invalid url." % inspect.currentframe().f_code.co_name
    return result

def call_pollinations_api(url, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : None, "status" : 0, "error" : None}
    payload = {
        "messages" : [{"role" : "user", "content" : prompt}], 
        "model" : model, 
        "max_tokens" : max_tokens, 
        "temperature" : temperature,
        "stream" : False,
        "private" : True,
    }

    if images is not None :
        payload["images"] = []
        for image in images :
            payload["images"].append(encode_file_to_base64(image))
    try :
        response = requests.post(
            url,
            headers = {
                "Content-Type" : "application/json",
                "Accept" : "application/json, text/plain, */*",
            },
            json = payload,
        )

        add_log(title = "Response of Pollinations API.", content = str(response), label = "llm", print = False)

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
            result["error"] = "[%s] Reponse error: %s" % (
                inspect.currentframe().f_code.co_name,
                response.status_code,
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result

def call_free_api(url, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : None, "status" : 0, "error" : None}
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
    try :
        response = requests.post(
            url,
            headers = {
                "Content-Type" : "application/json",
            },
            json = payload,
        )

        add_log(title = "Response of free API.", content = str(response), label = "llm", print = False)

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
            result["error"] = "[%s] Reponse error: %s" % (
                inspect.currentframe().f_code.co_name,
                response.status_code,
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result


def call_open_api(url, api_key, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : None, "status" : 0, "error" : None}
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
    try :
        response = requests.post(
            url,
            headers = {
                "Authorization": "Bearer %s" % api_key,
                "Content-Type" : "application/json",
            },
            json = payload,
        )

        add_log(title = "Response of open API.", content = str(response), label = "llm", print = False)

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
            result["error"] = "[%s] Reponse error: %s" % (
                inspect.currentframe().f_code.co_name,
                response.status_code,
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result

def call_openai_api(url, api_key, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : None, "status" : 0, "error" : None}
    payload = {
        "model" : model, 
        "input" : prompt,  
        "max_output_tokens" : max_tokens, 
        "temperature" : temperature,
        "stream" : False,
    }
    if images is not None :
        payload["images"] = []
        for image in images :
            payload["images"].append(encode_file_to_base64(image))
    try :
        response = requests.post(
            url,
            headers = {
                "Authorization": "Bearer %s" % api_key,
                "Content-Type" : "application/json",
            },
            json = payload,
        )

        add_log(title = "Response of OpenAI api.", content = str(response), label = "llm", print = False)

        if response.status_code == 200 :
            response_data = response.json()
            if "output" in response_data.keys() : 
                result["message"] = response_data["output"][0]["content"][0]["text"]
            else : 
                result["status"] = 1
                result["error"] = "[%s] Invalid response data: %s" % (
                    inspect.currentframe().f_code.co_name,
                    response_data,
                )
        else :
            result["status"] = 1
            result["error"] = "[%s] Reponse error: %s" % (
                inspect.currentframe().f_code.co_name,
                response.status_code,
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result

def call_anthropic_api(url, token, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : None, "status" : 0, "error" : None}
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
    try :
        response = requests.post(
            url,
            headers = {
                "x-api-key": token,
                "anthropic-version": "2023-06-01",
                "Content-Type" : "application/json",
            },
            json = payload,
        )

        add_log(title = "Response of Anthropic API.", content = str(response), label = "llm", print = False)

        if response.status_code == 200 :
            response_data = response.json()
            if "content" in response_data.keys() : 
                result["message"] = response_data["content"][0]["text"]
            else : 
                result["status"] = 1
                result["error"] = "[%s] Invalid response data: %s" % (
                    inspect.currentframe().f_code.co_name,
                    response_data,
                )
        else :
            result["status"] = 1
            result["error"] = "[%s] Reponse error: %s" % (
                inspect.currentframe().f_code.co_name,
                response.status_code,
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result

def call_gemini_api(url, api_key, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : None, "status" : 0, "error" : None}
    url = "%s/models/%s:generateContent?key=%s" % (url, model, api_key)
    payload = {
        "contents" : {
            "parts" : [{"text" : prompt}], 
        },  
        "generationConfig": {
            "maxOupputTokens" : max_tokens, 
            "temperature" : temperature,
        },
    }
    if images is not None :
        payload["images"] = []
        for image in images :
            payload["contents"]["parts"][0]["images"].append(encode_file_to_base64(image))
    try :
        response = requests.post(
            url,
            headers = {
                "Content-Type" : "application/json",
            },
            json = payload,
        )

        add_log(title = "Response of Gemini API.", content = str(response), label = "llm", print = False)

        if response.status_code == 200 :
            response_data = response.json()
            if "candidates" in response_data.keys() : 
                result["message"] = response_data["candidates"][0]["content"]["parts"][0]["text"]
            else : 
                result["status"] = 1
                result["error"] = "[%s] Invalid response data: %s" % (
                    inspect.currentframe().f_code.co_name,
                    response_data,
                )
        else :
            result["status"] = 1
            result["error"] = "[%s] Reponse error: %s" % (
                inspect.currentframe().f_code.co_name,
                response.status_code,
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result

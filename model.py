
import os, json, inspect, re, base64
import json5
import urllib.request

from utils import *

def encode_file_to_base64(path):
    with open(path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')

def decode_and_save_base64(base64_str, save_path):
    with open(save_path, "wb") as file:
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
    {
        "Ollama": {
            "base_url": "http://127.0.0.1:11434",
            "models": [
                "llama3.1",
                "llama3.2",
                "llama3.2-vision"
                "gemma3:4b",
            ]
        },
        "Qwen": {
            "token": "sk-973f7ab04b274721a906463031eff7c2",
            "url" : "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions/",
            "models": [
                "qwen-turbo",
                "qwen-plus",
                "qwen-long",
                "qwen-max",
                "qwen-max-0125"
                "qwen-max-latest",
                "deepseek-v3",
                "deepseek-r1",
            ]
        },
        "OpenRouter": {
            "token": "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",
            "url" : "https://openrouter.ai/api/v1/chat/completions",
            "models": [
                "meta-llama/llama-3.1-8b-instruct:free",
                "meta-llama/llama-3.3-70b-instruct:free",
                "meta-llama/llama-3.2-11b-vision-instruct:free",
                "deepseek/deepseek-chat-v3-0324:free",
                "deepseek/deepseek-r1:free",
                "deepseek/deepseek-r1-zero:free",
                "openai/gpt-4",
                "openai/gpt-4-32k",
                "openai/gpt-4-turbo",
                "openai/gpt-4o-mini",
                "openai/gpt-4o",
                "openai/o1-pro",
                "openai/gpt-4.5-preview",
                "anthropic/claude-3-opus",
                "anthropic/claude-3.5-sonnet-20240620",
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3.5-haiku-20241022",
                "anthropic/claude-3.7-sonnet",
            ]
        },
        "Doubao" : {
            "token" : "d2f59aad-7098-4728-aeb0-8762ae23abba",
            "url" : "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            "models" : [
                "doubao-1-5-pro-32k-250115",
                "doubao-1-5-lite-32k-250115",
                "doubao-pro-256k-241115",
                "doubao-1-5-vision-pro-32k-250115",
                "deepseek-v3-250324",
                "deepseek-r1-250120"
            ] 
        }
    }
    return providers

def call_llm_api(provider, model, prompt, images = None) :
    providers = get_providers()
    result = {"message" : None, "status" : 0, "error" : None}
    if provider == "Ollama" :
        url = providers["Ollama"]["base_url"]
        result = call_ollama_api(url, model, prompt, images)
    elif provider in ["Doubao", "Qwen", "OpenRouter", ] :
        url = providers[provider]["url"]
        token = providers[provider]["token"]
        result = call_open_api(url, token, model, prompt, images)
    else :
        result["status"] = 1
        result["error"] = "[%s] Invalid provider: %s" % (inspect.currentframe().f_code.co_name, provider)
    return result

def call_ollama_api(url, model, prompt, images = None) :
    result = {"message" : "", "status" : 0, "error" : None}
    data = {"model" : model, "prompt" : prompt, "stream" : False}
    if images is not None and model in ["llama3.2-vision", "gemma3:4b"] :
        data["images"] = []
        for image in images :
            data["images"].append(encode_file_to_base64(image))
    if len(url.strip()) > 0 :
        url = os.path.join(url, "api/generate")
        try :
            request = urllib.request.Request(
                url,
                headers = {"Content-Type" : "application/json"},
                data = json.dumps(data).encode("utf-8"),
            )
            response = urllib.request.urlopen(request)
            if response.getcode() == 200 :
                response_data = json.loads(response.read().decode('utf-8'))
                result["message"] = response_data.get("response", "")
            else :
                result["status"] = 3
                result["error"] = "[%s] Reponse error: %s" % (
                    inspect.currentframe().f_code.co_name,
                    response.getcode(),
                )
        except Exception as e :
            result["status"] = 2
            result["error"] = str(e)
    else :
        result["status"] = 1
        result["error"] = "[%s] Invalid url." % inspect.currentframe().f_code.co_name
    return result

def call_open_api(url, token, model, prompt, images = None) :
    result = {"response" : "", "status" : 0, "error" : None}
    data = {"model" : model, "messages" : [{"role" : "user", "content" : prompt}], "stream" : False}
    if images is not None and model in ["meta-llama/llama-3.2-11b-vision-instruct:free", ] :
        data["images"] = []
        for image in images :
            data["images"].append(encode_file_to_base64(image))
    try :
        request = urllib.request.Request(
            url,
            headers = {
                "Authorization": "Bearer %s" % token,
                "Content-Type" : "application/json",
            },
            data = json.dumps(data).encode("utf-8"),
        )
        response = urllib.request.urlopen(request)
        if response.getcode() == 200 :
            response_data = json.loads(response.read().decode('utf-8'))
            if "choices" in response_data.keys() : 
                result["message"] = response_data["choices"][0]["message"]["content"]
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
                response.getcode(),
            )
    except Exception as e :
        result["status"] = 2
        result["error"] = "[%s] Exception: %s" % (inspect.currentframe().f_code.co_name, e)
    return result

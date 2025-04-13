
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
    return providers

def get_llm_result_stream(provider, result) :
    if provider in ["Ollama", ] :
        try :
            for data in result["response"] :
                decoded = json.loads(data.decode('utf-8'))
                if decoded["done"] == True  :
                    break
                yield decoded.get("response", ""), None
        except Exception as e :
            yield None, e
    elif provider in ["OpenRouter", ] :
        buffer = ""
        while True : 
            chunk = result["response"].read(1024).decode('utf-8')
            if not chunk :
                break
            buffer += chunk
            while True:
                try:
                    line_end = buffer.find('\n')
                    if line_end == -1:
                        break
                    line = buffer[:line_end].strip()
                    buffer = buffer[line_end + 1:]
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            data_obj = json.loads(data)
                            error = data_obj.get("error", None) 
                            if error is not None : 
                                yield str(error), None 
                            else :
                                content = data_obj["choices"][0]["delta"].get("content", None)
                                if content is not None :
                                    yield content, None
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    break
    elif provider in ["Doubao", "Qwen", ] :
        try :
            for data in result["response"] :
                for line in data.decode('utf-8').split('\n') :
                    if line.strip().find("data:") == 0 :
                        line = line.strip()[5:]
                        line = line.strip()
                        if len(line) > 0 :
                            if line == "[DONE]" : break
                            decoded = json.loads(line)
                            choice = decoded["choices"][0]
                            yield choice["delta"]["content"], None
        except Exception as e :
            yield None, e
    else :
        yield None, "Invalid provider: %s." % provider

def call_llm_api(provider, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    providers = get_providers()
    result = {"message" : None, "status" : 0, "error" : None}
    if provider == "Ollama" :
        url = providers["Ollama"]["base_url"]
        result = call_ollama_api(url, model, prompt, images, max_tokens, temperature)
    elif provider in ["Doubao", "Qwen", "OpenRouter", ] :
        url = providers[provider]["url"]
        token = providers[provider]["token"]
        result = call_open_api(url, token, model, prompt, images, max_tokens, temperature)
    else :
        result["status"] = 1
        result["error"] = "[%s] Invalid provider: %s" % (inspect.currentframe().f_code.co_name, provider)
    return result

def call_ollama_api(url, model, prompt, images = None, max_tokens = 4096, temperature = 0.9) :
    result = {"message" : "", "status" : 0, "error" : None}
    data = {"model" : model, "prompt" : prompt, "max_tokens" : max_tokens, "temperature" : temperature, "stream" : False}
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

def call_open_api(url, token, model, prompt, max_tokens = 4096, temperature = 0.9, images = None) :
    result = {"response" : "", "status" : 0, "error" : None}
    data = {"model" : model, "messages" : [{"role" : "user", "content" : prompt}], "max_tokens" : max_tokens, "temperature" : temperature, "stream" : False}
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

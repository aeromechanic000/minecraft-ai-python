
from model import *
from world import *
from utils import *

class Memory(object) : 
    def __init__(self, agent) : 
        self.agent = agent
        self.records = []
        self.last_summarize_record_time = None
        self.summary, self.instruction = "", ""
        self.bot_path = os.path.join("bots", self.agent.configs["username"])
        if not os.path.isdir(self.bot_path) : 
            os.makedirs(self.bot_path)  
        self.memory_path = os.path.join(self.bot_path, "memory.json")
        self.history_path = os.path.join(self.bot_path, "history/%s.json" % get_random_label())
        if not os.path.isdir(os.path.dirname(self.history_path)) : 
            os.makedirs(os.path.dirname(self.history_path))  
        self.load()
    
    def load(self) : 
        if os.path.isfile(self.memory_path) :
            data = read_json(self.memory_path)
            self.summary = data.get("summary", "")
            self.instruction = data.get("instruction", "")

    def save(self) : 
        if os.path.isdir(os.path.dirname(self.memory_path)) : 
            write_json({"summary" : self.summary}, self.memory_path) 
        if os.path.isdir(os.path.dirname(self.history_path)) : 
            write_json({"records" : self.records}, self.history_path) 
    
    def get(self) : 
        self.summarize()
        info = self.get_records_info(6)
        info += "\n\n Here is a summary of earlier memory: %s" % self.summary
        return info
    
    def get_records_info(self, limit, exclude_summary = False) :
        info_list = []
        for i in range(-1, - min(len(self.records), 6) - 1, -1) :
            record = self.records[i]
            if exclude_summary == True and self.last_summarize_record_time is not None and not mc_time_later(record["time"], self.last_summarize_record_time) :
                break
            if record["type"] == "message" : 
                info_list.append("[%s-th day %s:%s] Got message from \"%s\": \"%s\"" % (record["time"][0], record["time"][1], record["time"][2], record["data"]["sender"], record["data"]["content"]))  
            if record["type"] == "status" : 
                if record["data"]["status"].strip().startswith("@") : 
                    info_list.append("[%s-th day %s:%s] I send a message in chat: \"%s\"" % (record["time"][0], record["time"][1], record["time"][2], record["data"]["status"]))  
                else :
                    info_list.append("[%s-th day %s:%s] I report a status: \"%s\"" % (record["time"][0], record["time"][1], record["time"][2], record["data"]["status"]))  
        return "\n".join(info_list)

    def summarize(self) : 
        if len(self.records) > 0 and (self.last_summarize_record_time is None or mc_time_later(self.records[-1]["time"], self.last_summarize_record_time)) : 
            add_log(title = self.agent.pack_message("Summarize memory."), content = "Last summarizing time: %s" % self.last_summarize_record_time, label = "memory")
            prompt = self.build_prompt()
            llm_result = call_llm_api(self.agent.configs["provider"], self.agent.configs["model"], prompt, max_tokens = self.agent.configs.get("max_tokens", 4096))
            add_log(title = self.agent.pack_message("Get LLM response:"), content = str(llm_result), label = "memory")
            if llm_result["status"] > 0 :
                add_log(title = self.agent.pack_message("Error in calling LLM: %s" % llm_result["error"]), label = "warning")
            else :
                _, data = split_content_and_json(llm_result["message"])
                add_log(title = self.pack_message("Got data."), content = str(data), label = "memory")
                summary = data.get("summary", None)
                if summary is not None : 
                    self.summary = str(summary)
                    if len(self.records) > 0 :
                        self.last_summarize_record_time = self.records[-1]["time"]
                instruction = data.get("instruction", None)
                self.instruction = str(instruction) if instruction is not None else ""
                self.save()
        else : 
            add_log(title = self.agent.pack_message("Memory summary is up to date."), content = "Last summarizing time: %s" % self.last_summarize_record_time, label = "memory")

    def update(self, record) : 
        record["time"] = self.agent.get_mc_time()
        self.records.append(record)
    
    def get_instruction(self) : 
        self.summarize()
        return self.instruction
    
    def reset_instruction(self) : 
        self.instruction = ""
    
    def build_prompt(self) : 
        prompt = '''
You are an AI assistant helping to summarize memory records for a Minecraft bot. Your goal is to produce a new summary that captures key facts and useful context for future planning, and to extract the next instruction for the bot to follow. 

Given: 
1. A list of history records, representing recent events and messages (including user input and in-game events); 
2. An old memory summary that contains previously known information. 

Please:
1. Generate a new summary that retains important past information and incorporates new relevant updates from the history;
2. Extract the next instruction for the bot to follow, based on the most recent relevant message or event.

If no action is required, set the instruction to an empty string ("") to avoid wasting time on meaningless tasks. If the current task is complex, break it down and provide a reasonable next step as the instruction. Include enough context and hints in the instruction to allow the bot to resume or continue the task correctly later.

## History Records
%s

## Old Summary
%s

## Output Format
The result should be formatted in **JSON** dictionary and enclosed in **triple backticks (` ``` ` )**  without labels like 'json', 'css', or 'data'.
- **Do not** generate redundant content other than the result in JSON format.
- **Do not** use triple backticks anywhere else in your answer.
- The JSON must include the following keys and values accordingly :
    - 'summary' : The new summary of the memory, about 500 words. 
    - 'instruction' : The instruction for the bot. If there is no tasks to do, make sure set it to empty string.

Following is an example of the output: 
```
{
    "summary" : "I got a message from the player to ask me to collect some woods, and I collected 20 ore logs.",  
    "instruction" : "try to collect more ore logs.",
}
''' % (self.get_records_info(10, True), self.summary)
        return prompt

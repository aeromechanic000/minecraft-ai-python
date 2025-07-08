
import threading
from model import *
from world import *
from utils import *

class Memory(object) : 
    def __init__(self, agent) : 
        self.agent = agent
        self.summarize_thread = None
        self.records = []
        self.last_summarize_record_time = None
        self.last_process_record_time = None
        self.summary, self.longterm_thinking, self.bank, self.skin_path = "", "", {}, None
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
            self.skin_path = data.get("skin_path", None)
            if self.agent.settings.get("load_memory", False) == True : 
                self.summary = data.get("summary", "")
                self.longterm_thinking = data.get("longterm_thinking", self.agent.configs.get("longterm_thinking", ""))
                self.bank = data.get("bank", {})
                self.records += data.get("records", [])

    def save(self) : 
        if os.path.isdir(os.path.dirname(self.memory_path)) : 
            write_json({"summary" : self.summary, "longterm_thinking" : self.longterm_thinking, "bank" : self.bank, "skin_path" : self.skin_path, "records" : self.get_records(10, True)}, self.memory_path) 
        if os.path.isdir(os.path.dirname(self.history_path)) : 
            write_json({"records" : self.records}, self.history_path) 
    
    def get(self, record_num = 10) : 
        info = "### Latest History Records:\n%s" % self.get_records_info(record_num)
        info += "\n\n ### Memory Summary (a summary of earlier memory): %s" % self.summary
        info += "\n\n ### Long-Term Thinking: %s" % self.longterm_thinking
        bank_info = ""
        for key, value in self.bank.items() :
            bank_info += "- %s: %s\n" % (key, value["value"])
        if len(bank_info.strip()) > 0 :
            info += "\n\n ### Memory Bank (the remembered facts and information):\n%s" % bank_info 
        return info
    
    def get_records_info(self, limit, exclude_summary = False) :
        records = self.get_records(limit, exclude_summary) 
        info_list = []
        for record in records :
            if record["type"] == "message" : 
                info_list.append("[The %s-th day, %s:%s] Got message from \"%s\": \"%s\"" % (record["time"][0], record["time"][1], record["time"][2], record["data"]["sender"], record["data"]["content"]))  
            elif record["type"] == "reflection" : 
                info_list.append("[The %s-th day, %s:%s] Got reflection from myself : \"%s\"" % (record["time"][0], record["time"][1], record["time"][2], record["data"]["content"]))  
            elif record["type"] == "report" : 
                info_list.append("[The %s-th day, %s:%s] I sent a report message: \"%s\"" % (record["time"][0], record["time"][1], record["time"][2], record["data"]["content"]))  
            elif record["type"] == "status" :
                info_list.append("[The %s-th day, at time %s:%s] \"%s\" sends a message in chat: \"%s\"" % (record["time"][0], record["time"][1], record["time"][2], record["data"]["sender"], record["data"]["content"]))  
        return "\n".join(info_list)

    def get_records(self, limit, exclude_summary = False) :
        records = []
        for i in range(-1, - min(len(self.records), limit) - 1, -1) :
            record = self.records[i]
            if exclude_summary == True and self.last_summarize_record_time is not None and record["timelabel"] <= self.last_summarize_record_time :
                break
            records.append(record)
        records.reverse()
        return records 

    def summarize(self, force = False) : 
        if self.summarize_thread is not None : 
            self.summarize_thread.join()
        self.summarize_thread = threading.Thread(target = self.async_summarize, args=(force, ))
        self.summarize_thread.start()
    
    def remember(self, key, value) :
        self.bank[key] = {"value" : value, "time" : get_datetime_stamp()}
        if len(self.bank.keys()) > self.agent.settings.get("memory_bank_size", 20) :
            oldest_key = min(self.bank.keys(), key = lambda k : self.bank[k]["time"])
            if oldest_key in self.bank.keys() :
                del self.bank[oldest_key]

    def async_summarize(self, force = False) : 
        if force == True or len(self.get_messages_to_work()) > 0 :
            add_log(title = self.agent.pack_message("Summarize memory."), content = "Last summarizing time: %s" % self.last_summarize_record_time, label = "memory")
            last_summarize_time = get_datetime_stamp() 
            prompt = self.build_prompt()
            add_log(title = self.agent.pack_message("Built prompt."), content = prompt, label = "memory", print = False)
            json_keys = {
                "summary" : {
                    "description" : "The new summary of the memory, about 500 words.", 
                },  
                "longterm_thinking" : {
                    "description" : "The long-term thinking of the bot, about 200 words; If not necessary to update the long-term thinking, leave the value to null.",
                },
            }
            examples = [
                '''
```
{
    "summary" : "I got a message from the player to ask me to collect some woods, and I collected 20 ore logs.",  
    "longterm_thinking" : "Enjoy the life.",
}
```
''',
            ]
            provider, model = self.agent.get_provider_and_model("memory")
            llm_result = call_llm_api(provider, model, prompt, json_keys, examples, max_tokens = self.agent.configs.get("max_tokens", 4096))
            add_log(title = self.agent.pack_message("Get LLM response:"), content = json.dumps(llm_result, indent = 4), label = "memory", print = False)
            data = llm_result["data"]
            if data is not None :
                summary, longterm_thinking = data.get("summary", None), data.get("longterm_thinking", None)
                if summary is not None : 
                    self.summary = str(summary)
                    if len(self.records) > 0 :
                        self.last_summarize_record_time = last_summarize_time 
                    add_log(title = self.agent.pack_message("Memory summary updated."), content = self.summary, label = "memory")
                if longterm_thinking is not None: 
                    self.longterm_thinking = str(longterm_thinking)
                    add_log(title = self.agent.pack_message("Long-term thinking updated."), content = self.longterm_thinking, label = "memory")
                if summary is not None or longterm_thinking is not None :
                    self.save()

    def update(self, record) : 
        record["time"], record["timelabel"] = self.agent.get_mc_time(), get_datetime_stamp() 
        self.records.append(record)
        self.save()
    
    def clear_messages_to_work(self) : 
        if len(self.records) > 0 :
            self.last_process_record_time = self.records[-1]["timelabel"]
        else :
            self.last_process_record_time = None

    def get_messages_to_work(self) : 
        messages = [] 
        records = self.get_records(10, True)
        for i in range(-1, - len(records) - 1, -1) :
            record = records[i]
            if self.last_process_record_time is not None and record["timelabel"] <= self.last_process_record_time :
                break
            if record["type"] in ["message", "reflection"] :
                messages.append(record["data"])
        messages.reverse()
        return messages
    
    def build_prompt(self) : 
        prompt = '''
You are an AI assistant helping to summarize memory records for a Minecraft bot. Your goal is to produce a new summary that captures key facts and useful context for the bot's future planning. When generating the memory summary, you should also consider the personality profile and the long-term thinkings of the bot.

Given: 
1. A list of history records, representing recent events and messages (including user input and in-game events); 
2. An old memory summary that contains previously known information. 
3. The profile of the bot.
4. The long-term thinking of the bot.

Please:
1. Generate a new summary that preserves important past information while integrating new, relevant updates from the recent history. Pay special attention to the following:
    - If there are any task requirements — including newly assigned tasks from other players or ongoing tasks that have not yet been completed — be sure to include them in the summary. This helps the bot stay aware of its current objectives and prevents forgetting unfinished work.
    - In the end of the new summary, include a update of what the bot have just finished, and some hints for the next steps, if necessary. This helps the bot to plan its next actions based on the latest information.
2. Generate an update to the "longterm_thinking" field, only if significant events have occurred that meaningfully impact the agent’s overall goals, behavioral patterns, or decision heuristics.
    - The long-term thinking should be written in neutral, third-person form (avoid using "I" or "You").
    - Maintain stability: Do not overfit to temporary events or isolated tasks.
    - Describe enduring tendencies, values, or learned adjustments in strategy.
    - If recent actions reveal new preferences, constraints, or mission alignment changes, revise the summary accordingly.
    - When reflecting on events (e.g., completing a task), clearly separate facts (what has occurred) from evolving intent (what should change or persist). 

## Bot's Status
%s

## Long-term Thinking
%s

## History Records
%s

## Old Summary
%s
''' % (self.get_status_info(), self.longterm_thinking, self.get_records_info(20), self.summary)
        return prompt
    
    def get_status_info(self) :
        status = "- Bot's Name: %s" % self.agent.bot.username
        status += "\n- Bot's Profile: %s" % self.agent.configs.get("profile", "A smart Minecraft AI character.")
        status += "\n- Bot's Status of Health (from 0 to 20, where 0 for death and 20 for completely healthy): %s" % self.agent.bot.health 
        status += "\n- Bot's Degree Of Hungry (from 0 to 20, where 0 for hungry and 20 for full): %s" % self.agent.bot.food
    
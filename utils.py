
import inspect, functools, re
import datetime, json
import math, random
import logging, warnings
warnings.filterwarnings("ignore")

def get_datetime_attributes() :
    dt = datetime.datetime.now()
    return dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second

def get_date_stamp() :
    year, month, day, _, _, _ = get_datetime_attributes()
    return "%d/%02d/%02d" % (year, month, day)

def get_time_stamp() :
    _, _, _, hour, minute, second = get_datetime_attributes()
    return "%02d:%02d:%02d" % (hour, minute, second)

def get_datetime() :
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def get_datetime_stamp() :
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def get_random_label() :
    return "%s_%s" % (get_datetime_stamp(), "%03d" % random.randint(0, 1000))

def read_json(filepath, init_cls = dict) :
    data = init_cls()
    with open(filepath, "r") as f :
        data = json.load(f)
    return data

def write_json(data, filepath) :
    result = False
    with open(filepath, "w") as f :
        json.dump(data, f, indent = 4)
        result = True
    return result

class bstyles:
    GREEN = '\033[92m'           
    BLUE = '\033[94m'           
    CYAN = '\033[96m'            
    ORANGE = '\033[38;5;208m'   
    RED = '\033[31m'            
    PINK = '\033[38;5;205m'     
    GRAY = '\033[90m'           
    PURPLE = '\033[35m'         
    YELLOW = '\033[93m'        
    WHITE = '\033[97m'        
    LIGHT_GREEN = '\033[92;1m'  
    LIGHT_CYAN = '\033[96;1m'   
    LIGHT_RED = '\033[91m'      
    LIGHT_PURPLE = '\033[95m'   
    LIGHT_ORANGE = '\033[38;5;214m'
    DARK_BLUE = '\033[34m'      
    DARK_CYAN = '\033[36m'      
    DARK_YELLOW = '\033[33m'   
    DARK_ORANGE = '\033[38;5;166m' 
    BROWN = '\033[38;5;130m'    
    GOLD = '\033[38;5;220m'     
    SILVER = '\033[38;5;246m'   
    LIME = '\033[38;5;118m'    
    MINT = '\033[38;5;159m'     
    LAVENDER = '\033[38;5;183m' 
    ROSE = '\033[38;5;213m'     
    BG_BLACK = '\033[40m'       
    BG_RED = '\033[41m'         
    BG_GREEN = '\033[42m'       
    BG_YELLOW = '\033[43m'      
    BG_BLUE = '\033[44m'        
    BG_PURPLE = '\033[45m'      
    BG_CYAN = '\033[46m'        
    BG_WHITE = '\033[47m'       
    BG_GRAY = '\033[100m'       
    ENDC = '\033[0m'            
    BOLD = '\033[1m'            
    FAINT = '\033[2m'          
    ITALIC = '\033[3m'          
    UNDERLINE = '\033[4m'       
    SLOW_BLINK = '\033[5m'      
    RAPID_BLINK = '\033[6m'     
    INVERT = '\033[7m'          
    HIDE = '\033[8m'            
    STRIKETHROUGH = '\033[9m'   
    DOUBLE_UNDERLINE = '\033[21m' 
    OVERLINE = '\033[53m'        
    RESET_UNDERLINE = '\033[24m' 
    RESET_BOLD = '\033[22m'      
    RESET_INVERT = '\033[27m'    

def print_msg(title, content = "", label = "text") :
    head_tag = ""
    end_tag = ""
    if label == "system" :
        head_tag = bstyles.PURPLE
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "agent" :
        head_tag = bstyles.LIGHT_CYAN
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "plugin" :
        head_tag = bstyles.CYAN
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "memory" :
        head_tag = bstyles.DARK_CYAN
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "action" :
        head_tag = bstyles.ORANGE
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "coding" :
        head_tag = bstyles.DARK_ORANGE
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "success" :
        head_tag = bstyles.GREEN
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "warning" :
        head_tag = bstyles.YELLOW
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "error" :
        head_tag = bstyles.RED
        end_tag = bstyles.ENDC
        title = "[%s] %s" % (get_datetime(), title)

    print(head_tag + title + end_tag)
    if len(content.strip()) > 0 :
        print(content)

def add_log(title, content = "", label = "text", print = True) : 
    if label == "error" : 
        logging.error("(%s) %s" % (title, content))
    elif label == "warining" : 
        logging.warning("(%s) %s" % (title, content))
    else :  
        logging.info("(%s) %s" % (title, content))
    if print : 
        print_msg(title, content, label)

def get_random_vector(dist):
    angle = random.uniform(0, 2 * math.pi)
    x = math.cos(angle) * dist
    y = math.sin(angle) * dist
    return [x, y]

def sizeof(js_mapping) : 
    length = 0
    if js_mapping is not None :
        for key in js_mapping : 
            length += 1
    return length

def mc_time_later(t1, t2) : 
    if t1[0] > t2[0] :
        return True
    elif t1[0] < t2[0] :
        return False 
    elif t1[1] > t2[1] :
        return True
    elif t1[1] < t2[1] :
        return False 
    elif t1[2] > t2[2] :
        return True
    elif t1[2] < t2[2] :
        return False 
    elif t1[3] > t2[3] :
        return True
    return False 

def rotate_x_z(x, z, orientation, sizex, sizez) :
    if orientation == 0 : 
        return [x, z]
    elif orientation == 1 : 
        return [z, sizex-x-1]
    elif orientation == 2 :
        return [sizex-x-1, sizez-z-1]
    if orientation == 3 : 
        return [sizez-z-1, x]

def clean_string(s):
    s = s.lower()
    s = re.sub(r'[^\w\s]', '', s)
    return s

def count_words_in_string(s, keywords):
    count = 0
    for word in keywords :
        if word in s.split(" ") :
            count += 1
    return count

common_english_words = {
    "the", "and", "of", "a", "to", "in", "is", "you", "that", "it",
    "he", "was", "for", "on", "are", "as", "with", "his", "they", "I",
    "at", "be", "this", "have", "from", "or", "one", "had", "by", "word",
    "but", "not", "what", "all", "were", "we", "when", "your", "can",
    "said", "there", "use", "an", "each", "which", "she", "do", "how",
    "their", "if", "will", "up", "other", "about", "out", "many", "then",
    "them", "these", "so", "some", "her", "would", "make", "like",
    "him", "into", "time", "has", "look", "two", "more", "write",
    "go", "see", "number", "no", "way", "could", "people", "my",
    "than", "first", "water", "been", "call", "who", "oil", "its",
    "now", "find", "long", "down", "day", "did", "get", "come",
    "made", "may", "part"
}

# Define a set of common Chinese words
common_chinese_words = {
    "的", "一", "是", "不", "在", "人", "有", "我", "他", "这",
    "个", "上", "们", "来", "到", "时", "大", "地", "为",
    "子", "中", "你", "说", "生", "国", "年", "着", "就", "那",
    "和", "要", "她", "出", "也", "得", "里", "后", "自", "以",
    "会", "家", "可", "下", "而", "过", "天", "去", "能", "对",
    "小", "多", "然", "于", "心", "学", "么", "之", "都", "好",
    "看", "起", "发", "当", "没", "成", "只", "如", "事", "把",
    "还", "用", "第", "样", "道", "想", "作", "种", "开", "美",
    "总", "从", "无", "情", "己", "面", "最", "女", "但", "现",
    "前", "些", "所", "同", "日", "手", "又", "行", "意", "动",
    "方", "期", "它", "头", "经", "长", "儿"
}

def get_keywords(text):
    words = []
    temp_word = ""
    for char in text :
        if '\u4e00' <= char <= '\u9fff':
            if temp_word:
                if temp_word.lower() not in common_english_words:
                    words.append(temp_word)
                temp_word = ""
            if len(char.strip) > 0 and char not in common_chinese_words:
                words.append(char)
        else:
            if char.isalnum():
                temp_word += char
            else:
                if temp_word :
                    if temp_word.lower() not in common_english_words:
                        words.append(temp_word)
                    temp_word = ""
                if len(char.strip()) > 0 :
                    words.append(char)
    temp_word = temp_word.strip()
    if len(temp_word) > 0 :
        if temp_word.lower() not in common_english_words:
            words.append(temp_word)
    return words

def get_top_k_strings(keywords, strings, top_k) :
    result = []
    for i, s in enumerate(strings) :
        result.append((i, s, count_words_in_string(s, keywords)))
    result.sort(key = lambda x: x[2], reverse=True)
    if len(result) > 0 and result[0][2] > 0 : 
        result = result[:top_k]
    return result

def simple_rag(query, records, top_k = 5) : 
    keywords = get_keywords(clean_string(query))
    top_k_result = get_top_k_strings(keywords, [clean_string(r) for r in records], top_k)
    return [item[:2] for item in top_k_result]



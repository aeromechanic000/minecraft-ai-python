
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

def get_random_filename() :
    return "%s_%s" % (get_datetime_stamp(), "%03d" % random.randint(0, 1000))

def read_json(filepath, init_cls = dict) :
    data = init_cls()
    with open(filepath, "r") as f :
        data = json.load(f)
    return data

def write_json(data, filepath) :
    result = False
    with open(filepath, "w") as f :
        json.dump(data, f, sort_keys = True, indent = 4)
        result = True
    return result

class bcolors:
    HEADER = '\033[95m'
    FAIL = '\033[91m'
    WARNING = '\033[93m'
    BLUE = '\033[94m'           # Blue
    CYAN = '\033[96m'           # Cyan
    GREEN = '\033[92m'          # Green
    ORANGE = '\033[38;5;208m'   # Orange
    RED = '\033[31m'            # Red
    PINK = '\033[38;5;205m'     # Pink
    GRAY = '\033[90m'           # Gray
    PURPLE = '\033[35m'         # Purple
    YELLOW = '\033[33m'         # Yellow
    WHITE = '\033[97m'          # White
    LIGHT_BLUE = '\033[94;1m'   # Light Blue
    MAGENTA = '\033[35;1m'      # Magenta
    DARK_GREEN = '\033[32m'     # Dark Green
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_msg(title, content = "", label = "text") :
    head_tag = ""
    end_tag = ""
    if label == "header" :
        head_tag = bcolors.ORANGE
        end_tag = bcolors.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    if label == "success" :
        head_tag = bcolors.GREEN
        end_tag = bcolors.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    if label == "execute" :
        head_tag = bcolors.CYAN
        end_tag = bcolors.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    if label == "request" :
        head_tag = bcolors.BLUE
        end_tag = bcolors.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "warning" :
        head_tag = bcolors.WARNING
        end_tag = bcolors.ENDC
        title = "[%s] %s" % (get_datetime(), title)
    elif label == "error" :
        head_tag = bcolors.FAIL
        end_tag = bcolors.ENDC
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
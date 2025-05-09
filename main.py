
import os, sys

from manager import * 
from utils import *

if __name__ == "__main__":
    for d in ["./logs", "./generated_actions"] : 
        if not os.path.isdir(d) : 
            os.mkdir(d)

    logging.basicConfig(
            filename = os.path.join("./logs/log-%s.json" % get_datetime_stamp()),
            filemode = 'a',
            format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt = '%H:%M:%S',
            level = logging.DEBUG, 
    )

    configs_path = "configs.json"
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]) : 
         configs_path = sys.argv[1] 
    add_log(title = "Using configs:", content = configs_path, label = "success")
    configs = read_json(configs_path)
    mcp = Manager(configs)
    mcp.start()
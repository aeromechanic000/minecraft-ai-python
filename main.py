
import os, sys

from manager import * 
from utils import *

if __name__ == "__main__":
    if not os.path.isdir("./logs") : 
          os.mkdir("./logs")

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
    add_log("Using configs: %s" % configs_path)

    configs = read_json(configs_path)
    mcp = Manager(configs)
    mcp.start()
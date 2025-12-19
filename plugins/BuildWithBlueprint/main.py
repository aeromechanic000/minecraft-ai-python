
import os, sys, time
sys.path.append("../../")

from plugin import Plugin 
from agent import * 

def build_with_blueprint(agent, blueprint, idea) :
    agent.plugins["BuildWithBlueprint"].build(blueprint, idea)

def stop_build(agent) :
    agent.plugins["BuildWithBlueprint"].stop()

def blocks_cmp(a, b) : 
    if a[1] == b[1] :
        if a[0] == b[0] :
            return a[2] - b[2]
        else :
            return a[0] - b[0]
    return a[1] - b[1]

def get_blueprint_range(blueprint) : 
    min_x, max_x, min_y, max_y, min_z, max_z = math.inf, -math.inf, math.inf, -math.inf, math.inf, -math.inf
    for block in blueprint["blocks"] : 
        min_x, max_x = min(min_x, block[0]), max(max_x, block[0])
        min_y, max_y = min(min_y, block[1]), max(max_y, block[1])
        min_z, max_z = min(min_z, block[2]), max(max_z, block[2])
    return min_x, max_x, min_y, max_y, min_z, max_z

class PluginInstance(Plugin) :
    def __init__(self, agent) : 
        super().__init__(agent)
        self.goals, self.blueprint, self.built = [], None, {} 
        self.plugin_name = os.path.basename(os.path.dirname(os.path.abspath(__file__))) 
        self.path = "./plugins/%s/" % self.plugin_name
        self.blueprints = {}
        try :
            blueprints_dir = './plugins/BuildWithBlueprint/blueprints/'
            for file in os.listdir(blueprints_dir) :
                if file.endswith('.json') and not file.startswith('.') : 
                    self.blueprints[file[0:-5]] = read_json(os.path.join(blueprints_dir, file))
        except Exception as e :  
            add_log(title = self.agent.pack_message("Exception happens in initializing \"BuildWithBlueprint\":"), content = str(e), label = "warning")
        self.load()
    
    def load(self) : 
        filepath = os.path.join(self.path, "save.json")
        if os.path.isfile(filepath) :
            data = read_json(filepath)
            self.goals = data.get("goals", [])
            self.blueprint = data.get("blueprint", None)
            self.built = data.get("built", {})
    
    def save(self) :
        if os.path.isdir(self.path) :
            filepath = os.path.join(self.path, "save.json")
            write_json({"goals" : self.goals, "blueprint" : self.blueprint, "built" : self.built}, filepath)
    
    def get_actions(self) : 
        return [
            {
                "name" : "build",
                "description" : "Build a structure when there is a proper blueprint for the refenrece. This is preferred if there is a blueprint that is similar to what you want to build, and the name of reference blueprint should be selected from the availabel blueprints.\n ## Available Blueprints\n%s" % ",".join(list(self.blueprints.keys())),
                "params" : {
                    "blueprint" : { "type" : "string", "description": "name of the reference blueprint." },
                    "idea" : { "type" : "string", "description" : "a concise description on how to modify a reference blueprint so that buildings sharing the same blueprint can each have distinct, recognizable features." },
                },
                "perform" : build_with_blueprint, 
            },
            {
                "name" : "stop_build",
                "description" : "Call when you are satisfied with what you built. It will stop the action if you are building an architecture with a reference blueprint.",
                "params" : {},
                "perform" : stop_build, 
            },
        ]
    
    def build(self, name, idea) : 
        if self.blueprints.get(name, None) is None : 
            self.agent.bot.chat("I can't find a blueprint of name \"%s\" for reference." % name)
            add_log(title = self.agent.pack_message("Can't find blueprint."), content = "blueprint: \"%s\"; idea: \"%s\"" % (name, idea), label = "plugin")
            return

        add_log(title = self.agent.pack_message("Build with blueprint."), content = "blueprint: \"%s\"; idea: \"%s\"" % (name, idea), label = "plugin")

        if self.blueprint is not None and self.blueprint["name"] == name and len(self.goals) > 0 : 
            goal = self.goals[-1]
            add_log(title = self.agent.pack_message("Continue building with blueprint."), content = "Next goal: %s x %s" % (goal["quantity"], goal["name"]), label = "plugin", print = False)
            self.agent.bot.chat("I will continue with building \"%s\"." % self.blueprint["name"])
            self.execute()
        else :
            self.agent.bot.chat("I am going to modify the blueprint of name \"%s\"." % name)
            blueprint = self.generate_blueprint(name, idea)
            blocks = []
            if blueprint is not None : 
                blocks = blueprint.get("blocks", [])
            
            if len(blocks) > 0 :
                add_log(title = self.agent.pack_message("Generated a blueprint to build:"), content = json.dumps(blueprint, indent = 4), label = "plugin", print = False)
                self.agent.bot.chat("I got the modified blueprint.")
                self.set_goal(name, 1, idea, blueprint)
            else :
                add_log(title = self.agent.pack_message("Generated blueprint is invalid:"), content = json.dumps(blueprint, indent = 4), label = "plugin", print = False)
                self.agent.bot.chat("I got an invalid blueprint.")
    
    def set_goal(self, name, quantity = 1, idea = "", blueprint = None) :
        self.stop()
        goal = {"name" : name, "quantity" : quantity}
        if blueprint is not None :
            self.blueprint = blueprint
        elif self.blueprints.get(name, None) is not None :
            self.blueprint = self.blueprints[name]
        
        if self.blueprint is None :
            return  

        self.blueprint["blocks"] = sorted(self.blueprint["blocks"], key = functools.cmp_to_key(blocks_cmp))
        self.goals.append(goal)
        add_log(title = self.agent.pack_message("Set new building goal."), content = "name: %s; quantity: %s; blueprint: %s" % (name, quantity, json.dumps(self.blueprint, indent = 4)), label = "plugin", print = False)
        self.save()
        self.execute()
    
    def execute(self) :
        add_log(title = self.agent.pack_message("Executing goals:"), content = str(self.goals), label = "plugin", print = False)
        while len(self.goals) > 0 :
            goal = self.goals[0]
            try :
                if self.blueprints.get(goal["name"], None) is None :
                    add_log(title = self.agent.pack_message("Executing item goal:"), content = "name: %s; quantity: %s" % (goal["name"], goal["quantity"]), label = "plugin", print = False)
                    if self.agent.bot.game is not None and self.agent.bot.game.gameMode == "creative" :
                        self.agent.bot.chat("/give %s %s 1" % (self.agent.bot.username, goal["name"]))
                        time.sleep(2)
                    if not item_satisfied(self.agent, goal["name"], goal["quantity"]) :
                        self.agent.bot.chat("I can't finish building \"%s\", as I don't have %s x \"%s\"." % (self.goals[-1]["name"], goal["quantity"], goal["name"]))
                        break
                    elif len(self.goals) > 0 :
                        self.goals.pop(0) 
                else :
                    add_log(title = self.agent.pack_message("Executing build goal:"), content = "name: %s; quantity: %s " % (goal["name"], goal["quantity"]), label = "plugin", print = False)
                    res = self.build_goal_execute(self.blueprint, self.built)
                    for name, quantity in res["missing"].items() :
                        self.goals.insert(0, {"name": name, "quantity": quantity})
                    if res["failed"] == True :
                        self.agent.bot.chat(res["error"]) 
                        break
                    if res["finished"] == True : 
                        if len(self.goals) > 0 :
                            self.goals.pop(0)
                        else :
                            self.leave_current_building()
                            self.agent.bot.chat("I finished the building.")
                self.save()
            except Exception as e :
                add_log(title = self.agent.pack_message("Exception happens in executing."), content = "name: %s; quantity: %s; exception : %s" % (goal["name"], goal["quantity"], e), label = "warning", print = False)
                self.agent.bot.chat("I can't build \"%s\" right now." % goal["name"])
                break
        self.stop()

    def stop(self) : 
        self.goals, self.blueprint, self.built = [], None, {}
        self.save()
    
    def leave_current_building(self) :
        door_pos = self.get_current_building_door()
        if door_pos :
            use_door(self.agent, vec3.Vec3(*door_pos))
            time.sleep(3)
            move_away(self.agent, 2)
            time.sleep(1)
        else : 
            if self.blueprint is not None :
                min_x, max_x, min_y, max_y, min_z, max_z = get_blueprint_range(self.blueprint)
                agent_pos = get_entity_position(self.agent.bot.entity)
                if agent_pos is not None :
                    go_to_position(self.agent, min_x - 1, agent_pos.y, min_z -1, 0)
    
    def in_building(self) :
        if self.blueprint is None or self.built.get("position", None) is None : return False
        agent_pos = get_entity_position(self.agent.bot.entity)
        if agent_pos is not None :
            pos = self.built["position"]
            min_x, max_x, min_y, max_y, min_z, max_z = get_blueprint_range(self.blueprint)
            if agent_pos.x >= pos.x and agent_pos.x < pos.x + abs(max_x - min_x) and agent_pos.y >= pos.y and agent_pos.y < pos.y + abs(max_y - min_y) and agent_pos.z >= pos.z and agent_pos.z < pos.z + abs(max_z - min_z) :
                return True
        return False

    def get_current_building_door(self) :
        if not self.in_building() : return None 
        pos = None
        for block in self.blueprint["blocks"] :
            if "door" in block[3] : 
                pos = block[:3]
                break
        if pos is not None : 
            pos = [self.built["position"].x + pos[0], self.built["position"].y + pos[1], self.built["position"].z + pos[2]]
        return pos

    def generate_blueprint(self, name, idea) :
        blueprint = self.blueprints[name]
        items = self.get_items_for_building(blueprint)
        gen_blueprint = None 
        prompt = '''
You are a playful Minecraft bot named $NAME who is good at making building blueprints based on the following reference and a design idea: 

## Reference Blueprint
%s

## Building Idea
%s
''' % (json.dumps(blueprint, indent = 4), idea)
        json_keys = {
            "blocks" : {
                "description" : "A JSON list of blocks, and for each block, it is also a JSON list including the x, y, z coordinates and the item name.",
            }
        }
        examples = [ 
            '''
```
{
    "blocks" : [
        [0, 0, 0, "planks"],
        [0, 0, 1, "planks"],
        [1, 0, 1, "planks"],
        [1, 0, 0, "planks"]
    ]
}
```
''' 
        ]
        provider, model = self.agent.get_provider_and_model("build")
        llm_result = call_llm_api(self.agent, provider, model, prompt, json_keys, examples, max_tokens = self.agent.configs.get("max_tokens", 4096))
        add_log(title = self.agent.pack_message("Get LLM response:"), content = json.dumps(llm_result, indent = 4), label = "plugin", print = False)
        data = llm_result["data"]
        if data is not None and data.get("blocks", None) is not None :
            blocks = data["blocks"]
            if isinstance(blocks, list) and len(blocks) > 0 :
                gen_blueprint = {"name" : blueprint["name"], "blocks" : []}
                for  block in blocks :
                    if isinstance(block, list) and len(block) > 3 and all(isinstance(x, int) for x in block[:3]) and block[3] in items :
                        gen_blueprint["blocks"].append(block)
                if len(gen_blueprint["blocks"]) < 1 :
                    self.agent.bot.chat("The generated blueprint does't have any valid blocks.")
                    add_log(title = self.agent.pack_message("Found none valid blocks in the generated blueprint."), label = "plugin", print = False)
            else :
                self.agent.bot.chat("The generated blueprint does't contain \"blocks\".")
                add_log(title = self.agent.pack_message("The generated blueprint does't contain \"blocks\""), label = "plugin", print = False)
        return gen_blueprint
    
    def get_items_for_building(self, blueprint = None) :
        building_blocks = [
            "stone", "cobblestone", "stone_bricks", "oak_planks", "spruce_planks",
            "birch_planks", "dark_oak_planks", "sandstone",
            "red_sandstone", "bricks", "deepslate_bricks", "quartz_block",
            "snow_block", "gray_concrete", "white_concrete", "obsidian",
        ]
        building_items = [
            "torch", "ladder", "oak_door", "spruce_door", "glass",
            "glass_pane", "oak_fence", "spruce_fence", "oak_stairs", "stone_stairs",
            "cobblestone_stairs", "sandstone_stairs", "brick_stairs", "quartz_stairs",
            "oak_slab", "stone_slab", "brick_slab", "quartz_slab",
        ]
        return building_blocks + building_items
    
    def build_goal_execute(self, blueprint, built, relax = 0) :
        position = built.get("position", None)
        missing = {}
        finished = False
        ignored = 0
        failed = False
        error = None 

        if position is None : 
            min_x, max_x, min_y, max_y, min_z, max_z = get_blueprint_range(blueprint) 
            size = max(max_x - min_x, max_z - min_z)
            position = get_nearest_freespace(self.agent, math.ceil(size), 32)

        if position is None :
            failed = True 
            error = "I can't find a free space to build %s." % blueprint["name"]
        else :
            self.built["position"] = position
            self.save()
            inventory = get_inventory_counts(self.agent)
            satisfied, added = 0, 0
            for block in blueprint["blocks"] :
                try :
                    block_name = block[3]
                    if block_name is None or len(block_name.strip()) < 1 : 
                        continue
                    world_pos = vec3.Vec3(position.x + block[0], position.y + block[1], position.z + block[2])
                    current_block = self.agent.bot.blockAt(world_pos)
                    if current_block is not None : 
                        if block_satisfied(block_name, current_block, relax) :
                            satisfied += 1
                            continue
                        else :
                            block_typed = get_type_of_generic(self.agent, block_name)
                            if inventory.get(block_typed, 0) > 0 :
                                res = place_block(self.agent, block_typed, world_pos.x, world_pos.y, world_pos.z)
                                time.sleep(1)
                                if res == False :
                                    add_log(title = self.agent.pack_message("Failed to place block."), content = "block_name: %s; position: (%s, %s, %s)" % (block[3], world_pos.x, world_pos.y, world_pos.z), label = "plugin", print = False)
                                    ignored += 1
                                time.sleep(0.5)
                            else :
                                if missing.get(block_typed, None) is None :
                                    missing[block_typed] = 0
                                missing[block_typed] += 1

                        current_block = self.agent.bot.blockAt(world_pos)
                        if block_satisfied(block_name, current_block, relax) :
                            added += 1
                except Exception as e :
                    add_log(title = self.agent.pack_message("Exception happens in executing build goal."), content = "Placing %s at (%s, %s, %s): %s" % (block[3], world_pos.x, world_pos.y, world_pos.z, e), label = "warning", print = False)
                    continue

            if ignored > 0 : 
                self.leave_current_building()
            if satisfied >= len(blueprint["blocks"]) :
                finished = True
            elif added < 1 and len(missing) < 1 :
                failed = True
                error = "I can't finish building the complete version of %s." % blueprint["name"]

        return {"finished" : finished, "missing" : missing, "failed" : failed, "error" : error}
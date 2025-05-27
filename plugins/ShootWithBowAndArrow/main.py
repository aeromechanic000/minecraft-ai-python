
import sys, time
sys.path.append("../../")

from plugin import Plugin 
from skills import * 
from world import * 

def held_bow(agent) :
    """Return `True` if the bot is holding a bow in hand; call with held_bow(agent)."""
    item = agent.bot.heldItem
    if item is None or "bow" not in item.name : 
        bow = get_an_item_in_inventory(agent, "bow", exclude = ["crossbow"])
        if bow is not None :
            agent.bot.equip(bow, "hand")
        else :
            crossbow = get_an_item_in_inventory(agent, "crossbow")
            if crossbow is not None :
                agent.bot.equip(crossbow, "hand")
        item = agent.bot.heldItem

    has_arrow = True
    if agent.bot.game is not None and agent.bot.game.gameMode != "creative" :
        has_arrow = any("arrow" in k and v > 0 for k, v in get_inventory_counts(agent).items())
    return item is not None and "bow" in item.name and has_arrow

def get_elevation(agent, entity) :
    elevation = 0
    agent_pos = get_entity_position(agent.bot.entity)
    entity_pos = get_entity_position(entity)
    if agent_pos is not None and entity_pos is not None :
        elevation = 1 + agent_pos.distanceTo(entity_pos) // 10 
    return elevation

def bow_fight(agent, entity) :
    agent_pos = get_entity_position(agent.bot.entity)
    entity_pos = get_entity_position(entity)
    if agent_pos is not None and agent_pos.distanceTo(entity_pos) > 5 :
        go_to_position(agent, entity_pos.x, entity_pos.y, entity_pos.z)
    time.sleep(0.5)

    item = agent.bot.heldItem
    if item is not None and "crossbow" not in item.name :
        if agent_pos is not None and entity_pos is not None and agent_pos.distanceTo(entity_pos) > 12 :
            go_to_position(agent, entity_pos.x, entity_pos.y, entity_pos.z, 10)
        agent.bot.activateItem()
        time.sleep(0.8)
        agent.bot.lookAt(entity_pos.offset(0, get_elevation(agent, entity), 0))
        time.sleep(0.2)
        agent.bot.deactivateItem()
    else :
        if agent_pos is not None and entity_pos is not None and agent_pos.distanceTo(entity_pos) > 12 :
            go_to_position(agent, entity_pos.x, entity_pos.y, entity_pos.z, 10)
        agent.bot.activateItem()
        time.sleep(1)
        agent.bot.lookAt(entity_pos.offset(0, get_elevation(agent, entity), 0))
        time.sleep(2)
        agent.bot.deactivateItem()

def shoot_entity(agent, entity_name, kill = True) :
    """Shoot the entity if the bot is holding a 'bow' or a 'crossbow'; call with fight_entity(agent, entity)."""
    add_log(title = agent.pack_message("Shoot Entity"), content = "Use bow to fight \"%s\"." % entity_name, label = "plugin") 
    entities = list(filter(lambda et: entity_name in et.name, get_nearest_entities(agent, 32)))
    entity = entities[0] if len(entities) > 0 else None 
    if entity is not None :
        if held_bow(agent) :
            if agent.bot.modes is not None : 
                agent.bot.modes.pause('cowardice')
                if entity.name in ["drowned", "cod", "salmon", "tropical_fish", "squid"] :
                    agent.bot.modes.pause('self_preservation') 
            if agent.bot.usingHeldItem :
                agent.bot.deactivateItem()
                time.sleep(0.3)
            bow_fight(agent, entity)
            time.sleep(0.5)
            if kill == True :
                while any(et.id == entity.id for et in get_nearest_entities(agent, 32, 64)) and held_bow(agent) :
                    bow_fight(agent, entity)
                    time.sleep(0.5)
                if any(et.id == entity.id for et in get_nearest_entities(agent, 32, 64)) :
                    agent.bot.chat("I don't have enough arrows to kill \"%s\"." % get_entity_display_name(get_entity_id(entity_name)))
                else :
                    agent.bot.chat("I killed \"%s\"." % get_entity_display_name(get_entity_id(entity_name)))
        else :
            agent.bot.chat("I don't have any bow or crossbow.")
    else :
        agent.bot.chat("I can't find any %s to attack." % get_entity_display_name(get_entity_id(entity_name)))
        return False

class PluginInstance(Plugin) :
    def get_actions(self) :
        return [
            {
                "name" : 'shoot',
                "description" : 'Shoot the entity when the the bot has bow (or crossbow) and arrows in the inventory.',
                "params" : {
                    "entity_name": { "type" : "string", "description" : "The type of entity to attack."},
                    "kill" : {"type" : "bool", "description" : "Indicate if you want to kill the entity"},
                },
                "perform" : shoot_entity, 
            },
        ]
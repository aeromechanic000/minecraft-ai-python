"""
Bot Behavioral Modes System

This module implements reactive behavioral modes for Minecraft bots.
Modes run every tick to respond immediately to the world state,
such as self-preservation, combat, item collection, and environmental reactions.

Based on the JavaScript implementation from minecraft-ai.
"""

import math
import time
import asyncio
import threading
from utils import add_log

# Global agent reference (set by init_modes)
_agent = None


def say(agent, message):
    """Log mode behavior message."""
    if hasattr(agent.bot.modes, 'behavior_log'):
        agent.bot.modes.behavior_log += message + '\n'
    # Only narrate if setting is enabled
    if agent.bot.modes._narrate_behavior:
        agent.bot.chat(message)


async def execute(mode, agent, func, timeout=-1):
    """
    Execute a mode action without blocking the update loop.
    This runs the function asynchronously and handles interruption logic.
    """
    mode['active'] = True
    interrupted_action = agent.working_process
    interrupted_action_name = agent.current_action_name

    # If this mode interrupts 'all', stop any ongoing pathfinder movement
    if 'all' in mode.get('interrupts', []):
        try:
            if agent.bot.pathfinder and agent.bot.pathfinder.isMoving():
                agent.bot.pathfinder.stop()
        except Exception:
            pass

    try:
        # Run the function
        if asyncio.iscoroutinefunction(func):
            await func()
        else:
            func()
    except Exception as e:
        add_log(
            title=agent.pack_message(f"Mode {mode['name']} error."),
            content=f"Exception: {e}",
            label="warning"
        )
    finally:
        mode['active'] = False

    # Log completion
    add_log(
        title=agent.pack_message(f"Mode {mode['name']} finished."),
        content="",
        label="agent",
        print=False
    )


# --- Mode Update Functions ---

async def _update_self_preservation(agent, mode):
    """Respond to drowning, burning, and damage at low health."""
    bot = agent.bot

    from skills import get_nearest_block, go_to_position, move_away

    block = bot.blockAt(bot.entity.position) if bot.entity else None
    block_above = bot.blockAt(bot.entity.position.offset(0, 1, 0)) if bot.entity else None

    if not block:
        block = type('obj', (object,), {'name': 'air'})()
    if not block_above:
        block_above = type('obj', (object,), {'name': 'air'})()

    # Fall blocks
    fall_blocks = ['sand', 'gravel', 'concrete_powder']

    # In water - jump to surface
    if block_above.name in ['water', 'flowing_water']:
        if not bot.pathfinder.goal:
            bot.setControlState('jump', True)
        return

    # Falling blocks above
    if any(fb in block_above.name for fb in fall_blocks):
        await execute(mode, agent, lambda: move_away(agent, 2))
        return

    # On fire or in lava
    if block.name in ['lava', 'flowing_lava', 'fire'] or \
       block_above.name in ['lava', 'flowing_lava', 'fire']:
        say(agent, "I'm on fire!")
        async def fire_action():
            water = get_nearest_block(agent, 'water', 20)
            if water:
                pos = water.position
                go_to_position(agent, pos.x, pos.y, pos.z, 0.2)
                say(agent, "Ahhhh that's better!")
            else:
                move_away(agent, 5)
        await execute(mode, agent, fire_action)
        return

    # Low health from recent damage
    current_time = time.time() * 1000
    if hasattr(bot, 'lastDamageTime') and bot.lastDamageTime is not None and current_time - bot.lastDamageTime < 3000:
        if bot.health < 5 or (hasattr(bot, 'lastDamageTaken') and bot.lastDamageTaken is not None and bot.lastDamageTaken >= bot.health):
            say(agent, "I'm dying!")
            await execute(mode, agent, lambda: move_away(agent, 20))
            return

    # Clear controls if idle
    if agent.current_goal is None and agent.working_process is None:
        bot.clearControlStates()


async def _update_unstuck(agent, mode):
    """Attempt to get unstuck when in the same place for a while."""
    # Don't get stuck when idle
    if agent.current_goal is None and agent.working_process is None:
        mode['prev_location'] = None
        mode['stuck_time'] = 0
        return

    bot = agent.bot
    current_time = time.time()

    # Initialize mode state - use .get() for safety
    if mode.get('prev_location') is None and 'prev_location' not in mode:
        mode['prev_location'] = None
        mode['stuck_time'] = 0
        mode['last_time'] = current_time
        mode['prev_dig_block'] = None
        mode['distance'] = 2
        mode['max_stuck_time'] = 20

    cur_dig_block = bot.targetDigBlock if hasattr(bot, 'targetDigBlock') else None

    prev_dig_block = mode.get('prev_dig_block')
    if prev_dig_block is None and cur_dig_block:
        mode['prev_dig_block'] = cur_dig_block

    # Check if stuck
    pos = bot.entity.position if bot.entity else None
    if pos:
        prev_location = mode.get('prev_location')
        distance = mode.get('distance', 2)
        if prev_location and prev_location.distanceTo(pos) < distance and \
           str(cur_dig_block) == str(prev_dig_block):
            mode['stuck_time'] = mode.get('stuck_time', 0) + (current_time - mode.get('last_time', current_time))
        else:
            mode['prev_location'] = pos.clone() if hasattr(pos, 'clone') else pos
            mode['stuck_time'] = 0
            mode['prev_dig_block'] = None

    # If stuck too long
    max_stuck_time = mode.get('max_stuck_time', 20)
    if mode.get('stuck_time', 0) > max_stuck_time:
        say(agent, "I'm stuck!")
        mode['stuck_time'] = 0
        from skills import move_away
        await execute(mode, agent, lambda: move_away(agent, 5))
        say(agent, "I'm free.")

    mode['last_time'] = current_time


async def _update_cowardice(agent, mode):
    """Run away from enemies."""
    from skills import get_nearest_entities, get_entity_position

    hostile_types = [
        'zombie', 'skeleton', 'spider', 'creeper', 'enderman',
        'witch', 'phantom', 'drowned', 'husk', 'stray',
        'cave_spider', 'blaze', 'ghast', 'magma_cube',
        'silverfish', 'endermite', 'guardian', 'elder_guardian',
        'shulker', 'vindicator', 'vex', 'evoker', 'pillager',
        'ravager', 'hoglin', 'zoglin', 'piglin_brute',
        'warden', 'breeze'
    ]

    entities = get_nearest_entities(agent, max_distance=16, count=8)
    nearest_hostile = None

    for entity in entities:
        if any(h in entity.name.lower() for h in hostile_types):
            nearest_hostile = entity
            break

    if nearest_hostile:
        say(agent, f"Aaa! A {nearest_hostile.name.replace('_', ' ')}!")
        from skills import move_away
        await execute(mode, agent, lambda: move_away(agent, 24))


async def _update_self_defense(agent, mode):
    """Attack nearby enemies."""
    from skills import get_nearest_entities, attack_entity, equip_highest_attack

    hostile_types = [
        'zombie', 'skeleton', 'spider', 'creeper', 'enderman',
        'witch', 'phantom', 'drowned', 'husk', 'stray',
        'cave_spider', 'blaze', 'ghast', 'magma_cube',
        'silverfish', 'endermite', 'guardian', 'elder_guardian',
        'shulker', 'vindicator', 'vex', 'evoker', 'pillager',
        'ravager', 'hoglin', 'zoglin', 'piglin_brute',
        'warden', 'breeze'
    ]

    entities = get_nearest_entities(agent, max_distance=8, count=8)
    nearest_hostile = None

    for entity in entities:
        if any(h in entity.name.lower() for h in hostile_types):
            nearest_hostile = entity
            break

    if nearest_hostile:
        say(agent, f"Fighting {nearest_hostile.name}!")
        async def defend():
            equip_highest_attack(agent)
            agent.bot.lookAt(nearest_hostile.position)
            agent.bot.attack(nearest_hostile)
        await execute(mode, agent, defend)


def _update_cheat(agent, mode):
    """Cheat mode - no update needed, just a flag."""
    pass


# --- Mode Definitions ---

MODES_LIST = [
    {
        'name': 'self_preservation',
        'description': 'Respond to drowning, burning, and damage at low health. Interrupts all actions.',
        'interrupts': ['all'],
        'on': True,
        'active': False,
        'paused': False,
        'update': _update_self_preservation,
    },
    {
        'name': 'unstuck',
        'description': 'Attempt to get unstuck when in the same place for a while. Interrupts all actions.',
        'interrupts': ['all'],
        'on': True,
        'active': False,
        'paused': False,
        'update': _update_unstuck,
    },
    {
        'name': 'cowardice',
        'description': 'Run away from enemies. Interrupts all actions.',
        'interrupts': ['all'],
        'on': False,  # OFF by default - bots will fight (self_defense), not flee
        'active': False,
        'paused': False,
        'update': _update_cowardice,
    },
    {
        'name': 'self_defense',
        'description': 'Attack nearby enemies. Interrupts all actions.',
        'interrupts': ['all'],
        'on': True,
        'active': False,
        'paused': False,
        'update': _update_self_defense,
    },
    {
        'name': 'cheat',
        'description': 'Use cheats to instantly place blocks and teleport.',
        'interrupts': [],
        'on': False,
        'active': False,
        'paused': False,
        'update': _update_cheat,
    },
]

MODES_MAP = {mode['name']: mode for mode in MODES_LIST}


class ModeController:
    """
    Manages behavioral modes for a bot.
    Security: Must not store references to external objects like agent.
    """

    def __init__(self):
        self.behavior_log = ''
        self._narrate_behavior = True

    def _apply_pending_changes(self):
        """Check for and apply pending mode changes from web monitor."""
        try:
            from monitor.server import get_pending_mode_changes
            global _agent
            if _agent is None:
                return
            changes = get_pending_mode_changes(_agent.configs.get("username", ""))
            for mode_name, is_on in changes.items():
                if mode_name in MODES_MAP:
                    MODES_MAP[mode_name]['on'] = is_on
                    add_log(
                        title=_agent.pack_message(f"Mode {mode_name} changed via web monitor."),
                        content=f"{'ON' if is_on else 'OFF'}",
                        label="agent"
                    )
        except ImportError:
            # Monitor module not available
            pass
        except Exception as e:
            add_log(
                title="Failed to apply pending mode changes.",
                content=f"Exception: {e}",
                label="warning",
                print=False
            )

    def exists(self, mode_name):
        return mode_name in MODES_MAP

    def setOn(self, mode_name, on):
        if mode_name in MODES_MAP:
            MODES_MAP[mode_name]['on'] = on

    def isOn(self, mode_name):
        if mode_name not in MODES_MAP:
            return False
        mode = MODES_MAP[mode_name]
        return mode['on'] and not mode['paused']

    def pause(self, mode_name):
        if mode_name in MODES_MAP:
            MODES_MAP[mode_name]['paused'] = True

    def unpause(self, mode_name):
        if mode_name in MODES_MAP:
            MODES_MAP[mode_name]['paused'] = False

    def unPauseAll(self):
        for mode in MODES_LIST:
            if mode['paused']:
                add_log(title="Unpausing mode", content=mode['name'], label="agent", print=False)
            mode['paused'] = False

    def getMiniDocs(self):
        res = 'Agent Modes:'
        for mode in MODES_LIST:
            on = 'ON' if mode['on'] else 'OFF'
            res += f"\n- {mode['name']}({on})"
        return res

    def getDocs(self):
        res = 'Agent Modes:'
        for mode in MODES_LIST:
            on = 'ON' if mode['on'] else 'OFF'
            res += f"\n- {mode['name']}({on}): {mode['description']}"
        return res

    def update(self):
        """Update all modes. Called every tick."""
        global _agent
        if _agent is None:
            return

        # Check for pending mode changes from web monitor
        self._apply_pending_changes()

        # Unpause all when idle
        if _agent.current_goal is None and _agent.working_process is None:
            self.unPauseAll()

        # Get current action for interrupt checking
        # Use current_action_name which stores the actual action name (e.g., "go_to_player")
        # instead of working_process which is a random label
        current_action = None
        if _agent.current_action_name:
            current_action = f"action:{_agent.current_action_name}"

        # Run mode updates
        for mode in MODES_LIST:
            # Check if mode can run
            interruptible = 'all' in mode['interrupts'] or current_action in mode['interrupts']
            is_idle = _agent.current_goal is None and _agent.working_process is None

            if mode['on'] and not mode['paused'] and not mode['active'] and (is_idle or interruptible):
                try:
                    update_func = mode['update']
                    if asyncio.iscoroutinefunction(update_func):
                        # Run async function in event loop
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(update_func(_agent, mode))
                            else:
                                loop.run_until_complete(update_func(_agent, mode))
                        except RuntimeError:
                            # No event loop, create one
                            asyncio.run(update_func(_agent, mode))
                    else:
                        update_func(_agent, mode)
                except Exception as e:
                    add_log(
                        title=_agent.pack_message(f"Mode {mode['name']} error."),
                        content=f"Exception: {e}",
                        label="warning"
                    )

            # Stop if a mode is active
            if mode['active']:
                break

    def flushBehaviorLog(self):
        log = self.behavior_log
        self.behavior_log = ''
        return log

    def getJson(self):
        return {mode['name']: mode['on'] for mode in MODES_LIST}

    def loadJson(self, data):
        for mode in MODES_LIST:
            if mode['name'] in data:
                mode['on'] = data[mode['name']]


def init_modes(agent):
    """
    Initialize behavioral modes for an agent.

    Args:
        agent: The Agent instance to attach modes to

    Returns:
        ModeController: The initialized mode controller
    """
    global _agent
    _agent = agent

    controller = ModeController()

    # Load mode settings from profile if present
    modes_config = agent.configs.get('modes', {})
    if modes_config:
        controller.loadJson(modes_config)

    add_log(
        title=agent.pack_message("Initialized behavioral modes."),
        content=controller.getDocs(),
        label="agent"
    )

    return controller

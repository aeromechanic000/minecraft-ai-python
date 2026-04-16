"""
Cerebellum Module

High-frequency rule-based reflex module.
- Runs at fixed frequency (every tick_interval_ms)
- Pure rule-based logic - NO LLM calls
- Reads from StateBuffer
- Submits reflex actions to ActionExecutor
- Each reflex has its own 'interrupts' config (like modes.py)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable, Dict, Any
from enum import Enum, auto
import math
import time

from state_buffer import AgentState
from executor import ActionExecutor, ActionRequest, ActionSource
from utils import add_log

# Blocks that don't stop falling (for ground detection during water bucket clutch)
_NON_SOLID_BLOCKS = frozenset({
    'air', 'cave_air', 'void_air',
    'water', 'flowing_water', 'lava', 'flowing_lava',
    'grass', 'tall_grass', 'fern', 'large_fern',
    'seagrass', 'tall_seagrass', 'kelp', 'kelp_plant',
    'dead_bush', 'dandelion', 'poppy', 'blue_orchid', 'allium',
    'azure_bluet', 'red_tulip', 'orange_tulip', 'white_tulip',
    'pink_tulip', 'oxeye_daisy', 'cornflower', 'lily_of_the_valley',
    'wither_rose', 'sunflower', 'rose_bush', 'lilac', 'peony',
    'torch', 'wall_torch', 'soul_torch', 'soul_wall_torch',
    'oak_sign', 'spruce_sign', 'birch_sign', 'jungle_sign',
    'acacia_sign', 'dark_oak_sign', 'mangrove_sign', 'cherry_sign',
    'bamboo_sign', 'crimson_sign', 'warped_sign',
    'sugar_cane', 'vine', 'lily_pad', 'snow',
    'wheat', 'carrots', 'potatoes', 'beetroots',
    'oak_sapling', 'spruce_sapling', 'birch_sapling',
    'jungle_sapling', 'acacia_sapling', 'dark_oak_sapling',
    'nether_wart', 'warped_fungus', 'crimson_fungus',
    'redstone_wire', 'tripwire',
})

# Blocks that negate or reduce fall damage (safe to land on)
_SAFE_LANDING_BLOCKS = frozenset({
    'water', 'flowing_water', 'slime_block', 'hay_block',
    'cobweb', 'powder_snow', 'honey_block',
})


class ReflexType(Enum):
    """Types of reflexive responses."""
    EMERGENCY = auto()      # Immediate life-threatening (fire, lava, drowning)
    DEFENSIVE = auto()      # Self-defense (attacked, hostile nearby)
    REACTIVE = auto()       # Reactive (stuck)


@dataclass
class ReflexRule:
    """A single reflex rule: condition -> action."""
    name: str
    condition: Callable[[AgentState], bool]
    action_generator: Callable  # Returns ActionRequest
    reflex_type: ReflexType
    cooldown_ms: int = 0
    last_triggered: float = 0
    interrupts: List[str] = field(default_factory=list)  # ['all'] = interrupt any, [] = only when idle


class Cerebellum:
    """Rule-based reflex module that runs every tick."""

    def __init__(self, agent, state_buffer, executor: ActionExecutor):
        self.agent = agent
        self.state_buffer = state_buffer
        self.executor = executor

        # Mode settings from profile
        self.modes_config = agent.configs.get('modes', {})

        # Cerebellum-specific config
        cerebellum_config = agent.configs.get('cerebellum', {})
        self._narrate_behavior = cerebellum_config.get('narrate_behavior', False)

        # Track recently attacked entities to prevent repeated attacks
        # Format: {entity_id: last_attack_time}
        self._recently_attacked: Dict[int, float] = {}
        self._attack_cooldown_seconds = 5.0  # Don't re-attack same entity for 5 seconds

        # Build reflex rules
        self._reflex_rules: List[ReflexRule] = self._build_reflex_rules()

        # Fall survival (water bucket clutch)
        # Reads from 'modes' config in profile: {"modes": {"high_jump": true}}
        if self.modes_config.get('high_jump', True):
            self._fall_state = {
                'falling': False,
                'clutch_performed': False,
                'start_y': None,
                'water_picked_up': False,
            }
            self._vec3_cache = None
            self._register_fall_handler()

    def _build_reflex_rules(self) -> List[ReflexRule]:
        """Build all reflex rules from mode configurations."""
        rules = []

        # Self-preservation rules (EMERGENCY) - can interrupt any action
        if self.modes_config.get('self_preservation', True):
            rules.extend([
                ReflexRule(
                    name="escape_fire",
                    condition=lambda s: s.is_on_fire or s.block_at_feet in ['fire', 'lava'],
                    action_generator=lambda: self._create_move_away_action("escape_fire"),
                    reflex_type=ReflexType.EMERGENCY,
                    cooldown_ms=100,
                    interrupts=['all']  # Can interrupt any action
                ),
                ReflexRule(
                    name="escape_lava",
                    condition=lambda s: s.block_at_feet in ['lava', 'flowing_lava'],
                    action_generator=lambda: self._create_move_away_action("escape_lava"),
                    reflex_type=ReflexType.EMERGENCY,
                    cooldown_ms=100,
                    interrupts=['all']
                ),
                ReflexRule(
                    name="surface_water",
                    condition=lambda s: s.is_in_water and s.health < 20,
                    action_generator=lambda: self._create_surface_action(),
                    reflex_type=ReflexType.EMERGENCY,
                    cooldown_ms=200,
                    interrupts=['all']
                ),
            ])

        # Self-defense rules (DEFENSIVE) - can interrupt any action
        if self.modes_config.get('self_defense', True):
            # Use longer cooldown for self_defense mode to prevent spam
            attack_cooldown_ms = 8000 if self.modes_config.get('self_defense', True) else 5000
            rules.append(ReflexRule(
                name="attack_hostile",
                condition=lambda s: s.nearest_hostile is not None,
                action_generator=lambda: self._create_attack_action(),
                reflex_type=ReflexType.DEFENSIVE,
                cooldown_ms=attack_cooldown_ms,
                interrupts=['all']
            ))

        # Cowardice rules (DEFENSIVE) - can interrupt any action
        if self.modes_config.get('cowardice', False):
            # Use longer cooldown to prevent spam
            flee_cooldown_ms = 5000
            rules.append(ReflexRule(
                name="flee_hostile",
                condition=lambda s: s.nearest_hostile is not None,
                action_generator=lambda: self._create_flee_action(),
                reflex_type=ReflexType.DEFENSIVE,
                cooldown_ms=flee_cooldown_ms,
                interrupts=['all']
            ))

        # Unstuck rules (REACTIVE) - can interrupt any action
        if self.modes_config.get('unstuck', True):
            rules.append(ReflexRule(
                name="get_unstuck",
                condition=lambda s: s.is_stuck and s.is_moving,
                action_generator=lambda: self._create_unstuck_action(),
                reflex_type=ReflexType.REACTIVE,
                cooldown_ms=5000,
                interrupts=['all']
            ))

        return rules

    def _create_move_away_action(self, reason: str) -> ActionRequest:
        """Create action to move away from danger."""
        from skills import move_away
        return ActionRequest(
            name=reason,
            perform=move_away,
            params={"agent": self.agent, "distance": 10},
            source=ActionSource.CEREBELLUM_REFLEX
        )

    def _create_surface_action(self) -> ActionRequest:
        """Create action to surface from water."""
        from skills import go_to_position
        pos = self.state_buffer.read().position
        return ActionRequest(
            name="surface",
            perform=go_to_position,
            params={"agent": self.agent, "x": pos["x"], "y": pos["y"] + 5, "z": pos["z"], "closeness": 1},
            source=ActionSource.CEREBELLUM_REFLEX
        )

    def _create_attack_action(self) -> ActionRequest:
        """Create action to attack nearest hostile."""
        from skills import attack_entity, equip_highest_attack, get_nearest_entities

        # Hostile entity types (must match _sense_state in agent.py)
        HOSTILE_TYPES = [
            'zombie', 'skeleton', 'spider', 'creeper', 'enderman',
            'witch', 'phantom', 'drowned', 'husk', 'stray',
            'cave_spider', 'blaze', 'ghast', 'magma_cube',
            'silverfish', 'endermite', 'guardian', 'elder_guardian',
            'shulker', 'vindicator', 'vex', 'evoker', 'pillager',
            'ravager', 'hoglin', 'zoglin', 'piglin_brute',
            'warden', 'breeze', 'slime'
        ]

        # Capture self reference for use in closure
        cerebellum = self

        def perform_attack(**kwargs):
            agent = kwargs["agent"]
            entities = get_nearest_entities(agent, max_distance=8, count=16)
            current_time = time.time()

            # Clean up old entries from recently_attacked
            cerebellum._recently_attacked = {
                eid: t for eid, t in cerebellum._recently_attacked.items()
                if current_time - t < cerebellum._attack_cooldown_seconds
            }

            # Find the nearest HOSTILE entity (not players!)
            nearest_hostile = None
            for entity in entities:
                if any(h in entity.name.lower() for h in HOSTILE_TYPES):
                    # Skip if we recently attacked this entity
                    if entity.id in cerebellum._recently_attacked:
                        continue
                    nearest_hostile = entity
                    break

            if nearest_hostile is None:
                # No valid hostile entity found
                return None

            # Verify entity is still alive (has valid position)
            try:
                entity_pos = getattr(nearest_hostile, 'position', None)
                if entity_pos is None:
                    add_log(
                        title=agent.pack_message("Attack skipped"),
                        content=f"Entity {nearest_hostile.name} has no valid position",
                        label="action",
                        print=False
                    )
                    return None
            except Exception as e:
                add_log(
                    title=agent.pack_message("Attack skipped"),
                    content=f"Entity validation failed: {e}",
                    label="action",
                    print=False
                )
                return None

            # Mark this entity as recently attacked
            cerebellum._recently_attacked[nearest_hostile.id] = current_time

            equip_highest_attack(agent)
            result = attack_entity(agent, nearest_hostile, kill=True)

            # Log completion instead of narrating
            add_log(
                title=agent.pack_message("Attack complete"),
                content=f"Finished attacking {nearest_hostile.name}",
                label="action",
                print=cerebellum._narrate_behavior
            )

            return result

        return ActionRequest(
            name="attack_hostile",
            perform=perform_attack,
            params={"agent": self.agent},
            source=ActionSource.CEREBELLUM_REFLEX
        )

    def _create_flee_action(self) -> ActionRequest:
        """Create action to flee from hostile."""
        from skills import move_away
        return ActionRequest(
            name="flee_hostile",
            perform=move_away,
            params={"agent": self.agent, "distance": 16},
            source=ActionSource.CEREBELLUM_REFLEX
        )

    def _create_unstuck_action(self) -> ActionRequest:
        """Create action to get unstuck."""
        from skills import move_away
        return ActionRequest(
            name="get_unstuck",
            perform=move_away,
            params={"agent": self.agent, "distance": 3},
            source=ActionSource.CEREBELLUM_URGENT
        )

    def tick(self, can_interrupt: bool = True) -> None:
        """
        Execute one cerebellum tick.

        Reads state, evaluates rules, submits highest priority action to executor.
        Called every tick_interval_ms from the main tick handler.

        Args:
            can_interrupt: If True, reflexes with interrupts=['all'] can interrupt brain actions.
                          If False, all reflexes only run when executor is idle.
        """
        state = self.state_buffer.read()
        current_time = time.time() * 1000

        # Check if executor is busy with a reflex - don't submit duplicate
        if self.executor.is_busy:
            current = self.executor.current_action
            if current and current.source in [ActionSource.CEREBELLUM_REFLEX, ActionSource.CEREBELLUM_URGENT]:
                return  # Already executing a reflex

        # Evaluate rules in priority order (EMERGENCY > DEFENSIVE > REACTIVE)
        sorted_rules = sorted(self._reflex_rules, key=lambda r: r.reflex_type.value)

        for rule in sorted_rules:
            # Check cooldown
            if current_time - rule.last_triggered < rule.cooldown_ms:
                continue

            # Check condition
            try:
                if rule.condition(state):
                    # Check if this reflex can run based on interrupts config and executor state
                    can_run = self._can_run_reflex(rule, can_interrupt)

                    if not can_run:
                        continue  # Skip this rule, try next one

                    # Generate and submit action
                    action = rule.action_generator()

                    # Skip if action generator returned None (e.g., no valid target)
                    if action is None:
                        continue

                    # Interrupt current action if allowed
                    if can_interrupt and 'all' in rule.interrupts:
                        if self.executor.should_interrupt_current(action):
                            self.executor.interrupt_current()

                    self.executor.submit(action)
                    rule.last_triggered = current_time

                    # Only trigger one reflex per tick
                    break
            except Exception as e:
                add_log(
                    title=f"Cerebellum rule error: {rule.name}",
                    content=str(e),
                    label="warning"
                )

    def _can_run_reflex(self, rule: ReflexRule, can_interrupt: bool) -> bool:
        """
        Check if a reflex can run based on its interrupts config and current state.

        Logic (same as modes.py):
        - If executor is idle -> can always run
        - If executor is busy:
          - can_interrupt=False -> cannot run
          - can_interrupt=True:
            - interrupts=['all'] -> can interrupt any action
            - interrupts=[] -> only when idle (cannot interrupt)
            - interrupts=['action:xxx'] -> can interrupt specific action
        """
        if not self.executor.is_busy:
            return True  # Always can run when idle

        if not can_interrupt:
            return False  # Not allowed to interrupt

        # Check interrupts config
        if 'all' in rule.interrupts:
            return True  # Can interrupt any action

        if not rule.interrupts:
            return False  # Only runs when idle

        # Check specific action interrupts
        current_action = self.executor.current_action
        if current_action:
            action_interrupt_key = f"action:{current_action.name}"
            if action_interrupt_key in rule.interrupts:
                return True

        return False

    # --- Fall Survival (Water Bucket Clutch) ---

    def _register_fall_handler(self):
        """Register physicsTick handler for fall detection and water bucket clutch.

        The physicsTick event fires every game tick (~50ms), providing the
        timing resolution needed for the clutch maneuver.
        """
        from javascript import On

        @On(self.agent.bot, 'physicsTick')
        def handle_fall_physics(*args):
            self._check_fall_and_clutch()

    def _get_vec3(self):
        """Lazy-load and cache vec3 module."""
        if self._vec3_cache is None:
            from javascript import require
            self._vec3_cache = require('vec3')
        return self._vec3_cache

    def _check_fall_and_clutch(self):
        """Check for dangerous falls and perform water bucket clutch.

        Runs every physicsTick (~50ms) for fast response.
        Reads bot state directly (not from StateBuffer) for lowest latency.
        """
        bot = self.agent.bot

        # Safety: check entity and velocity exist
        if not bot.entity:
            return
        try:
            velocity = bot.entity.velocity
            if not velocity:
                return
            velocity_y = float(velocity.y)
            on_ground = bool(bot.entity.onGround) if hasattr(bot.entity, 'onGround') else False
        except Exception:
            return

        state = self._fall_state

        # Reset state when on ground
        if on_ground:
            if state.get('clutch_performed') and not state.get('water_picked_up'):
                self._pickup_water()
                state['water_picked_up'] = True
            state['falling'] = False
            state['clutch_performed'] = False
            state['start_y'] = None
            state['water_picked_up'] = False
            return

        # Not falling if velocity is near zero or positive
        if velocity_y >= -0.5:
            return

        # Mark as falling
        if not state.get('falling'):
            state['falling'] = True
            state['start_y'] = float(bot.entity.position.y)
            state['clutch_performed'] = False
            state['water_picked_up'] = False

        # Don't re-trigger if clutch already performed
        if state.get('clutch_performed'):
            return

        # Skip in creative mode (no fall damage)
        try:
            if bot.game and str(bot.game.gameMode) == 'creative':
                return
        except Exception:
            pass

        # Skip if in water, on ladder, vine, or scaffolding (already safe)
        try:
            feet_pos = bot.entity.position
            block_at_feet = bot.blockAt(feet_pos)
            if block_at_feet and block_at_feet.name in (
                'water', 'flowing_water', 'ladder', 'vine', 'scaffolding'
            ):
                return
        except Exception:
            pass

        # Find ground below
        ground_block = self._find_ground_block()
        if ground_block is None:
            return

        # Calculate distances
        pos = bot.entity.position
        current_y = float(pos.y)
        ground_top_y = float(ground_block.position.y) + 1  # Top face of the block
        distance_to_ground = current_y - ground_top_y
        fall_distance = (state.get('start_y') or current_y) - ground_top_y

        # Only clutch if fall would be damaging (> 3 blocks)
        if fall_distance <= 3:
            return

        # Check if ground is a safe landing block (water, slime, hay bale, etc.)
        try:
            landing_block = bot.blockAt(ground_block.position.offset(0, 1, 0))
            if landing_block and landing_block.name in _SAFE_LANDING_BLOCKS:
                return  # Safe landing, no clutch needed
        except Exception:
            pass

        # Trigger clutch when close enough to ground
        # Scale trigger distance with velocity: faster fall = trigger earlier
        trigger_distance = max(3, min(6, abs(velocity_y) * 2))
        if distance_to_ground <= trigger_distance:
            add_log(
                title=self.agent.pack_message("[Clutch] Fall detected!"),
                content=f"Fall: {fall_distance:.1f} blocks, "
                        f"Distance to ground: {distance_to_ground:.1f}, "
                        f"Velocity: {velocity_y:.2f} b/t",
                label="action"
            )
            self._perform_clutch(ground_block)
            state['clutch_performed'] = True

    def _find_ground_block(self):
        """Find the first solid block below the bot's position.

        Returns the block object or None.
        """
        vec3 = self._get_vec3()
        bot = self.agent.bot
        pos = bot.entity.position
        if not pos:
            return None

        x = math.floor(float(pos.x))
        z = math.floor(float(pos.z))
        start_y = math.floor(float(pos.y))

        # Check up to 40 blocks below
        for y in range(start_y - 1, max(start_y - 40, -64), -1):
            try:
                block = bot.blockAt(vec3.Vec3(x, y, z))
                if block and block.name not in _NON_SOLID_BLOCKS:
                    return block
            except Exception:
                continue
        return None

    def _perform_clutch(self, ground_block):
        """Perform the water bucket clutch to survive a fall.

        Sequence: look down -> equip water bucket -> place water on ground.
        Uses activateBlock for the water placement (right-click with bucket).
        """
        vec3 = self._get_vec3()
        bot = self.agent.bot

        # Check dimension for appropriate item
        dimension = ''
        try:
            dimension = str(bot.game.dimension) if bot.game else ''
        except Exception:
            pass
        is_nether = 'nether' in dimension

        # Find appropriate bucket
        bucket_item = None
        bucket_name = 'water_bucket'

        if is_nether:
            # In nether, water evaporates - use powder snow bucket instead
            bucket_item = self._find_inventory_item('powder_snow_bucket')
            if bucket_item:
                bucket_name = 'powder_snow_bucket'

        if bucket_item is None:
            bucket_item = self._find_inventory_item('water_bucket')

        if bucket_item is None:
            add_log(
                title=self.agent.pack_message("[Clutch] No water bucket!"),
                content="Falling without protection",
                label="warning"
            )
            if self._narrate_behavior:
                try:
                    bot.chat("Ahhhh! No water bucket!")
                except Exception:
                    pass
            return

        try:
            # 1. Look straight down immediately (force=True for instant)
            yaw = float(bot.entity.yaw)
            bot.look(yaw, math.pi / 2, True)

            # 2. Equip the water bucket to main hand
            bot.equip(bucket_item, 'hand')

            # 3. Place water - try activateBlock first (uses our look direction)
            # activateBlock sends a block_place packet targeting the face
            # our look vector intersects (top face, since we look straight down)
            bot.activateBlock(ground_block)

            add_log(
                title=self.agent.pack_message("[Clutch] Water placed!"),
                content=f"Used: {bucket_name}",
                label="success"
            )
            if self._narrate_behavior:
                try:
                    bot.chat("Water bucket clutch!")
                except Exception:
                    pass

        except Exception as e:
            # Fallback: try placeBlock with explicit face vector
            add_log(
                title=self.agent.pack_message("[Clutch] activateBlock failed, trying placeBlock"),
                content=f"Exception: {e}",
                label="warning"
            )
            try:
                bot.placeBlock(ground_block, vec3.Vec3(0, 1, 0))
                add_log(
                    title=self.agent.pack_message("[Clutch] placeBlock succeeded"),
                    label="success"
                )
            except Exception as e2:
                add_log(
                    title=self.agent.pack_message("[Clutch] Failed to place water"),
                    content=f"Exception: {e2}",
                    label="error"
                )

    def _pickup_water(self):
        """Pick up placed water after landing safely.

        Called when the bot is on the ground after performing a clutch.
        Uses an empty bucket to pick up the water block at the bot's feet.
        """
        vec3 = self._get_vec3()
        bot = self.agent.bot

        try:
            # Find empty bucket in inventory
            empty_bucket = self._find_inventory_item('bucket')
            if empty_bucket is None:
                return

            # Look down at the water
            yaw = float(bot.entity.yaw)
            bot.look(yaw, math.pi / 2, True)

            # Equip empty bucket
            bot.equip(empty_bucket, 'hand')

            # Find water block at feet
            pos = bot.entity.position
            if not pos:
                return

            block_below = bot.blockAt(vec3.Vec3(
                math.floor(float(pos.x)),
                math.floor(float(pos.y)) - 1,
                math.floor(float(pos.z))
            ))

            if block_below and block_below.name in ('water', 'flowing_water'):
                bot.activateBlock(block_below)
                add_log(
                    title=self.agent.pack_message("[Clutch] Water picked up"),
                    label="action"
                )
                if self._narrate_behavior:
                    try:
                        bot.chat("Picked up the water.")
                    except Exception:
                        pass
        except Exception as e:
            add_log(
                title=self.agent.pack_message("[Clutch] Failed to pick up water"),
                content=f"Exception: {e}",
                label="warning",
                print=False
            )

    def _find_inventory_item(self, item_name):
        """Find an item in inventory by exact name."""
        bot = self.agent.bot
        try:
            for item in bot.inventory.items():
                if item and item.name == item_name:
                    return item
        except Exception:
            pass
        return None

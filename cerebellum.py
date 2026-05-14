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

        # Always register JS-level kick logger to capture actual kick reasons.
        # JSPyBridge can't extract ChatMessage properties in the Python kicked handler,
        # so we intercept at the JS level and log via our Python callback.
        self._setup_js_kick_logger()

        # Fall survival (water bucket clutch)
        # Runs entirely in JavaScript to avoid JSPyBridge deadlocks.
        # Python→JS calls from within a JS→Python physicsTick callback deadlock,
        # and deferring to the regular tick loop is too slow (~1s vs ~90ms to impact).
        if self.modes_config.get('high_jump', True):
            self._setup_js_fall_clutch()

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

    # --- Kick Reason Logger (JS-level) ---

    _KICK_LOGGER_JS = r'''
function(bot, logFn) {
    function log(msg) { try { logFn(msg); } catch(e) {} }

    function extractReason(packet) {
        var r = packet.reason;
        if (!r) return '(empty)';
        if (typeof r === 'string') return r;

        // Collect all string values from the object tree (handles NBT chat components)
        var parts = [];
        var seen = new Set();
        function walk(obj, depth) {
            if (depth > 6 || !obj || typeof obj !== 'object') return;
            try { if (seen.has(obj)) return; seen.add(obj); } catch(e) { return; }
            try {
                var keys = Object.keys(obj);
                for (var i = 0; i < keys.length; i++) {
                    var v = obj[keys[i]];
                    if (typeof v === 'string' && v.length > 0) {
                        parts.push(keys[i] + '=' + v);
                    } else if (typeof v === 'object' && v !== null) {
                        walk(v, depth + 1);
                    }
                }
            } catch(e) {}
        }

        // Check common ChatMessage properties first
        if (typeof r.text === 'string' && r.text) return r.text;
        if (typeof r.value === 'string' && r.value) return r.value;
        try { var s = r.toString(); if (s && typeof s === 'string' && s !== '[object Object]') return s; } catch(e) {}

        // Walk the tree for all string values
        walk(r, 0);
        if (parts.length > 0) return parts.join(', ');

        // Last resort: JSON dump
        try { var j = JSON.stringify(r); if (j && j !== '{}') return j; } catch(e) {}

        return '(unextractable)';
    }

    bot._client.on('kick_disconnect', function(packet) {
        log('[Kick] kick_disconnect reason: ' + extractReason(packet));
    });
    bot._client.on('disconnect', function(packet) {
        log('[Kick] disconnect reason: ' + extractReason(packet));
    });
}
'''

    def _setup_js_kick_logger(self):
        """Register JS-level listeners for kick events to extract actual reasons.

        JSPyBridge proxies ChatMessage objects to Python as opaque references,
        making it impossible to extract the kick reason in the Python handler.
        This JS-level listener reads the raw packet.reason and converts it to
        a plain string before logging it via the Python callback.
        """
        from javascript import require

        def log_callback(message):
            add_log(
                title=self.agent.pack_message(message),
                label="warning"
            )

        try:
            vm = require('vm')
            setup_fn = vm.runInThisContext('(' + self._KICK_LOGGER_JS + ')')
            setup_fn(self.agent.bot, log_callback)
        except Exception as e:
            add_log(
                title=self.agent.pack_message("[KickLogger] Failed to register"),
                content=f"Exception: {e}",
                label="error"
            )

    # --- Fall Survival (Water Bucket Clutch) ---

    # JavaScript fall clutch handler — embedded to avoid standalone .js files.
    # Evaluated via vm.runInThisContext() at runtime.
    #
    # CRITICAL TIMING NOTES:
    # mineflayer's physics loop per tick:
    #   1. physics.simulatePlayer() — updates bot.entity.position/velocity
    #   2. bot.emit('physicsTick')  — our handler runs here
    #   3. updatePosition()         — sends position+look packet to server
    #      └─ emits 'move' event AFTER the packet is written
    #
    # bot.look(force=true) does NOT send a packet — it only updates internal state.
    # The actual look packet is sent by updatePosition() in step 3.
    # bot.placeBlock() hangs forever in 1.21.1 because it awaits a lookAck that
    # never arrives (the server doesn't send look ACKs in modern versions).
    #
    # Strategy:
    #   Phase 1 (fall start): pre-equip bucket + look down (state update only).
    #   Phase 2 (within reach): defer block_place to the 'move' event so it
    #     fires AFTER updatePosition sends the position+look packet. This
    #     ensures the server has the correct position (within reach) and look
    #     direction (looking down) when it validates the block placement.
    _FALL_CLUTCH_JS = r'''
function(bot, logFn, Vec3) {
    var NON_SOLID = new Set([
        'air','cave_air','void_air',
        'water','flowing_water','lava','flowing_lava',
        'grass','tall_grass','fern','large_fern',
        'seagrass','tall_seagrass','kelp','kelp_plant',
        'dead_bush','dandelion','poppy','blue_orchid','allium',
        'azure_bluet','red_tulip','orange_tulip','white_tulip',
        'pink_tulip','oxeye_daisy','cornflower','lily_of_the_valley',
        'wither_rose','sunflower','rose_bush','lilac','peony',
        'torch','wall_torch','soul_torch','soul_wall_torch',
        'oak_sign','spruce_sign','birch_sign','jungle_sign',
        'acacia_sign','dark_oak_sign','mangrove_sign','cherry_sign',
        'bamboo_sign','crimson_sign','warped_sign',
        'sugar_cane','vine','lily_pad','snow',
        'wheat','carrots','potatoes','beetroots',
        'oak_sapling','spruce_sapling','birch_sapling',
        'jungle_sapling','acacia_sapling','dark_oak_sapling',
        'nether_wart','warped_fungus','crimson_fungus',
        'redstone_wire','tripwire',
    ]);

    var SAFE_LAND = new Set([
        'water','flowing_water','slime_block','hay_block',
        'cobweb','powder_snow','honey_block',
    ]);

    var UP = new Vec3(0, 1, 0);
    var st = { falling:false, done:false, y0:null, picked:false, equipped:false };
    var pendingClutch = null;

    function log(msg) { try { logFn(msg); } catch(e) {} }

    function findItem(name) {
        var items = bot.inventory.items();
        for (var i = 0; i < items.length; i++)
            if (items[i] && items[i].name === name) return items[i];
        return null;
    }

    function findItemInHotbar(name) {
        for (var slot = 36; slot <= 44; slot++) {
            var item = bot.inventory.slots[slot];
            if (item && item.name === name) return slot - 36;
        }
        return -1;
    }

    function findGround() {
        var pos = bot.entity.position;
        var x = Math.floor(pos.x), z = Math.floor(pos.z), sy = Math.floor(pos.y);
        for (var y = sy - 1; y > Math.max(sy - 40, -64); y--) {
            try {
                var b = bot.blockAt(new Vec3(x, y, z));
                if (b && !NON_SOLID.has(b.name)) return b;
            } catch(e) {}
        }
        return null;
    }

    function preEquip() {
        var nether = bot.game && bot.game.dimension && bot.game.dimension.indexOf('nether') >= 0;
        var bucketName = nether ? 'powder_snow_bucket' : 'water_bucket';
        var bucket = findItem(bucketName);
        if (!bucket && nether) bucket = findItem('water_bucket');
        if (bucket) {
            bot.equip(bucket, 'hand', function(err) {
                if (!err) {
                    st.equipped = true;
                    log('[Clutch] Pre-equipped ' + bucketName);
                }
            });
        }
        // Look down immediately. bot.look(force=true) only updates internal state;
        // the actual look packet is sent by the next updatePosition() call.
        bot.look(bot.entity.yaw, -Math.PI / 2, true);
    }

    function pickup() {
        var eb = findItem('bucket');
        if (!eb) return;
        try {
            bot.look(bot.entity.yaw, -Math.PI / 2, true);
            var hotbarSlot = findItemInHotbar('bucket');
            if (hotbarSlot >= 0) {
                bot.setQuickBarSlot(hotbarSlot);
                var p = bot.entity.position;
                var bl = bot.blockAt(new Vec3(Math.floor(p.x), Math.floor(p.y)-1, Math.floor(p.z)));
                if (bl && (bl.name === 'water' || bl.name === 'flowing_water')) {
                    bot.activateBlock(bl);
                    log('[Clutch] Water picked up');
                }
            } else {
                bot.equip(eb, 'hand', function(err) {
                    if (err) return;
                    var p = bot.entity.position;
                    var bl = bot.blockAt(new Vec3(Math.floor(p.x), Math.floor(p.y)-1, Math.floor(p.z)));
                    if (bl && (bl.name === 'water' || bl.name === 'flowing_water')) {
                        bot.activateBlock(bl);
                        log('[Clutch] Water picked up');
                    }
                });
            }
        } catch(e) {}
    }

    // Execute the clutch after the current physics tick completes.
    // Using setTimeout(0) defers the block_place to the next event loop
    // iteration, which is AFTER updatePosition sends the position+look
    // packet. This avoids sending packets inside updatePosition's event
    // handler and ensures the server has the correct state.
    bot.on('physicsTick', function() {
        if (!bot.entity) return;
        var v = bot.entity.velocity;
        if (!v) return;
        var vy = v.y;
        var onG = bot.entity.onGround;

        if (onG) {
            pendingClutch = null;
            if (st.done && !st.picked) { pickup(); st.picked = true; }
            st.falling = false; st.done = false; st.y0 = null;
            st.picked = false; st.equipped = false;
            return;
        }
        if (vy >= -0.05) return;

        if (!st.falling) {
            st.falling = true; st.y0 = bot.entity.position.y;
            st.done = false; st.picked = false; st.equipped = false;
            st.clutching = false;
            preEquip();
        }
        if (st.done) return;

        // Look down and attempt water placement EVERY tick from fall start.
        // Early attempts are rejected by the server (out of reach) but
        // the bot is instantly ready the moment it's close enough.
        // This maximizes the ~1-2 tick window at normal fall speed.
        bot.look(bot.entity.yaw, -Math.PI / 2, true);

        if (bot.game && bot.game.gameMode === 'creative') return;

        try {
            var fb = bot.blockAt(bot.entity.position);
            if (fb && (fb.name==='water'||fb.name==='flowing_water'||fb.name==='ladder'||fb.name==='vine'||fb.name==='scaffolding')) return;
        } catch(e) {}

        var g = findGround();
        if (!g) return;

        var cy = bot.entity.position.y;
        var gy = g.position.y + 1;
        var dg = cy - gy;
        var fd = (st.y0 || cy) - gy;
        if (fd <= 3) return;

        try {
            var lb = bot.blockAt(g.position.offset(0, 1, 0));
            if (lb && SAFE_LAND.has(lb.name)) return;
        } catch(e) {}

        if (!st.clutching) {
            var nether = bot.game && bot.game.dimension && bot.game.dimension.indexOf('nether') >= 0;
            var bucketName = nether ? 'powder_snow_bucket' : 'water_bucket';
            var hotbarSlot = findItemInHotbar(bucketName);
            if (hotbarSlot < 0 && nether) {
                bucketName = 'water_bucket';
                hotbarSlot = findItemInHotbar(bucketName);
            }
            if (hotbarSlot >= 0 || st.equipped) {
                st.clutching = true;
                st.clutchHotbar = hotbarSlot;
                st.clutchBucket = bucketName;
                st.clutchAttempts = 0;
                log('[Clutch] Fall detected! Fall: ' + fd.toFixed(1) + ', Dist: ' + dg.toFixed(1) + ', Vel: ' + vy.toFixed(2));
            } else {
                st.done = true;
                return;
            }
        }

        try {
            if (st.clutchHotbar >= 0) {
                bot.setQuickBarSlot(st.clutchHotbar);
            }
            bot._client.write('use_item', {
                hand: 0,
                sequence: 0,
                rotation: {
                    x: -(bot.entity.yaw * 180 / Math.PI),
                    y: -(bot.entity.pitch * 180 / Math.PI)
                }
            });
            st.clutchAttempts++;
                if (st.clutchAttempts === 1) {
                    var gp = g.position;
                    var p = bot.entity.position;
                    log('[Clutch] Placing... Bot: ' + p.x.toFixed(1) + ',' + p.y.toFixed(1) + ',' + p.z.toFixed(1) +
                        ' Ground: ' + gp.x + ',' + gp.y + ',' + gp.z +
                        ' Slot: ' + bot.quickBarSlot +
                        ' Held: ' + (bot.heldItem ? bot.heldItem.name : 'none'));
                }
                if (st.clutchAttempts >= 40) {
                    st.done = true;
                    log('[Clutch] Gave up after ' + st.clutchAttempts + ' attempts');
                }
            } catch(e) {
                log('[Clutch] Error: ' + e);
                st.done = true;
            }
    });
}
'''

    def _setup_js_fall_clutch(self):
        """Initialize the JavaScript fall clutch handler.

        The entire fall detection and water bucket clutch runs in JavaScript
        on the physicsTick event (~50ms). This avoids JSPyBridge deadlocks:
        - Python->JS calls (bot.equip, bot.activateBlock) from within a
          JS->Python physicsTick callback deadlock the bridge.
        - Deferring to the regular tick loop is too slow (~1s interval vs
          ~90ms between detection and impact).

        The JS code is embedded in _FALL_CLUTCH_JS and evaluated with
        Node.js vm.runInThisContext, then called with (bot, logFn, Vec3).
        """
        from javascript import require

        def log_callback(message):
            add_log(
                title=self.agent.pack_message(message),
                label="action"
            )

        try:
            vm = require('vm')
            vec3 = require('vec3').Vec3
            setup_fn = vm.runInThisContext('(' + self._FALL_CLUTCH_JS + ')')
            setup_fn(self.agent.bot, log_callback, vec3)

            add_log(
                title=self.agent.pack_message("[Clutch] JS fall handler registered"),
                label="success"
            )
        except Exception as e:
            add_log(
                title=self.agent.pack_message("[Clutch] Failed to load JS handler"),
                content=f"Exception: {e}",
                label="error"
            )

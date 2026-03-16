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

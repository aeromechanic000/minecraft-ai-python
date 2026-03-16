"""
State Buffer Module

Provides a shared state container for inter-module communication between
Cerebellum, Brain, and Executor. Single-threaded access (no locking needed).
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class ActionSource(Enum):
    """Source of action - used by both Executor and StateBuffer."""
    CEREBELLUM_REFLEX = 1
    CEREBELLUM_URGENT = 2
    BRAIN_PLANNED = 3


@dataclass
class CurrentAction:
    """Info about the currently executing action."""
    name: str = ""
    source: ActionSource = ActionSource.BRAIN_PLANNED
    params: Dict[str, Any] = field(default_factory=dict)
    started_at: float = 0.0  # timestamp when action started

    @property
    def elapsed_seconds(self) -> float:
        """How long the action has been running."""
        import time
        return time.time() - self.started_at if self.started_at > 0 else 0

    def is_active(self) -> bool:
        """Check if there's an active action."""
        return self.name != ""

    def to_dict(self) -> Dict:
        """Convert to dict for LLM prompt."""
        return {
            "name": self.name,
            "source": self.source.name,
            "params": self.params,
            "elapsed_seconds": round(self.elapsed_seconds, 1)
        }


@dataclass
class AgentState:
    """Snapshot of agent state at a point in time."""
    # Position
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0, "z": 0})

    # Health & Status
    health: float = 20.0
    food: float = 20.0
    is_on_fire: bool = False
    is_in_water: bool = False
    is_in_lava: bool = False

    # Nearby Entities
    nearby_hostiles: List[Dict] = field(default_factory=list)
    nearest_hostile: Optional[Dict] = None

    # Blocks
    block_at_feet: Optional[str] = None
    block_above: Optional[str] = None

    # Motion
    is_moving: bool = False
    is_stuck: bool = False

    # Current Action (KEY: visible to Brain for decision making)
    current_action: CurrentAction = field(default_factory=CurrentAction)

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)


class StateBuffer:
    """Simple state buffer for single-threaded access."""

    def __init__(self):
        self._state: AgentState = AgentState()

    def update(self, **kwargs) -> None:
        """Update state with new values."""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self._state.timestamp = datetime.now()

    def read(self) -> AgentState:
        """Get current state."""
        return self._state

    def set_current_action(self, action: CurrentAction) -> None:
        """Update the current action being executed."""
        self._state.current_action = action

    def clear_current_action(self) -> None:
        """Clear the current action when execution completes."""
        self._state.current_action = CurrentAction()

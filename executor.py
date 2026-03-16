"""
Action Executor Module

Centralized action executor with priority queue.
- Receives actions from Cerebellum and Brain
- Executes ONE action at a time SYNCHRONOUSLY
- Updates StateBuffer with current action info (visible to Brain)
- Brain can request interruption of any action (including cerebellum)
- Cerebellum can interrupt based on per-reflex 'interrupts' config
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
import time

from state_buffer import ActionSource, CurrentAction
from utils import add_log


@dataclass
class ActionRequest:
    """Represents a request to execute an action."""
    name: str
    perform: Callable        # The skill function to execute
    params: Dict[str, Any]   # Parameters for the function
    source: ActionSource
    priority: int = 0        # Lower = higher priority
    created_at: float = field(default_factory=time.time)


class ActionExecutor:
    """Centralized action executor with priority queue."""

    def __init__(self, agent, state_buffer):
        self.agent = agent
        self.state_buffer = state_buffer
        self._current_request: Optional[ActionRequest] = None
        self._pending_actions: List[ActionRequest] = []
        self._is_executing: bool = False

    def submit(self, request: ActionRequest) -> None:
        """
        Submit an action request.
        Adds to queue sorted by priority.
        """
        self._pending_actions.append(request)
        self._pending_actions.sort(key=lambda r: (r.source.value, r.priority))

    def has_pending(self) -> bool:
        """Check if there are pending actions."""
        return len(self._pending_actions) > 0

    def get_next(self) -> Optional[ActionRequest]:
        """Get highest priority action from queue."""
        if self._pending_actions:
            return self._pending_actions.pop(0)
        return None

    def get_current_action_info(self) -> CurrentAction:
        """Get info about current action for Brain decision making."""
        if self._current_request is None:
            return CurrentAction()

        return CurrentAction(
            name=self._current_request.name,
            source=self._current_request.source,
            params=self._current_request.params,
            started_at=self._current_request.created_at
        )

    def should_interrupt_current(self, new_request: ActionRequest) -> bool:
        """Check if new request should interrupt current action."""
        if self._current_request is None:
            return False

        # Cerebellum reflex always interrupts (when allowed)
        if new_request.source == ActionSource.CEREBELLUM_REFLEX:
            return True

        # Higher priority (lower number) interrupts
        if new_request.source.value < self._current_request.source.value:
            return True

        return False

    def interrupt_current(self, reason: str = "") -> None:
        """
        Interrupt current action.

        Can be called by:
        - Cerebellum (for reflex actions)
        - Brain (via request_interrupt() when LLM decides to)
        """
        if self._current_request:
            from utils import add_log

            # Stop pathfinder if moving
            try:
                if hasattr(self.agent.bot, 'pathfinder') and self.agent.bot.pathfinder:
                    if hasattr(self.agent.bot.pathfinder, 'isMoving') and self.agent.bot.pathfinder.isMoving():
                        self.agent.bot.pathfinder.stop()
            except Exception as e:
                add_log(
                    title=self.agent.pack_message("Pathfinder stop error during interrupt"),
                    content=str(e),
                    label="warning"
                )

            # Stop PVP if fighting
            try:
                if hasattr(self.agent.bot, 'pvp') and self.agent.bot.pvp:
                    if hasattr(self.agent.bot.pvp, 'stop'):
                        self.agent.bot.pvp.stop()
            except Exception as e:
                add_log(
                    title=self.agent.pack_message("PVP stop error during interrupt"),
                    content=str(e),
                    label="warning"
                )

            add_log(
                title=self.agent.pack_message(f"Action interrupted: {self._current_request.name}"),
                content=f"Reason: {reason}" if reason else "No reason provided",
                label="warning"
            )

            self._current_request = None
            self._is_executing = False
            self.state_buffer.clear_current_action()

    def request_brain_interrupt(self, reason: str = "") -> bool:
        """
        Request interruption from Brain.

        Called when LLM decides to interrupt current action.
        Returns True if interruption succeeded.
        """
        if not self._is_executing:
            return False

        try:
            self.interrupt_current(reason=f"Brain decision: {reason}")
            return True
        except Exception as e:
            from utils import add_log
            add_log(
                title=self.agent.pack_message("Brain interrupt failed"),
                content=f"Exception: {e}",
                label="error"
            )
            return False

    def execute_next(self) -> Optional[Any]:
        """
        Execute the highest priority action synchronously.

        Updates StateBuffer with current action info before execution.
        """
        if self._is_executing:
            return None

        action = self.get_next()
        if action is None:
            return None

        self._current_request = action
        self._is_executing = True

        # Update state buffer with current action (visible to Brain)
        current_action = CurrentAction(
            name=action.name,
            source=action.source,
            params=action.params,
            started_at=time.time()
        )
        self.state_buffer.set_current_action(current_action)

        try:
            # Log action source
            source_label = "[Cerebellum]" if action.source.name.startswith("CEREBELLUM") else "[Brain]"
            add_log(
                title=f"{source_label} Executing action: {action.name}",
                content=f"Params: {action.params}",
                label="action"
            )

            # Execute the action synchronously
            result = action.perform(**action.params)

            add_log(
                title=f"{source_label} Action completed: {action.name}",
                content=f"Result: {result}" if result else "Success",
                label="success"
            )
            return result
        except Exception as e:
            add_log(
                title=f"{source_label} Action error: {action.name}",
                content=str(e),
                label="error"
            )
            return None
        finally:
            self._current_request = None
            self._is_executing = False
            self.state_buffer.clear_current_action()

    @property
    def is_busy(self) -> bool:
        """Check if executor is currently executing an action."""
        return self._is_executing or self._current_request is not None

    @property
    def current_action(self) -> Optional[ActionRequest]:
        """Get current action request."""
        return self._current_request

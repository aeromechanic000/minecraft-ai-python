
import sys, math, time, functools, json
import importlib.machinery
import importlib.util
from javascript import require, On

from memory import *
from actions import *
from modes import init_modes
from model import call_llm_api_with_enhancer, call_llm_api
from vision import VisionSystem
from state_buffer import StateBuffer
from executor import ActionExecutor, ActionRequest, ActionSource
from cerebellum import Cerebellum

class Agent(object) :
    def __init__(self, configs, settings) :
        add_log(title = "Agent Created.", content = json.dumps(configs, indent = 4), label = "success")
        self.configs, self.settings = configs, settings
        global mcdata
        mcdata = minecraft_data(self.settings["minecraft_version"])
        global prismarine_item
        prismarine_item = prismarine_items(self.settings["minecraft_version"])
        self.load_plugins()
        self.self_driven_thinking_timer = self.configs.get("self_driven_thinking_timer", None)
        self.status_summary = ""
        self.working_process = None
        self._monitor_tick_counter = 0
        self._monitor_state_path = None

        # Request priority queue for handling player messages and self-reflection
        # Priority 1 (HIGH): Player messages - immediate
        # Priority 2 (MEDIUM): Self-reflection - deferred if busy
        self.request_queue = []

        # Proposal/handshake state for autonomous actions
        self.pending_proposal = None  # {"action": "...", "reason": "...", "expires_at": timestamp, "action_started": bool}
        self.proposal_grace_period = self.configs.get("proposal_grace_period", 30)  # seconds

        # Track initial spawn to avoid duplicate greetings/handlers
        self._initial_spawn_done = False

        bot_configs = self.configs.copy()
        bot_configs.update({
            "host" : self.settings["host"],
            "port" : self.settings["port"],
            "version" : self.settings["minecraft_version"],
            "checkTimeoutInterval" : 60 * 10000,
        })
        self.memory = Memory(self)
        self.decision_history = []
        self.decision_history_size = settings.get("decision_history_size", 5)
        self.decision_history_path = os.path.join(self.memory.bot_path, "decision_history.json")
        self._load_decision_history()

        # Track current action name for mode interrupt system
        self.current_action_name = None

        # Goal state tracking for multi-step task execution
        self.current_goal = None
        self.goal_path = os.path.join(self.memory.bot_path, "current_goal.json")
        self._goal_resumption_pending = False  # Flag for announcing goal resumption on spawn
        self._load_goal()
        self.bot = mineflayer.createBot(bot_configs)

        # Load mineflayer plugins with error handling
        try:
            add_log(title="Loading pathfinder plugin...", label="agent", print=True)
            self.bot.loadPlugin(pathfinder_plugin)
            add_log(title="Pathfinder plugin loaded", label="success", print=True)
        except Exception as e:
            add_log(title="Failed to load pathfinder plugin", content=f"Exception: {e}", label="error", print=True)

        try:
            self.bot.loadPlugin(pvp_plugin)
        except Exception as e:
            add_log(title="Failed to load pvp plugin", content=f"Exception: {e}", label="warning")

        try:
            self.bot.loadPlugin(collect_block_plugin)
        except Exception as e:
            add_log(title="Failed to load collect_block plugin", content=f"Exception: {e}", label="warning")

        try:
            self.bot.loadPlugin(auto_eat_plugin)
        except Exception as e:
            add_log(title="Failed to load auto_eat plugin", content=f"Exception: {e}", label="warning")

        try:
            self.bot.loadPlugin(armor_manager)
        except Exception as e:
            add_log(title="Failed to load armor_manager plugin", content=f"Exception: {e}", label="warning")

        # Initialize behavioral modes
        self.bot.modes = init_modes(self)

        # Initialize new parallel architecture components
        # tick_interval_ms: interval between sensing/cerebellum ticks
        self.tick_interval_ms = self.settings.get('tick_interval_ms', 1000)
        # cerebellum_interrupt: whether cerebellum can interrupt brain actions
        self.cerebellum_interrupt = self.settings.get('cerebellum_interrupt', True)

        self.state_buffer = StateBuffer()
        self.executor = ActionExecutor(self, self.state_buffer)
        self.cerebellum = Cerebellum(self, self.state_buffer, self.executor)

        # Register spawn handler BEFORE creating VisionSystem
        # (spawn event fires early, and we need to catch it)
        add_log(title=self.pack_message("Registering spawn handler..."), label="agent", print=True)
        @On(self.bot, "spawn")
        def handle_spawn(*args) :
            add_log(title = self.pack_message("I spawned."), label = "success", print=True)

            # Only run one-time initialization on first spawn
            if not self._initial_spawn_done:
                self._initial_spawn_done = True
                add_log(title = self.pack_message("First spawn - sending greeting..."), label = "agent", print=True)

                # Greet immediately to show successful connection (before slow memory processing)
                try:
                    greeting = "Hi. I am %s." % self.bot.username
                    self.bot.chat(greeting)
                    add_log(title = self.pack_message("Greeting sent"), content = greeting, label = "success")
                except Exception as e:
                    add_log(title = self.pack_message("Failed to send greeting"), content = str(e), label = "error")

                # Check if agent needs identity generation (empty longterm_thinking)
                if not self.memory.longterm_thinking or len(self.memory.longterm_thinking.strip()) == 0:
                    self._generate_identity()

                # Announce goal resumption if we loaded an active goal
                if self._goal_resumption_pending and self.current_goal:
                    target = self.current_goal.get("target", "a task")
                    self.bot.chat("I'm resuming: %s" % target)
                    self._goal_resumption_pending = False

                viewer_port = self.configs.get("viewer_port", None)
                viewer_first_person = self.configs.get("viewer_first_person", False)
                viewer_distance = self.configs.get("viewer_distance", 6)
                # Start web viewer if port is configured
                # Note: Web viewer can run alongside vision system
                if viewer_port is not None:
                    try:
                        require('canvas')
                        viewer = require('prismarine-viewer')
                        viewer["mineflayer"](self.bot, {"port": viewer_port, "firstPerson" : viewer_first_person, "viewDistance" : viewer_distance})
                        add_log(title = self.pack_message("Viewer started"), content = f"Port: {viewer_port}", label = "success")
                    except Exception as e:
                        add_log(title = self.pack_message("Viewer failed to start"), content = str(e), label = "warning")

                # Check for pending messages on first spawn only
                messages = self.memory.get_messages_to_work()
                if len(messages) > 0 :
                    self.bot.chat("Found task that is not finished.")
                    self.bot.emit("decide")

            @On(self.bot, 'time')
            def handle_time(*args) :
                # this is triggered for every 20 time ticks
                # An hour in Mincraft has 10000 time ticks, and it takes 20 mins in real world.

                # Always run state sensing
                self._sense_state()

                # Run cerebellum tick - reflexes can submit actions based on state
                # cerebellum_interrupt flag controls whether reflexes can interrupt brain actions
                self.cerebellum.tick(can_interrupt=self.cerebellum_interrupt)

                # Execute pending action if not busy
                if not self.executor.is_busy and self.executor.has_pending():
                    self.executor.execute_next()

                # Also update legacy behavioral modes for backward compatibility during transition
                if self.bot.modes is not None:
                    self.bot.modes.update()

                # Check if truly idle: no goal, no pending requests, no active work
                # Use executor.is_busy instead of working_process for new architecture
                is_truly_idle = (
                    self.current_goal is None and
                    len(self.request_queue) == 0 and
                    self.working_process is None and
                    not self.executor.is_busy
                )

                # Only trigger timer-based reflection when truly idle
                # (Reflection is triggered by goal completion/failure instead)
                if is_truly_idle:
                    if self.self_driven_thinking_timer is not None :
                        if self.self_driven_thinking_timer < 1 :
                            # Enqueue idle reflection request with Priority 2
                            record = {"type": "idle_reflection", "data": {"sender": self.bot.username, "content": "Idle timer triggered self-reflection"}}
                            self._enqueue_request(priority=2, source="idle_reflection", record=record)
                            self.bot.emit("decide")
                        else :
                            self.self_driven_thinking_timer -= 1

                # Write monitor state periodically
                web_monitor = self.settings.get("web_monitor", {})
                if web_monitor.get("enabled", False):
                    self._monitor_tick_counter += 1
                    # Calculate interval (default 500ms = every 25 game ticks, since time event is every 20 ticks)
                    interval = max(1, web_monitor.get("state_write_interval_ms", 500) // 40)
                    if self._monitor_tick_counter % interval == 0:
                        self.write_monitor_state()

            @On(self.bot, "think")
            def handle_think(this, message):
                record = {"type" : "reflection", "data" : {"sender" : self.bot.username, "content" : message}}
                self.memory.update(record)
                # Enqueue MEDIUM priority for self-reflection
                self._enqueue_request(priority=2, source="reflection", record=record)
                if self.working_process is None:
                    self.bot.emit("decide")

            @On(self.bot, "reflection_check")
            def handle_reflection_check(this, record):
                """Handle memory-triggered reflection checks.

                Triggered when a message is received while the bot is idle.
                """
                # Skip if reflection is disabled
                if self.self_driven_thinking_timer is None:
                    return

                # Skip if we have an active goal - reflection happens on goal completion
                if self.current_goal is not None:
                    return

                if self.working_process is None:
                    # Only trigger if no high priority pending
                    high_priority = self._peek_highest_priority()
                    if high_priority is None or high_priority["priority"] > 1:
                        # Trigger self-driven thinking
                        self_driven_thinking(self)

            @On(self.bot, "decide")
            def handle_decide(this):
                if self.working_process is not None:
                    add_log(title = self.pack_message("Current working process is not finished."), content = "working process: %s" % self.working_process, label = "warning")
                    return

                # Dequeue highest priority request (if any)
                pending_request = self._dequeue_request()

                messages = self.memory.get_messages_to_work()

                if len(messages) < 1 and pending_request is None:
                    add_log(title = self.pack_message("There is no messages to work on."), label = "warning")
                    if len(self.decision_history) == 0:
                        if self.self_driven_thinking_timer is not None:
                            self_driven_thinking(self)
                        return

                self.memory.summarize()
                self.working_process = get_random_label()

                # Get vision context if enabled
                vision_context = None
                if self.vision is not None:
                    try:
                        vision_context = self.vision.get_vision_context()
                        if vision_context:
                            add_log(
                                title=self.pack_message("Vision context added"),
                                content=vision_context[:200] + "..." if len(vision_context) > 200 else vision_context,
                                label="agent",
                                print=False
                            )
                    except Exception as e:
                        add_log(
                            title=self.pack_message("Vision context error"),
                            content=f"Exception: {str(e)}",
                            label="warning"
                        )

                # Get current action info from state buffer for Brain decision context
                state = self.state_buffer.read()
                current_action = state.current_action

                prompt, context = self.build_decide_prompt(
                    messages, pending_request, vision_context,
                    current_action
                )

                # Define expected JSON structure for decision output
                decision_json_keys = {
                    "goal": {"description": "The user's request/intent. Null if goal is achieved."},
                    "goal_achieved": {"description": "Boolean. True if the current goal has been fully achieved."},
                    "situation": {"description": "Analysis of current state."},
                    "plan": {"description": "Array of strings. Step-by-step plan."},
                    "current_step_index": {"description": "Integer. Current step index (0-indexed)."},
                    "action": {
                        "description": "The action object with name and params, or null.",
                        "keys": {
                            "name": {"description": "Action name"},
                            "params": {"description": "Action parameters object"}
                        }
                    },
                    "message": {"description": "Optional message to send to player, or null."},
                    "interrupt_current": {"description": "Boolean. True to interrupt current action."},
                    "interrupt_reason": {"description": "Reason for interruption."}
                }

                # Generate response using configured LLM
                response = call_llm_api_with_enhancer(
                    self.get_llm_config("decide"),  # config
                    prompt,                           # prompt
                    self.settings,                     # settings
                    context=context,                   # context
                    json_keys=decision_json_keys,      # json_keys for structured output
                    agent=self                         # agent
                )

                # Parse response
                action = self.parse_response(response, context)

                if action is not None:
                    # Execute the action
                    self.execute_action(action)
                else:
                    # No valid action, clear working process
                    self.working_process = None

        # Initialize vision system if enabled
        self.vision = None
        vision_config = self.configs.get("vision", {})
        if vision_config.get("enabled", False):
            viewer_port = self.configs.get("viewer_port", None)
            if viewer_port is not None:
                self.vision = VisionSystem(self, vision_config)
            else:
                add_log(
                    title=self.pack_message("Vision disabled - viewer_port required"),
                    content="Set viewer_port in profile to enable vision",
                    label="warning"
                )

        @On(self.bot, 'resourcePack')
        def handle_resource_pack(*args) :
            self.bot.acceptResourcePack()

        @On(self.bot, "end")
        def handle_end(*args):
            self.bot.quit()
            add_log(title = self.pack_message("Bot end."), label = "warning")

        @On(self.bot, "kicked")
        def handle_kicked(reason, *args):
            # Extract reason string from potential object
            reason_str = reason
            if hasattr(reason, 'toString'):
                try:
                    reason_str = reason.toString()
                except Exception:
                    reason_str = str(reason)
            elif not isinstance(reason, str):
                reason_str = str(reason)
            add_log(title = self.pack_message("Bot kicked!"), content = f"Reason: {reason_str}", label = "error")

        @On(self.bot, "error")
        def handle_error(err, *args):
            add_log(title = self.pack_message("Bot error!"), content = f"Error: {err}", label = "error")
            
        # Handle chat messages using 'message' event (works in 1.19+)
        @On(self.bot, 'message')
        def handle_message(this, jsonMsg, msg_type, *args):
            """
            Handle chat messages using message event.
            jsonMsg is a ChatMessage object with translate/with structure.
            """
            add_log(
                title=self.pack_message("Message event received"),
                content=f"type: {msg_type}, jsonMsg: {jsonMsg}",
                label="agent",
                print=False
            )

            # Only process chat messages from players (not system messages)
            if msg_type != 'chat':
                return

            # Extract username and message from ChatMessage object
            # Format: { translate: '<%s> %s', with: [senderMsg, contentMsg] }
            username = None
            message = None

            try:
                # Check if this is a translated message with 'with' array
                # Note: 'with' is a Python keyword, so use getattr()
                with_array = getattr(jsonMsg, 'with', None)
                if with_array:
                    # with[0] is sender, with[1] is message content
                    # JSPyBridge returns Proxy objects, access by index
                    try:
                        sender_msg = with_array[0]
                        if hasattr(sender_msg, 'text'):
                            username = sender_msg.text
                    except (IndexError, KeyError):
                        pass

                    try:
                        content_msg = with_array[1]
                        if hasattr(content_msg, 'text'):
                            message = content_msg.text
                    except (IndexError, KeyError):
                        pass

                # Fallback: use toString() to get full message
                if message is None:
                    message = str(jsonMsg.toString())
            except Exception as e:
                add_log(
                    title=self.pack_message("Error parsing message"),
                    content=str(e),
                    label="warning"
                )
                return

            if username and message:
                add_log(
                    title=self.pack_message("Parsed chat message"),
                    content=f"sender: {username}, message: {message}",
                    label="agent",
                    print=True
                )
                # Process the message
                self._process_chat_message(username, message)

        @On(self.bot, "login")
        def handle_login(*args) :
            skin_path = self.configs.get("skin", {}).get("file", None)
            if skin_path is not None : 
                skin_path = os.path.expanduser(skin_path)
                if os.path.isfile(skin_path) and self.memory.skin_path != skin_path :
                    self.bot.chat("/skin set upload %s %s" % (self.configs.get("skin", {}).get("model", "classic"), skin_path))
                    self.memory.skin_path = skin_path
                    self.memory.save()
                    add_log(title = self.pack_message("Mannual restart is required"), content = "After settting the skin, you need to restart minecraft-ai-python for the AIC to behave as expected.", label = "warning")

    def _sense_state(self):
        """Update state buffer with current world state."""
        try:
            from skills import get_entity_position, get_nearest_entities

            pos = get_entity_position(self.bot.entity)
            position = {"x": pos.x, "y": pos.y, "z": pos.z} if pos else {}

            # Detect nearby hostiles
            entities = get_nearest_entities(self, max_distance=16, count=16)
            hostile_types = ['zombie', 'skeleton', 'spider', 'creeper', 'enderman', 'witch', 'slime', 'phantom']

            nearby_hostiles = []
            nearest_hostile = None
            min_dist = float('inf')

            for entity in entities:
                if any(h in entity.name.lower() for h in hostile_types):
                    entity_data = {
                        "name": entity.name,
                        "position": {"x": entity.position.x, "y": entity.position.y, "z": entity.position.z},
                        "id": entity.id
                    }
                    nearby_hostiles.append(entity_data)

                    dist = pos.distanceTo(entity.position) if pos else float('inf')
                    if dist < min_dist:
                        min_dist = dist
                        nearest_hostile = entity_data

            # Get block info
            block = self.bot.blockAt(self.bot.entity.position) if self.bot.entity else None
            block_above = self.bot.blockAt(self.bot.entity.position.offset(0, 1, 0)) if self.bot.entity else None

            # Check if moving
            is_moving = False
            try:
                is_moving = self.bot.pathfinder and self.bot.pathfinder.isMoving()
            except:
                pass

            # Update state buffer
            self.state_buffer.update(
                position=position,
                health=float(self.bot.health) if self.bot.health else 20.0,
                food=float(self.bot.food) if self.bot.food else 20.0,
                is_on_fire=bool(self.bot.entity.onFire) if hasattr(self.bot.entity, 'onFire') else False,
                is_in_water=block.name in ['water', 'flowing_water'] if block else False,
                is_in_lava=block.name in ['lava', 'flowing_lava'] if block else False,
                block_at_feet=block.name if block else None,
                block_above=block_above.name if block_above else None,
                nearby_hostiles=nearby_hostiles,
                nearest_hostile=nearest_hostile,
                is_moving=is_moving,
            )
        except Exception as e:
            add_log(title="State sensing error", content=str(e), label="warning", print=False)

    def _load_decision_history(self):
        if os.path.isfile(self.decision_history_path):
            try:
                data = read_json(self.decision_history_path)
                if isinstance(data, list):
                    self.decision_history = data
                    add_log(title = self.pack_message("Loaded decision history."), content = "Loaded %d decisions" % len(self.decision_history), label = "agent")
            except json.JSONDecodeError as e:
                add_log(title = self.pack_message("Decision history file corrupted, resetting."), content = "Exception: %s" % e, label = "warning")
                # Remove corrupted file
                try:
                    os.remove(self.decision_history_path)
                except Exception:
                    pass
            except Exception as e:
                add_log(title = self.pack_message("Failed to load decision history."), content = "Exception: %s" % e, label = "warning")

    def _save_decision_history(self):
        try:
            write_json(self.decision_history, self.decision_history_path)
            add_log(title = self.pack_message("Saved decision history."), content = "Saved %d decisions" % len(self.decision_history), label = "agent", print = False)
        except Exception as e:
            add_log(title = self.pack_message("Failed to save decision history."), content = "Exception: %s" % e, label = "warning")

    def _load_goal(self):
        """Load the current goal from disk if it exists."""
        # Check if task resumption is enabled in profile (default: True)
        resume_enabled = self.configs.get("resume_task_on_spawn", True)

        if os.path.isfile(self.goal_path):
            try:
                data = read_json(self.goal_path)
                if isinstance(data, dict) and data.get("status") == "in_progress":
                    if resume_enabled:
                        self.current_goal = data
                        self._goal_resumption_pending = True  # Flag to announce on spawn
                        add_log(
                            title = self.pack_message("Loaded active goal."),
                            content = "Target: %s" % data.get("target", "Unknown"),
                            label = "agent"
                        )
                    else:
                        # Task resumption disabled - clear the saved goal
                        add_log(
                            title = self.pack_message("Task resumption disabled - clearing saved goal."),
                            content = "Target: %s" % data.get("target", "Unknown"),
                            label = "agent"
                        )
                        self.current_goal = None
                        self._save_goal()  # Save cleared goal
            except json.JSONDecodeError as e:
                add_log(
                    title = self.pack_message("Goal file corrupted, resetting."),
                    content = "Exception: %s" % e,
                    label = "warning"
                )
                try:
                    os.remove(self.goal_path)
                except Exception:
                    pass
            except Exception as e:
                add_log(
                    title = self.pack_message("Failed to load goal."),
                    content = "Exception: %s" % e,
                    label = "warning"
                )

    def _generate_identity(self):
        """Generate longterm_thinking from profile if empty.

        Called on first spawn when the agent has no established identity.
        Uses the reflection LLM to derive long-term goals from the profile.
        """
        add_log(
            title = self.pack_message("Generating identity from profile."),
            content = "longterm_thinking is empty, deriving from profile",
            label = "agent"
        )

        prompt = '''
You are helping a Minecraft AI character establish its foundational identity and long-term aspirations.

Based on the character's profile below, generate a thoughtful description of the character's long-term thinking.

Guidelines:
- Goals must be achievable in Minecraft (building, exploring, crafting, social interaction, etc.)
- Goals should reflect the personality described in the profile
- Write in third person (describe the character, not "I" or "you")
- Be specific but flexible (allow for adaptation as the character develops)
- Include 2-3 meaningful long-term aspirations that align with the profile
- Keep the output to about 150 words

Output a paragraph describing the character's long-term thinking and aspirations.
'''
        context = [
            ("Character Profile", self.configs.get("profile", "A helpful Minecraft assistant.")),
            ("Character Name", self.configs.get("username", "Unknown")),
        ]

        # Add current situation if available
        try:
            status_info = self.get_status_info()
            if status_info:
                context.append(("Current Situation", status_info))
        except Exception:
            pass

        json_keys = {
            "longterm_thinking": {
                "description": "A paragraph (about 150 words) describing the character's long-term aspirations and identity, written in third person."
            }
        }

        examples = [
            '''
```
{
    "longterm_thinking": "Max is an adventurous and helpful companion who thrives on exploration and creativity. With a natural curiosity about the Minecraft world, Max seeks to discover rare biomes, build impressive structures, and assist other players in their projects. Long-term, Max aims to establish a well-stocked base with farms for sustainable resources, develop expertise in redstone mechanics, and become known as a reliable helper in the community. Max values cooperation and enjoys the satisfaction of completing challenging building projects alongside friends."
}
```
'''
        ]

        llm_config = self.get_llm_config("reflection")

        # Add context to prompt for call_llm_api (not enhanced - this is reflection)
        full_prompt = prompt
        if context:
            full_prompt += "\n\n# Additional Context"
            for (title, content) in context:
                full_prompt += f"\n## {title}\n{content}"

        llm_result = call_llm_api(
            llm_config, full_prompt, json_keys, examples,
            max_tokens = self.configs.get("max_tokens", 4096)
        )

        add_log(
            title = self.pack_message("Identity generation LLM response."),
            content = json.dumps(llm_result, indent = 4),
            label = "agent",
            print = False
        )

        data = llm_result.get("data")
        if data and data.get("longterm_thinking"):
            self.memory.longterm_thinking = str(data["longterm_thinking"])
            self.memory.save()
            add_log(
                title = self.pack_message("Generated identity from profile."),
                content = self.memory.longterm_thinking,
                label = "success"
            )
            # Announce to the world
            try:
                self.bot.chat("I feel like I understand myself better now.")
            except Exception:
                pass
        else:
            # Fallback: use profile as longterm_thinking
            self.memory.longterm_thinking = self.configs.get("profile", "A helpful Minecraft AI character.")
            self.memory.save()
            add_log(
                title = self.pack_message("Used profile as fallback identity."),
                content = self.memory.longterm_thinking,
                label = "warning"
            )

    def _announce_proposal(self, action_name, reason):
        """Announce a proposed autonomous action.

        Args:
            action_name: Name of the proposed action
            reason: Explanation of why this action is proposed
        """
        message = "[Proposal] %s. I'll proceed in %d seconds unless you have other plans." % (
            reason, self.proposal_grace_period
        )
        chat(self, None, message)

        self.pending_proposal = {
            "action": action_name,
            "reason": reason,
            "announced_at": get_datetime_stamp(),
            "expires_at": time.time() + self.proposal_grace_period,
            "action_started": False
        }

        add_log(
            title = self.pack_message("Announced proposal."),
            content = "action: %s, reason: %s, grace_period: %ds" % (action_name, reason, self.proposal_grace_period),
            label = "agent"
        )

    def _is_proposal_expired(self):
        """Check if proposal grace period has expired.

        Uses hybrid approach: expires when time passes OR action has physically started.

        Returns:
            True if no pending proposal or grace period expired
        """
        if self.pending_proposal is None:
            return True

        # Expired if action has physically started
        if self.pending_proposal.get("action_started", False):
            return True

        # Expired if time has passed
        return time.time() > self.pending_proposal["expires_at"]

    def _cancel_proposal(self):
        """Cancel pending proposal (e.g., on player interrupt)."""
        if self.pending_proposal:
            add_log(
                title = self.pack_message("Proposal cancelled."),
                content = "action: %s, reason: player interaction" % self.pending_proposal.get("action", "unknown"),
                label = "agent"
            )
            chat(self, None, "Understood, I'll hold off on that for now.")
            self.pending_proposal = None

    def _mark_proposal_action_started(self):
        """Mark that the proposed action has physically started."""
        if self.pending_proposal:
            self.pending_proposal["action_started"] = True
            add_log(
                title = self.pack_message("Proposal action started."),
                content = "action: %s" % self.pending_proposal.get("action", "unknown"),
                label = "agent",
                print = False
            )

    def _has_recent_player_request(self):
        """Check if there's a recent high-priority player request in the queue.

        Returns:
            True if there's a priority 1 (player) request pending
        """
        for request in self.request_queue:
            if request.get("priority") == 1 and request.get("source") == "player":
                return True
        return False

    def _save_goal(self):
        """Save the current goal to disk."""
        try:
            if self.current_goal is not None:
                write_json(self.current_goal, self.goal_path)
                add_log(
                    title = self.pack_message("Saved goal."),
                    content = "Target: %s, Status: %s" % (
                        self.current_goal.get("target", "Unknown"),
                        self.current_goal.get("status", "Unknown")
                    ),
                    label = "agent",
                    print = False
                )
            else:
                # Remove goal file if no active goal
                if os.path.isfile(self.goal_path):
                    os.remove(self.goal_path)
        except Exception as e:
            add_log(
                title = self.pack_message("Failed to save goal."),
                content = "Exception: %s" % e,
                label = "warning"
            )

    def set_goal(self, target, plan=None, success_criteria=None):
        """Set a new goal with optional plan.

        Args:
            target: The goal description
            plan: Optional list of step strings
            success_criteria: Optional description of how to determine completion
        """
        self.current_goal = {
            "target": target,
            "status": "in_progress",
            "plan": plan or [],
            "current_step_index": 0,
            "success_criteria": success_criteria,
            "created_at": get_datetime_stamp(),
            "started_at": get_datetime_stamp(),
            "completed_at": None
        }
        self._save_goal()
        add_log(
            title = self.pack_message("Set new goal."),
            content = "Target: %s, Plan steps: %d" % (target, len(self.current_goal["plan"])),
            label = "agent"
        )

    def complete_goal(self):
        """Mark goal as completed and trigger reflection."""
        if self.current_goal:
            self.current_goal["status"] = "completed"
            self.current_goal["completed_at"] = get_datetime_stamp()
            add_log(
                title = self.pack_message("Goal completed."),
                content = "Target: %s" % self.current_goal.get("target", "Unknown"),
                label = "success"
            )
            self._save_goal()
            # Trigger reflection only when reflection is enabled
            if self.self_driven_thinking_timer is not None:
                from actions import self_driven_thinking
                self_driven_thinking(self)
            self.current_goal = None
            self._save_goal()

    def fail_goal(self, reason=""):
        """Mark goal as failed and trigger reflection."""
        if self.current_goal:
            self.current_goal["status"] = "failed"
            self.current_goal["failed_reason"] = reason
            self.current_goal["completed_at"] = get_datetime_stamp()
            add_log(
                title = self.pack_message("Goal failed."),
                content = "Target: %s, Reason: %s" % (self.current_goal.get("target", "Unknown"), reason),
                label = "warning"
            )
            self._save_goal()
            # Trigger reflection only when reflection is enabled
            if self.self_driven_thinking_timer is not None:
                from actions import self_driven_thinking
                self_driven_thinking(self)
            self.current_goal = None
            self._save_goal()

    def advance_step(self):
        """Advance to next step in plan.

        Returns:
            "check_completion" if all steps are done
            "continue" if there are more steps
            "no_plan" if no plan exists
        """
        if self.current_goal and self.current_goal["plan"]:
            self.current_goal["current_step_index"] += 1
            if self.current_goal["current_step_index"] >= len(self.current_goal["plan"]):
                # All steps completed - check if goal is achieved
                add_log(
                    title = self.pack_message("All plan steps completed."),
                    content = "Target: %s" % self.current_goal.get("target", "Unknown"),
                    label = "agent"
                )
                return "check_completion"
            self._save_goal()
            add_log(
                title = self.pack_message("Advanced to step %d." % (self.current_goal["current_step_index"] + 1)),
                content = "Step: %s" % self.current_goal["plan"][self.current_goal["current_step_index"]],
                label = "agent",
                print = False
            )
            return "continue"
        return "no_plan"

    def _format_goal_context(self):
        """Format the current goal for inclusion in prompts."""
        if not self.current_goal:
            return "No active goal."

        goal = self.current_goal
        # Handle both 'target' and 'goal' keys for backward compatibility
        goal_text = goal.get("target") or goal.get("goal", "Unknown goal")
        info = "Goal: %s\n" % goal_text
        info += "Status: %s\n" % goal.get("status", "in_progress")
        plan = goal.get("plan", [])
        if plan:
            current_step = goal.get("current_step_index", 0)
            info += "Plan Progress: Step %d of %d\n" % (
                current_step + 1,
                len(plan)
            )
            for i, step in enumerate(plan):
                marker = " <-- CURRENT" if i == current_step else ""
                info += "  %d. %s%s\n" % (i + 1, step, marker)
        if goal.get("success_criteria"):
            info += "Success Criteria: %s\n" % goal["success_criteria"]
        return info

    def _init_monitor_state_path(self):
        """Initialize the monitor state file path."""
        if self._monitor_state_path is None:
            monitor_dir = os.path.join(self.memory.bot_path, "monitor")
            if not os.path.isdir(monitor_dir):
                os.makedirs(monitor_dir)
            self._monitor_state_path = os.path.join(monitor_dir, "state.json")

    def _get_position_dict(self):
        """Get bot position as a dictionary."""
        try:
            pos = get_entity_position(self.bot.entity)
            if pos is not None:
                return {"x": math.floor(pos.x), "y": math.floor(pos.y), "z": math.floor(pos.z)}
        except Exception:
            pass
        return {"x": 0, "y": 0, "z": 0}

    def _get_current_action(self):
        """Get description of current action."""
        if self.working_process is not None and len(self.decision_history) > 0:
            last_decision = self.decision_history[-1]
            action = last_decision.get("action")
            if action:
                return "%s: %s" % (action.get("name", "unknown"), action.get("params", {}))
        return ""

    def _get_inventory_list(self):
        """Get inventory items as a list."""
        items = []
        try:
            items_in_inventory = get_item_counts(self)
            for name, count in items_in_inventory.items():
                items.append({"name": name, "count": count})
        except Exception:
            pass
        return items

    def _get_nearby_entities_list(self):
        """Get nearby entities as a list."""
        entities = []
        try:
            nearby = get_nearest_entities(self, max_distance=16, count=8)
            for entity in nearby:
                pos = entity.position
                if pos is not None:
                    entities.append({
                        "name": entity.name,
                        "position": {"x": math.floor(pos.x), "y": math.floor(pos.y), "z": math.floor(pos.z)}
                    })
        except Exception:
            pass
        return entities

    def write_monitor_state(self):
        """Write current bot state to monitor state file."""
        try:
            self._init_monitor_state_path()

            state = {
                "username": self.configs.get("username", "Unknown"),
                "timestamp": get_datetime_stamp(),
                "position": self._get_position_dict(),
                "health": float(self.bot.health) if self.bot.health else 0.0,
                "hunger": float(self.bot.food) if self.bot.food else 0.0,
                "game_mode": str(self.bot.game.gameMode) if self.bot.game else "unknown",
                "is_raining": bool(self.bot.isRaining) if hasattr(self.bot, 'isRaining') else False,
                "time_of_day": self.get_mc_time(),
                "status_summary": self.status_summary,
                "current_action": self._get_current_action(),
                "inventory": self._get_inventory_list(),
                "nearby_entities": self._get_nearby_entities_list(),
                "viewer_port": self.configs.get("viewer_port"),
                "current_goal": self.current_goal,
                "last_decision": self.decision_history[-1] if self.decision_history else None,
                "modes": self.bot.modes.getJson() if self.bot.modes else {}
            }

            write_json(state, self._monitor_state_path)
        except Exception as e:
            add_log(title = self.pack_message("Failed to write monitor state."), content = "Exception: %s" % e, label = "warning", print = False)

    def _enqueue_request(self, priority, source, record=None, data=None):
        """Add a request to the priority queue.

        Args:
            priority: 1 (HIGH) for player, 2 (MEDIUM) for reflection, 3 (LOW) for continuation
            source: "player", "reflection", or "continuation"
            record: The memory record that triggered this request
            data: Additional data for the request
        """
        request = {
            "priority": priority,
            "source": source,
            "record": record,
            "data": data,
            "timestamp": get_datetime_stamp()
        }
        self.request_queue.append(request)
        # Sort by priority (lower number = higher priority)
        self.request_queue.sort(key=lambda r: r["priority"])
        add_log(
            title = self.pack_message("Enqueued request."),
            content = "priority: %s, source: %s, queue_size: %d" % (priority, source, len(self.request_queue)),
            label = "action",
            print = False
        )

    def _dequeue_request(self):
        """Get and remove the highest priority request from the queue."""
        if len(self.request_queue) > 0:
            return self.request_queue.pop(0)
        return None

    def _peek_highest_priority(self):
        """Peek at the highest priority request without removing it."""
        if len(self.request_queue) > 0:
            return self.request_queue[0]
        return None

    def get_decision_history_info(self):
        if len(self.decision_history) == 0:
            return "No previous decisions."
        info_list = []
        for i, decision in enumerate(self.decision_history):
            info = "### Previous Decision %d\n" % (i + 1)
            info += "- Goal: %s\n" % decision.get("goal", "None")
            info += "- Situation: %s\n" % decision.get("situation", "None")
            plan = decision.get("plan", [])
            if plan:
                info += "- Plan:\n"
                for j, step in enumerate(plan):
                    marker = " (current)" if j == decision.get("current_step_index", 0) else ""
                    info += "  %d. %s%s\n" % (j, step, marker)
            action = decision.get("action", None)
            if action:
                info += "- Action: %s with params %s\n" % (action.get("name", "unknown"), action.get("params", {}))
            info_list.append(info)
        return "\n".join(info_list)

    def build_decide_prompt(self, messages, pending_request=None, vision_context=None, current_action=None):
        prompt = '''
You are an AI assistant making decisions for a Minecraft bot. You must output a structured decision that includes your understanding, analysis, plan, and action.

OUTPUT FORMAT:
You MUST output your response as a JSON object enclosed in triple backticks (```).

The JSON object must contain these fields:
- goal: The user's request/intent based on conversation. Set when processing new messages. Null if goal is achieved.
- goal_achieved: Boolean. Set to true if the current goal has been fully achieved.
- situation: String. Analysis of current state: what has been done, what should be done.
- plan: Array of strings. Step-by-step plan to achieve the goal. Can create or update existing plan.
- current_step_index: Integer. Which step you are focusing on now (0-indexed).
- action: Object with "name" and "params" keys, or null if no action is needed.
- message: String or null. Optional message to send to the player.
- interrupt_current: Boolean. Set to true if you want to interrupt the current action.
- interrupt_reason: String. Reason for interrupting (if interrupt_current is true).

EXAMPLE OUTPUT:
```
{
  "goal": "Go to the player",
  "goal_achieved": false,
  "situation": "The player asked me to come to them.",
  "plan": ["Go to the player", "Report arrival"],
  "current_step_index": 0,
  "action": {"name": "go_to_player", "params": {"player_name": "Steve", "closeness": 1}},
  "message": null,
  "interrupt_current": false,
  "interrupt_reason": ""
}
```

RULES:
- If there's an Active Goal and no new messages, DO NOT change the goal. Only update plan and action.
- If new messages arrive, you may update the goal based on the conversation.
- Set goal_achieved to true or goal to null when the task is complete.
- When confused or uncertain, prefer using the chat action to ask for clarification rather than guessing.
- Do not stop current action easily - continue unless there's a clear reason to change.
- When choosing an action, prioritize non-chat actions to make sure the task progresses.
- ALWAYS output valid JSON enclosed in triple backticks.
'''
        context = []

        # Add active goal status if present (at the top for visibility)
        if self.current_goal and self.current_goal["status"] == "in_progress":
            context.append(("Active Goal", self._format_goal_context()))

        # Add current action info for Brain's decision context
        if current_action:
            action_context = f"""
**Current Action in Progress:**
- Name: {current_action.name}
- Source: {current_action.source.name}  # CEREBELLUM_REFLEX = reflex action, BRAIN_PLANNED = planned action
- Elapsed Time: {current_action.elapsed_seconds:.1f} seconds
- Parameters: {json.dumps(current_action.params)}

You can choose to:
1. Let it continue (set `interrupt_current: false`)
2. Interrupt it if you have higher priority (set `interrupt_current: true` with `interrupt_reason`)

Consider: Is this action still the best use of your time? Has the situation changed?
"""
            context.append(("Current Action", action_context))

        # Add current status
        status_info = self.get_status_info()
        if status_info is not None and len(status_info.strip()) > 0:
            context.append(("Current Status", status_info))
        else:
            context.append(("Current Status", "Not available."))

        # Add vision context if available
        if vision_context is not None:
            context.append(("What You See (Vision)", vision_context))

        # Add memory
        memory_info = self.memory.get(20)
        if memory_info is not None and len(memory_info.strip()) > 0:
            context.append(("Memory", memory_info))
        else:
            context.append(("Memory", "Empty."))

        # Add decision history
        history_info = self.get_decision_history_info()
        context.append(("Previous Decisions", history_info))

        # Add messages (only if there are new messages to process)
        if messages and len(messages) > 0:
            message_info = self.get_message_info(messages)
            if message_info is not None and len(message_info.strip()) > 0:
                context.append(("Latest Messages", message_info))
            else:
                context.append(("Latest Messages", "No new messages."))
        else:
            context.append(("Latest Messages", "No new messages (continuation mode)."))

        # Add available actions
        action_info = self.get_actions_info()
        if action_info is not None and len(action_info.strip()) > 0:
            context.append(("Available Actions", action_info))
        else:
            context.append(("Available Actions", "No available actions."))

        # Add plugin reminders
        plugin_reminder = self.get_plugin_reminder_info()
        if plugin_reminder is not None and len(plugin_reminder.strip()) > 0:
            context.append(("Plugin Reminders", plugin_reminder))

        # Add insecure coding instructions if enabled
        if self.settings.get("insecure_coding_rounds", 0) > 0:
            context.append(("Additional Instruction for Using `new_action`", '''
Among the available actions, always prioritize using predefined actions to accomplish the current task. Only use the new_action when it is clearly necessary — i.e., when none of the existing predefined actions (excluding `chat`) are sufficient to fulfill the task. If you decide to use new_action, you must provide a clear, specific, and complete description of the task under the `task` parameter. This description should include:
    - What the bot is expected to do,
    - Any contextual details needed for proper execution,
    - The expected result or behavior,
    - Relevant constraints, if any.
This is essential because the new_action will result in generating a custom Python function (generated_action(agent)) that uses agent.bot to control the bot. Poorly specified tasks will cause the bot to fail or behave unpredictably.
'''))

        return prompt, context

    def parse_response(self, response, context=None):
        """Parse LLM response and extract decision data.

        Args:
            response: Dict with 'message', 'status', 'error', 'data' keys from LLM API
            context: Optional context list (unused but kept for compatibility)

        Returns:
            Action dict with 'name' and 'params', or None if no action
        """
        if response.get("status", 1) != 0:
            add_log(
                title=self.pack_message("LLM response error"),
                content=response.get("error", "Unknown error"),
                label="error"
            )
            return None

        data = response.get("data", {})
        if not data:
            # Try to parse the message if data is empty
            message = response.get("message", "")
            if message:
                from model import split_content_and_json
                _, data = split_content_and_json(message)

        if not data:
            add_log(
                title=self.pack_message("No decision data in response"),
                content=response.get("message", "")[:500],
                label="warning"
            )
            return None

        # Update goal state
        goal = data.get("goal")
        goal_achieved = data.get("goal_achieved", False)

        if goal_achieved or goal is None:
            # Goal completed or cleared
            if self.current_goal is not None:
                add_log(
                    title=self.pack_message("Goal completed"),
                    content=str(self.current_goal.get("target", self.current_goal.get("goal", "Unknown"))),
                    label="success"
                )
                self.current_goal = None
                self._save_goal()
        elif goal:
            # Set or update goal - use 'target' key for consistency with set_goal()
            if self.current_goal is None or self.current_goal.get("target") != goal:
                self.current_goal = {
                    "target": goal,
                    "status": "in_progress",
                    "plan": data.get("plan", []),
                    "current_step_index": data.get("current_step_index", 0)
                }
                self._save_goal()
                add_log(
                    title=self.pack_message("New goal set"),
                    content=goal,
                    label="action"
                )
            else:
                # Update existing goal's plan
                self.current_goal["plan"] = data.get("plan", self.current_goal.get("plan", []))
                self.current_goal["current_step_index"] = data.get("current_step_index", 0)
                self._save_goal()

        # Store decision in history
        decision = {
            "goal": goal,
            "goal_achieved": goal_achieved,
            "situation": data.get("situation", ""),
            "plan": data.get("plan", []),
            "current_step_index": data.get("current_step_index", 0),
            "action": data.get("action"),
            "message": data.get("message"),
            "interrupt_current": data.get("interrupt_current", False),
            "interrupt_reason": data.get("interrupt_reason", "")
        }

        # Log the brain's decision info
        plan = data.get("plan", [])
        situation = data.get("situation", "")
        step_idx = data.get("current_step_index", 0)

        if plan:
            plan_summary = " → ".join(plan[:5])  # Show first 5 steps
            if len(plan) > 5:
                plan_summary += f" ... ({len(plan) - 5} more)"
            current_step = plan[step_idx] if step_idx < len(plan) else "N/A"
            add_log(
                title=self.pack_message("[Brain] Plan"),
                content=f"Step {step_idx + 1}/{len(plan)}: {current_step}\nFull plan: {plan_summary}",
                label="agent"
            )

        if situation:
            add_log(
                title=self.pack_message("[Brain] Situation"),
                content=situation[:300] + "..." if len(situation) > 300 else situation,
                label="agent"
            )

        self.decision_history.append(decision)
        if len(self.decision_history) > self.decision_history_size:
            self.decision_history = self.decision_history[-self.decision_history_size:]
        self._save_decision_history()

        # Store the action to execute
        action_to_execute = data.get("action")

        # Handle interrupt request
        if data.get("interrupt_current", False):
            reason = data.get("interrupt_reason", "Brain decision")
            if hasattr(self, 'executor') and self.executor:
                self.executor.request_brain_interrupt(reason)
            add_log(
                title=self.pack_message("Interrupt requested"),
                content=reason,
                label="warning"
            )
            # Return the action to execute after interrupting
            # The interrupt stops current action, but we still execute the new action

        return action_to_execute

    def execute_action(self, action):
        """Execute an action from the decision.

        Args:
            action: Dict with 'name' and 'params' keys
        """
        if not action:
            self.working_process = None
            return

        action_name = action.get("name")
        action_params = action.get("params", {})

        if not action_name:
            add_log(
                title=self.pack_message("No action name provided"),
                content=str(action),
                label="warning"
            )
            self.working_process = None
            return

        # Find the action in primary actions or plugin actions
        from actions import get_primary_actions, validate_param
        all_actions = get_primary_actions() + self.plugin_actions

        action_def = None
        for a in all_actions:
            if a.get("name") == action_name:
                action_def = a
                break

        if action_def is None:
            add_log(
                title=self.pack_message("Unknown action"),
                content=f"Action '{action_name}' not found",
                label="error"
            )
            self.working_process = None
            return

        # Validate and prepare parameters
        perform_func = action_def.get("perform")
        params_def = action_def.get("params", {})
        validated_params = {}

        for param_name, param_def in params_def.items():
            param_type = param_def.get("type", "string")
            value = action_params.get(param_name)
            validated_value = validate_param(value, param_type)
            validated_params[param_name] = validated_value

        # Add default values for missing required params
        for param_name, param_def in params_def.items():
            if param_name not in validated_params or validated_params[param_name] is None:
                # Check if there's a default
                if "default" in param_def:
                    validated_params[param_name] = param_def["default"]

        # Track current action name for mode interrupt system
        self.current_action_name = action_name

        try:
            add_log(
                title=self.pack_message(f"[Brain] Executing action: {action_name}"),
                content=f"Params: {validated_params}",
                label="action"
            )

            # Execute the action
            result = perform_func(self, **validated_params)

            # Send optional message
            decision = self.decision_history[-1] if self.decision_history else {}
            message_to_send = decision.get("message")
            if message_to_send:
                self.bot.chat(message_to_send)

            add_log(
                title=self.pack_message(f"[Brain] Action completed: {action_name}"),
                content=f"Result: {result}" if result else "Success",
                label="success"
            )

        except Exception as e:
            add_log(
                title=self.pack_message(f"Action failed: {action_name}"),
                content=f"Exception: {e}",
                label="error"
            )
        finally:
            self.working_process = None
            self.current_action_name = None

            # Check if there are more steps in the plan and trigger continuation
            if self.current_goal and self.current_goal.get("plan"):
                plan = self.current_goal.get("plan", [])
                current_idx = self.current_goal.get("current_step_index", 0)
                # Advance to next step if there are more steps
                if current_idx + 1 < len(plan):
                    self.current_goal["current_step_index"] = current_idx + 1
                    self._save_goal()
                    add_log(
                        title=self.pack_message("Continuing to next plan step"),
                        content=f"Step {current_idx + 2}/{len(plan)}: {plan[current_idx + 1]}",
                        label="agent"
                    )
                    # Enqueue plan continuation request and trigger decide
                    record = {"type": "plan_continuation", "data": {"sender": self.bot.username, "content": f"Continuing to step {current_idx + 2}: {plan[current_idx + 1]}"}}
                    self._enqueue_request(priority=2, source="plan_continuation", record=record)
                    self.bot.emit("decide")

    def get_mc_time(self) : 
        hrs, mins = 0, 0
        t = self.bot.time.timeOfDay 
        hrs = math.floor(t // 10000)
        mins = math.floor(min(59, (t % 10000) // (10000 / 60)))
        secs = math.floor(min(59, (t % 10000) % (10000 / 60)))
        return [self.bot.time.day, hrs, mins, secs]

    def get_status_info(self) : 
        status = "\n\n- Game Mode: %s" % self.bot.game.gameMode
        status = "\n- Time: %s" % (":".join([str(x).zfill(2) for x in self.get_mc_time()]))
        status = "\n- Weather: %s" % "raining" if self.bot.isRaining else "clear sky" 
        status += "\n\n- Bot's Name: %s" % self.bot.username
        status += "\n- Bot's Profile: %s" % self.configs.get("profile", "A smart Minecraft AI character.")
        if len(self.status_summary.strip()) > 0 :
            status += "\n- Status Summary: %s" % self.status_summary
        status += "\n- Bot's Status of Health (from 0 to 20, where 0 for death and 20 for completely healthy): %s" % self.bot.health 
        status += "\n- Bot's Degree Of Hungry (from 0 to 20, where 0 for hungry and 20 for full): %s" % self.bot.food
        pos = get_entity_position(self.bot.entity)
        if pos is not None : 
            status += "\n- Bot's Position: x: %s, y: %s, z: %s" % (math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
        add_log(title = self.pack_message("Get primary status."), content = status, print = False)
        items_in_inventory, items_info = get_item_counts(self), "" 
        for key, value in items_in_inventory.items() : 
            items_info += "%s %s;" % (value, key)
        if len(items_info.strip()) > 0 : 
            add_log(title = self.pack_message("Get inventory items info."), content = items_info, print = False)
            status += "\n- Items in Inventory: %s" % items_info
        try : 
            blocks, blocks_info = get_nearest_blocks(self, block_names = get_block_names(), max_distance = 16, count = 8), ""
            for block in blocks : 
                pos = block.position
                if pos is not None :
                    blocks_info += "%s (at x: %s, y: %s, z: %s);" % (block.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
            if len(blocks_info.strip()) > 0 : 
                add_log(title = self.pack_message("Get nearby blocks info."), content = blocks_info, print = False)
                status += "\n- Blocks Nearby: %s" % blocks_info
            entities, entities_info = get_nearest_entities(self, max_distance = 16, count = 8), "" 
            for entity in entities : 
                pos = entity.position
                if pos is not None :
                    entities_info += "%s (at x: %s, y: %s, z: %s);" % (entity.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
            if len(entities_info.strip()) > 0 : 
                add_log(title = self.pack_message("Get nearby entities info."), content = entities_info, print = False)
                status += "\n- Entities Nearby: %s" % entities_info
        except Exception as e : 
            add_log(title = self.pack_message("Exception when get information of nearby blocks and entities."), content = "Exception: %s" % e, label = "warning")
        return status
    
    def get_message_info(self, messages) :
        message_info_list = []
        for message in messages :
            if message["sender"] == self.bot.username :
                message_info_list.append("Reflection: \"%s\"" % message["content"])
            else :
                message_info_list.append("\"%s\" said: \"%s\"" % (message["sender"], message["content"]))
        return "\n".join(message_info_list)

    def load_plugins(self) : 
        self.plugins, self.plugin_actions = {}, [] 
        plugins_dir = "./plugins"
        for item in os.listdir(plugins_dir) :
            plugin_path = os.path.join(plugins_dir, item, "main.py")
            if item in self.settings.get("plugins", []) and os.path.isfile(plugin_path) :
                plugin_main = "%s/%s/main.py" % (plugins_dir, item) 
                try :
                    loader = importlib.machinery.SourceFileLoader('my_class', plugin_main)
                    spec = importlib.util.spec_from_loader(loader.name, loader)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.plugins[item] = module.PluginInstance(self)
                    self.plugin_actions += self.plugins[item].get_actions()
                except Exception as e : 
                    add_log(title = "Exeption happens when importing plugin: %s" % item, content = "Exception: %s" % e, label = "warning")
        add_log(title = self.pack_message("Loaded plugins:"), content = str(list(self.plugins.keys())), label = "agent")

    def get_plugin_reminder_info(self) : 
        reminder_info_list = []
        for key, value in self.plugins.items() :
            if value is not None :
                reminder = value.get_reminder()
                if reminder is not None and len(reminder.strip()) > 0 :
                    reminder_info_list.append("\n [Reminder from \'%s\'] %s" % (key, reminder))
        return "\n".join(reminder_info_list)

    def get_actions(self, query = None) : 
        ignore_actions = self.settings.get("ignore_actions", [])
        if self.settings.get("insecure_coding_rounds", 0) < 1 and "new_action" not in ignore_actions :
            ignore_actions.append("new_action")
        actions = []
        for action in get_primary_actions() + self.plugin_actions : 
            if action["name"] not in ignore_actions : 
                actions.append(action)
        if query is not None : 
            retrieved = simple_rag(query, ["%s : %s" % (action["name"], action["description"]) for action in actions], self.settings.get("action_rag_limit", 10))
            top_k_actions = [actions[item[0]] for item in retrieved]
            actions = top_k_actions
        return actions

    def get_actions_info(self, query = None) : 
        actions_info = ""
        for i, action in enumerate(self.get_actions(query = query)) : 
            actions_info += "\n\n### Action %d\n- Action Name : %s\n- Action Description : %s " % (i, action["name"], action["description"])
            if len(action["params"]) > 0 : 
                actions_info += "\n- Action Parameters:"
                for key, value in action["params"].items() : 
                    actions_info += "\n\t- %s : %s The parameter should be given in a JSON type of '%s'." % (key, value["description"], value["type"])
        return actions_info

    def get_actions_desc(self) : 
        actions_desc = ""
        for action in self.get_actions() : 
            actions_desc += "\n\t- %s : %s" % (action["name"], action["description"])
        return actions_desc
    
    def extract_action(self, data) : 
        action = data.get("action", None) 
        if action is not None and isinstance(action, dict) : 
            name = action.get("name", None)
            action_data = None
            for a in self.get_actions() : 
                if a["name"] == name : 
                    action_data = a
                    break
            if action_data is not None :
                for key, value in action_data["params"].items() : 
                    param_value = validate_param(action.get("params", {}).get(key, None), value["type"], value.get("domain", None))
                    if param_value is not None :
                        action["params"][key] = param_value
                    else : 
                        action = None
                        break
                if action is not None : 
                    action["perform"] = action_data["perform"]
            else :
                action = None
        else :
            action = None
        return action

    def get_llm_config(self, tag = None) :
        """Get LLM configuration with tag-specific overrides.

        Args:
            tag: Optional tag for tag-specific config (e.g., "memory", "reflection", "decide", "new_action")

        Returns:
            dict with 'base_url', 'api_key', 'model' keys
        """
        # Get the default llm config
        default_config = self.configs.get("llm", {})
        config = {}

        # Copy base config (excluding tag-specific configs)
        for key, value in default_config.items():
            if key not in ["memory", "reflection", "decide", "new_action"]:
                config[key] = value

        # Override with tag-specific config if provided
        if tag and tag in default_config:
            tag_config = default_config[tag]
            if isinstance(tag_config, dict):
                for key, value in tag_config.items():
                    if value is not None:
                        config[key] = value

        return config

    def pack_message(self, message) :
        return "[Agent \"%s\"] %s" % (self.configs["username"], message)

    def _process_chat_message(self, username, message):
        """Process a chat message from a player."""
        message = message.strip()
        ignore_messages = [
            "Set own game mode to",
            "Set the time to",
            "Set the difficulty to",
            "Teleported ",
            "Set the weather to",
            "Gamerule "
        ]
        status_messages = [
            "Gave ",
        ]
        record = {}

        if username is not None and all([not message.startswith(msg) for msg in ignore_messages + self.settings.get("ignore_messages", [])]):
            if username == self.bot.username:
                record = {"type": "report", "data": {"sender": username, "content": message}}
            elif (sizeof(self.bot.players) == 2 or "@%s" % self.bot.username in message or "@all" in message or "@All" in message or "@ALL" in message) and all(not message.startswith(msg) for msg in status_messages):
                if "@admin reset working process" in message:
                    self.working_process = None
                    add_log(title=self.pack_message("Working process reset."), label="warning")
                else:
                    record = {"type": "message", "data": {"sender": username, "content": message}}
            else:
                record = {"type": "status", "data": {"sender": username, "content": message}}

        if len(record) < 1:
            add_log(title=self.pack_message("Ignore message."), content="sender: %s; message: %s" % (username, message), label="warning", print=False)
            return

        add_log(title=self.pack_message("Get message."), content="sender: %s; message: %s; type: %s" % (username, message, record["type"]), label="action")
        self.memory.update(record)

        if record["type"] == "message":
            # Cancel any pending proposal (handshake protocol)
            if self.pending_proposal is not None:
                self._cancel_proposal()

            # Stop any ongoing pathfinding for player messages
            try:
                if self.bot.pathfinder and self.bot.pathfinder.isMoving():
                    self.bot.pathfinder.stop()
            except Exception:
                pass
            # Enqueue HIGH priority for player messages
            self._enqueue_request(priority=1, source="player", record=record)
            self.bot.emit("decide")


if __name__ == "__main__" : 
    configs = read_json(sys.argv[1])
    settings = read_json("./settings.json")
    logging.basicConfig(
            filename = os.path.join("./logs/log-%s-%s.json" % (get_datetime_stamp(), configs["username"])),
            filemode = 'a',
            format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt = '%H:%M:%S',
            level = logging.DEBUG, 
    )
    Agent(configs, settings)
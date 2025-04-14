# Agent in MineMCP

In MineMCP, the **Agent** serves as the central controller for decision-making and interaction with the Minecraft environment. It continuously receives messages, evaluates the context, generates plans using an LLM, and executes appropriate actions via the available low-level skills.

The Agent is designed to be **autonomous**, **modular**, and **LLM-driven**, allowing it to respond adaptively to dynamic game scenarios while remaining interpretable and extensible.

---

### Agent Lifecycle

The Agent runs in a loop structured around three core processes:

1. **Message Processing**
2. **Planning**
3. **Acting**

---

### 1. Message Processing

The Agent first gathers **new messages** from the environment, including events, observations, or direct player input.

```python
self.get_new_messages()
```

Messages are preprocessed and passed through the system’s LLM context, helping the Agent stay updated on changes in the game world.

---

### 2. Planning

The Agent determines what to do next by generating a **plan** using an LLM.

```python
plan = self.llm.generate_plan(self.state, self.available_actions)
```

It selects from a predefined set of **available actions** (see Section 07 - Actions), considering context, constraints, and goals.

The generated plan is typically a short list of executable steps. Each step corresponds to an action with defined parameters. These are then added to the action queue:

```python
self.actions += plan
```

---

### 3. Acting

The Agent continuously monitors its action queue and performs the next action if available.

```python
def act(self):
    while self.act_running:
        if self.actions:
            action = self.actions.pop(0)
            getattr(self, action["perform"])(**action["params"])
```

Each action corresponds to a high-level command like `go_to_player`, `collect_blocks`, or `fight`, which internally invoke **skills** (see Section 08 - Skills) and API calls to control the bot.

Execution is logged and monitored to ensure stability and traceability.

---

### Additional Features

- **Recent Action History**: Maintains a fixed-length record of past actions to avoid loops and improve memory context.
- **Graceful Failure Handling**: Logs exceptions and attempts recovery from unexpected states during action execution.
- **Asynchronous Design**: Each part (message processing, planning, acting) runs in its own thread to support responsiveness and concurrency.

---

### Summary

The Agent in MineMCP acts as the orchestrator of perception, reasoning, and execution. By combining a clean message-action pipeline with LLM-generated planning and low-level control through skills, it allows complex behaviors to emerge from simple, modular components.

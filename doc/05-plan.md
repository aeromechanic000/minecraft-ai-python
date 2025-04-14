
# Plan in MineMCP

In MineMCP, **planning** is the core process where the agent interprets messages from the environment, constructs reasoning prompts, interacts with an LLM, and generates structured action plans. This step bridges perception and execution, ensuring the agent acts meaningfully based on its understanding of the world.

### The Planning Loop

The agent continuously runs a background loop (`plan()` method) controlled by the flag `self.plan_running`. During each iteration, it performs the following steps:

### 1. **Check for New Messages**

- The agent first checks if there are any pending messages in `self.messages`.
- It only proceeds if at least one of the messages is of type `"whisper"`, which indicates a direct command or instruction targeted at the agent.

### 2. **Extract and Clear Messages**

- The list of messages is copied and then cleared, ensuring that each batch of messages is processed only once.
- A log entry is created to record the messages being processed in this cycle.

### 3. **Construct LLM Prompt**

- The agent calls `build_plan_prompt(messages)` to create a natural language prompt for the LLM. This prompt summarizes the message content and provides necessary context for planning.

### 4. **Call the LLM API**

- The LLM API is invoked via `call_llm_api(...)` with parameters defined in the agent's configuration (such as provider, model, and max token limit).
- If the call fails, an error is logged.

### 5. **Parse LLM Response**

- If the LLM call is successful, the agent logs the response and attempts to parse it using `split_content_and_json()`, which separates the raw message and structured data.
- The structured JSON is expected to contain a `plan` or set of instructions that describe what the agent should do next.

### 6. **Update Agent Status and Push Actions**

- The agent updates its internal status with the extracted plan data via `update_status(data)`.
- Then, it attempts to extract the next action using `self.mcp_manager.extract_action(data)`.
- If a valid action is found, it is pushed to the action queue using `push_action(action)`.

### 7. **Exception Handling**

- The entire planning loop is wrapped in a try-except block.
- If any exception occurs (e.g., malformed LLM output or connection error), it is caught and logged as a warning, ensuring the agent does not crash and can recover in the next loop.

---

### Summary

The **Plan** stage is a key part of MineMCP’s LLM-based decision-making pipeline. It enables the agent to:

- Convert high-level human instructions into structured plans.
- Use a large language model to reason over environmental context and past messages.
- Transform language-based inputs into executable actions.

This structure aligns closely with modern LLM-agent architectures like those in **Voyager** and **Mindcraft**, where messages are interpreted through prompts, and planning is outsourced to capable generative models. Future extensions may involve maintaining memory across planning iterations or dynamically adjusting prompt construction strategies.

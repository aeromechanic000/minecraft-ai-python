
# Act in MineMCP

In MineMCP, the **Act** phase is responsible for executing the action plans generated during the planning phase. This phase takes the structured actions from the queue and translates them into real behaviors inside the Minecraft environment.

### The Acting Loop

The `act()` method runs continuously in its own loop, governed by the `self.act_running` flag. It performs the following operations to ensure actions are carried out correctly and sequentially:

### 1. **Fetch and Clear Action Queue**

- The agent maintains a queue of pending actions in `self.actions`.
- At each iteration, all current actions are copied into a temporary list `actions`, and the original queue is cleared.
- A log is generated to track which actions are being processed.

### 2. **Execute Actions One-by-One**

- If the temporary `actions` list is not empty, the agent pops the first action (`action = actions.pop(0)`) to perform it.
- The action object is expected to be a dictionary containing:
  - `"perform"`: the name of the method to call.
  - `"params"`: a dictionary of keyword arguments for the method.
  - `"name"`: a descriptive label for logging and history tracking.

### 3. **Perform Action via Dynamic Dispatch**

- Using Python’s `getattr`, the agent dynamically retrieves the method specified in `"perform"` and invokes it with the corresponding parameters.
- This dynamic dispatch allows the system to remain extensible and modular: new actions can be implemented as methods on the agent without modifying the `act()` loop.

### 4. **Track Recent Actions**

- Successfully performed actions are appended to `self.recent_actions`, a short-term memory buffer.
- The buffer length is capped using the `action_history_limit` (default: 5), which helps the agent avoid repeated or redundant actions during reasoning and planning.

### 5. **Error Handling**

- Each individual action is wrapped in a try-except block. If performing an action raises an exception (e.g., invalid parameters or method not found), the error is logged.
- The entire acting loop also has a broader try-except wrapper, ensuring the thread remains stable even under unexpected failure conditions.

---

### Summary

The **Act** stage is where **planning becomes behavior**. It handles:

- Fetching actions produced by the planner.
- Dynamically executing action methods with parameters.
- Logging and maintaining a lightweight history of actions for context and planning feedback.

This stage is tightly coupled with the agent’s skillset—i.e., the actual implementation of methods like `move_to`, `attack`, `gather`, etc.—which are defined elsewhere in the agent code.

By decoupling **what to do** (planning) from **how to do it** (acting), MineMCP adheres to a clean, modular architecture. This makes it easy to scale to new skills, add fallback behaviors, or integrate external execution frameworks.

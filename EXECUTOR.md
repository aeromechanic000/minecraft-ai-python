我已经**完整吸收你所有工程细节**，把你补充的：
- **集中式动作执行器（Action Executor）**
- **小脑 = Rule-based / 非大模型、低开销、反射式（self-defense / reflex）**
- **大脑 = 保持原有大模型规划，不增加调用**
- **状态感知按小脑频率运行**
- **信息 Buffer 机制、大模型不高频调用**
- **可中断机制（interrupt）**
- **异步并行三模块：感知 → 小脑 → 大脑 → 执行器**

全部**用专业、严谨、可直接写进架构文档**的英文完整重写，**逐字对齐你的逻辑**，不增、不减、不改你的设计。

---

# Full English Architecture Description
# Current Serial Scheme → Parallel Brain-Cerebellum Scheme with Centralized Executor

## 1. Description of the Original Execution Scheme
In the **original system**, the entire decision-making and control flow runs in a **serial, brain-first manner**. When a task request arrives, the system activates the **brain (LLM-based planner)** to generate a complete action plan, and the generated actions are executed immediately. The **cerebellum** is only activated when the agent is in an **idle state**—that is, when no active plan is being executed by the brain. At that time, the cerebellum performs simple rule-based (Ruby-style) checks to trigger basic self-protective or defensive reflexes such as self-defense, obstacle avoidance, or health recovery.

In this design:
- There is **no independent, unified action executor**.
- Both the brain and cerebellum can directly control action execution.
- The brain and cerebellum **never run in parallel**.
- The cerebellum cannot intervene while the brain is running.
- Sensing, decision-making, and execution are tightly coupled in sequence.
- The brain (LLM) is the dominant decision-maker, and the cerebellum only serves as a fallback mechanism.

---

## 2. The Target Parallel Execution Scheme
The improved system adopts a **fully asynchronous, parallel architecture** with three independent modules: **state sensing**, **cerebellum (deterministic reflex actor)**, **brain (non-deterministic planner)**, and a newly added **centralized action executor** that unifies all action control.

### Core Components (Parallel & Asynchronous)
### 2.1 State Sensing Module
- Sensing runs **at a fixed, high frequency** (aligned with the cerebellum’s decision frequency).
- It continuously extracts environment and agent state (position, health, enemies, obstacles, etc.).
- All observed states are written into a **shared state buffer** for access by the cerebellum, brain, and executor.
- Sensing operates independently and does not wait for the brain or cerebellum.

### 2.2 Cerebellum (Deterministic Reflex Module)
- The cerebellum runs **in parallel, at the same fixed high frequency as sensing**.
- It uses **rule-based (Ruby-style) logic** (or future non-LLM neural networks) for fast, low-overhead decisions.
- It focuses on **reflex-level, survival-critical actions**, such as:
  - Self-defense
  - Emergency dodge
  - Obstacle avoidance
  - Health maintenance
  - Immediate response to danger
- The cerebellum **does not rely on LLM** and introduces no inference overhead.
- It outputs only **immediate, short-horizon action proposals** to the centralized executor.
- It runs continuously, even when the brain is processing a plan.

### 2.3 Brain (Non-Deterministic Planning Module)
- The brain remains **LLM-based**, responsible for high-level task planning and goal generation.
- It runs **asynchronously and infrequently** to avoid excessive overhead.
- It reads state data from the **shared state buffer** only when processing a new request.
- A **state buffer mechanism** ensures the brain does not process redundant or overly frequent inputs.
- The brain processes **one request at a time** and waits until the previous plan and related actions are completed before accepting a new task.
- It supports an **interruptible planning mode**:
  During multi-step plan execution, before executing the next planned action, the brain can
  - reload latest environment state
  - check completed actions
  - check updated system status
  - check new user requests
  and re-evaluate or revise the remaining plan accordingly.

### 2.4 Centralized Action Executor (Newly Added)
This is the **only module that can perform real action execution**.
All action commands from the cerebellum and brain must be sent to this executor.

Its responsibilities include:
- Receive action proposals from the **cerebellum**
- Receive planned actions from the **brain**
- Perform **priority arbitration**
- Resolve **action conflicts** (e.g., cannot jump and crouch at the same time)
- Support **parallel, non-conflicting actions** (e.g., move + aim)
- Execute the final, safe, and valid action command

### Priority Logic Inside the Executor:
1. If the **cerebellum outputs a reflex/defensive action** (self-defense, emergency response), **execute it immediately**.
2. If no cerebellum reflex is triggered, **execute the action provided by the brain’s plan**.

This means:
- When the cerebellum is silent, the agent behaves exactly as in the original system (fully controlled by the brain).
- When the cerebellum detects danger, it overrides the brain’s action safely.

---

## 3. Key Modifications from the Original System
To upgrade from the original serial scheme to the new parallel scheme, the following changes are implemented:

1. **Add a fixed-frequency, parallel sensing module** that synchronizes with the cerebellum.
2. **Run the cerebellum continuously at high frequency**, instead of only during idle states.
3. Keep the cerebellum **rule-based (Ruby-style)** to avoid LLM overhead.
4. **Add a centralized action executor** to unify and control all physical execution.
5. The brain remains **LLM-based** with no additional inference or structural changes.
6. Introduce a **state buffer** to limit the frequency of LLM calls.
7. Support **interruptible planning** for the brain to adapt to dynamic environmental changes.
8. Transform the entire system from serial to **fully asynchronous and parallel execution**.

---

## 4. Summary of Behavior
After the upgrade:
- The **cerebellum provides constant, low-cost reflex protection** in parallel.
- The **brain maintains its original planning logic** without extra overhead.
- The **executor ensures safety and priority**.
- The agent behaves identically to the original system **when no danger is present**.
- The agent automatically enables survival reflexes **when danger appears**, without waiting for or blocking the brain.

This architecture achieves true **brain-cerebellum collaboration** while maintaining full compatibility with the original system logic.

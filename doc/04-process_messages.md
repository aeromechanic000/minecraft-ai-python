
# Process Messages

In MineMCP, the agent listens for chat messages in the Minecraft world and processes them using a filtering and categorization mechanism. This step is crucial, as it allows the agent to understand which messages are relevant, which should trigger actions, and which should be ignored.

### Event Hook: Listening to Chat

The agent registers a listener on the `chat` event from the Minecraft bot. When a new chat message is received, the following steps are executed:

### Message Handling Logic

1. **Check Message Sender**

   - If the message has a valid sender (i.e., `sender is not None`), further evaluation is carried out.
   - Messages from the agent itself (i.e., `sender == self.bot.username`) are treated differently from those sent by other players.

2. **Self-Reflection Mechanism**

   - If the message comes from the agent itself, it may be stored for internal reflection or self-monitoring.
   - This is probabilistic: with a small chance (determined by `reflection` in the agent's configuration), the message is saved as a `"whisper"` type. This allows the agent to reflect on its own statements if needed.

3. **Ignore List Filtering**

   - If the sender is listed in the agent's `ignored_senders` config, the message is discarded and logged silently.
   - This avoids processing messages from known spammy or irrelevant sources.

4. **Message Classification**

   - If the message contains an explicit mention of the agent’s name (e.g., `@AgentName`) or a general broadcast (`@all`, `@All`, `@ALL`), the message is treated as a `"whisper"` — a direct communication or instruction for the agent.
   - Otherwise, the message is categorized as an `"update"` — part of the ongoing environment context but not a direct command.

5. **Message Queuing**

   - Relevant messages (both `"whisper"` and `"update"`) are pushed to the agent’s message queue using `self.push_msg(...)`. This queue feeds into the planning and acting stages that follow.

6. **Logging Ignored Messages**

   - If a message is ignored due to being from an ignored sender, it is logged (but not printed in console) for transparency and debugging purposes.

### Summary

This message processing design allows the agent to:
- React to instructions addressed directly to it.
- Stay aware of contextual updates from the world.
- Avoid distractions from irrelevant or spammy sources.
- Reflect on its own behavior in a lightweight and configurable way.

This mechanism serves as the first filtering stage in the perception-action loop, ensuring that only meaningful inputs reach the reasoning core of the agent.


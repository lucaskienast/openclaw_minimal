# TODO

1. manage chats and memories etc per user and per session (i.e. multi-user and multi-session)
2. manage long term memory better (split it up)
    2.1. have long term memory for within each single chat session (isolated summaries for that chat session)
    2.2. have long term memory across all chat sessions (ONLY for key user preferences and key info, not for general chat summaries - name, job, location, etc - but not every request made or other conversational things)
    2.3. only trigger summaries once token window gets inefficiently large (pick industry standard)
3. enable calling and use of sub agents
    3.1. use A2A protocol for agent to agent communication
4. use MCP for tool calling
5. more sophisticated prompts and output format schema enforcement
   5.1. prompts: workflow guidelines (ReAct, todo checklist, sub agent delegation, response formats, read original message before final response to make sure everything done and answered etc)
   5.2. output formats: use structure doutputs and enforced out format schemas for EVERY LLM call by all agents and subagents
6. Detailed beautiful formatting of logs (boxed lines and emojis)
   6.1. reasoning,
   6.2. tool calls, 
   6.3. todo list status updates, 
   6.4. final answer etc
7. No code warnings ir improper calls of private methods etc outside of class ie proper software development principles
8. More tools available to agents
   8.1. graphing (create charts and save them)
   8.2. write todos to a file 
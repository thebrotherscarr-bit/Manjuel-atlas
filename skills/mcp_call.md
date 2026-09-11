## MCP Call

- **Action Keyword:** mcp_call
- **Description:** Calls one tool on a LOCAL MCP server this ground declares. Say it as "<server> <tool>", with any arguments as a JSON object after them — `atlas muster`, or `atlas flow_list {"project": "atlas"}`. A server is a dial, `MANJUEL_MCP_<NAME>` in .env, and its address must be loopback; anything else is refused by name, because the estate is local. Naming no tool, or one the server does not carry, answers with what that server does carry, so nothing needs a second skill to find its way. Use for "call <tool> on <server>", "what does <server> carry", "which MCP servers do we have".
- **Parameters Needed:** <content>The server and the tool, then any arguments as a JSON object — e.g. `atlas muster` or `atlas flow_list {"project": "atlas"}`. Blank falls back to the objective itself, which is read the same way.</content>
- **Says:** mcp call, call mcp, mcp tool, mcp servers, mcp server

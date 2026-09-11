## MCP Call

- **Action Keyword:** mcp_call
- **Description:** Calls one tool on a LOCAL MCP server this ground declares. A server is a dial — `MANJUEL_MCP_<NAME>` in .env — and its address must be loopback; anything else is refused by name, because the estate is local. Leaving the tool blank answers with what that server carries, and naming a tool it does not carry answers the same way, so nothing needs a second skill to find its way. Use for "call <tool> on <server>", "what does <server> carry", "which MCP servers do we have".
- **Parameters Needed:** <server>The declared server's name, e.g. atlas. Blank lists the servers this ground declares.</server> <tool>The tool to call on that server. Blank lists what the server carries.</tool> <content>That tool's arguments as a JSON object, e.g. {"project": "research"}. Blank sends none.</content>
- **Says:** mcp call, call mcp, mcp tool, mcp servers, mcp server

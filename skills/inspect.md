# Skill: Inspect

- **Action Keyword:** inspect
- **Description:** Reports the FACTS about a file before anything reads it — size, real type by its first bytes, line terminator, line count, first line, when it was modified, which jail it sits in (workspace or ground), whether git tracks it, whether the index holds it, whether it is a secret or client material, and how many injection markers the hard gate finds in it. Never its contents. Use on anything new or from outside (a download, code from GitHub, a pasted file) before reading it; with no path it reports what is NEW in the workspace since this sitting opened.
- **Parameters Needed:** <filepath>The file, relative to the workspace (agent_workspace/) or the ground; the workspace is tried first</filepath>. Leave it out to list what is new in the workspace.
- **Path Args:** filepath -> ground, content -> ground
- **Says:** inspect, what is this file, review the new files, what's new in the workspace, is it safe to read, is this safe to read

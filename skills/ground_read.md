## Ground Read

- **Action Keyword:** ground_read
- **Description:** Reads one file from the ground (the Research folder) as it is on disk right now — pipelines.md, memory.md, a seat's own file, source in chainkit/. Read-only, refuses secrets, stays inside the ground. Use when a question needs the CURRENT contents of a real file, not the index's snapshot of it.
- **Parameters Needed:** <content>The file's path relative to the ground, e.g. pipelines.md or agents/steward.md</content>. A LARGE file comes back as part 1 of N with its section headings listed; to move the window, send the path as <filepath> and the part as <content> — either a number (`2`) or a heading's text (`Fix log`). Two tags means file plus part; one tag always means the whole file.
- **Path Args:** content -> ground, filepath -> ground

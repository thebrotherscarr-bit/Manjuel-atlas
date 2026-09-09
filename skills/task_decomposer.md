# Skill: Multi-Step Operational Decomposition
- **Action Keyword:** decompose_task
- **Model Target:** phi4-mini:latest
- **Description:** Breaks a large objective into an ordered sequence of small, individually checkable steps. Use when a request is too big to act on directly and needs a route before anything is built.
- **CRITICAL CONSTRAINT:** Steps must be things a person can DO and then verify. Each one names how you would know it worked. Do not perform the task - only lay out the route. If the objective is under-specified, list what must be decided first instead of guessing.
- **Output Structure Requirement:** Optional `<thinking>...</thinking>` reasoning first, then a numbered list. Each line: an active-verb command, then ` -> DONE WHEN: <the observable result>`. Nothing after the list.
- **Parameters Needed:** <content>The objective to break down</content>

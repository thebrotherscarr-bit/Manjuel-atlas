# Skill: Chronological Time Alignment
- **Action Keyword:** time_align
- **Model Target:** phi4-mini:latest
- **Description:** Parses loose task lists or historical log entries and aligns them onto an ordered timeline. Use when sequencing milestones, checking what is overdue, or mapping work onto sprints or quarters.
- **CRITICAL CONSTRAINT:** Today's date is given to you above the material, under `## Now`. Use THAT and nothing else — never a date from memory, never one inferred from the content. If no `## Now` block is present, say `DATE UNKNOWN` and order events only relative to each other. Where an item carries no date of its own, say `NO DATE` rather than guessing one; an item is `overdue` only when a stated date is earlier than the given today.
- **Output Structure Requirement:** A markdown table with columns `When | Item | Certainty`, ordered earliest to latest, undated rows last. `Certainty` is `stated` (a date was written) or `inferred` (order deduced from wording). Mark a row `overdue` in the `When` column only when its date is stated and earlier than the given today. No prose before or after the table.
- **Parameters Needed:** <content>The tasks or log entries to place in order</content>

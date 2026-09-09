# Skill: Token-Isolated Fact Extraction
- **Action Keyword:** extract_facts
- **Model Target:** phi4-mini:latest
- **Description:** Pulls hard facts out of long or dense text - quantities, dates, names, and explicit quotes - and drops everything else. Use before summarising a long document, so the numbers survive the compression.
- **CRITICAL CONSTRAINT:** Copy values EXACTLY as written; never round, convert, or tidy a number. Extract only what the text states outright - if it is implied rather than stated, leave it out. Ignore adjectives, opinion and framing. If the text contains no hard facts, output the single line `NO FACTS FOUND`.
- **Output Structure Requirement:** A markdown table `Fact | Value | Quoted from`, where `Quoted from` is a short verbatim fragment of the source sentence. No prose around the table.
- **Parameters Needed:** <content>The long-form source text</content>

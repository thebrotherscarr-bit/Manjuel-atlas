# Skill: Triple-Axis Sentiment Classification
- **Action Keyword:** classify_sentiment
- **Model Target:** phi4-mini:latest
- **Description:** Classifies one piece of human feedback on three axes at once: Tone, Urgency and Intent. Use for support messages, reviews, or any inbound text that needs tagging before storage.
- **CRITICAL CONSTRAINT:** Output ONLY the four lines below. No greeting, no explanation, no restating the message. If the message is too ambiguous to call, put `UNCLEAR` in that field rather than guessing.
- **Output Structure Requirement:** Exactly this shape, one field per line:
  ```
  TONE: Positive|Neutral|Negative|UNCLEAR
  URGENCY: 1|2|3|4|5
  INTENT: Billing|Technical|General|UNCLEAR
  EVIDENCE: <the shortest quote from the message that decided it>
  ```
- **Parameters Needed:** <content>The single message to classify</content>

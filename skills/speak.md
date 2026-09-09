## Speak

- **Action Keyword:** speak
- **Description:** Read text aloud through the machine's own speech engine. Use when the operator asks to hear something, or asks you to say or read something out. Not for ordinary answers -- `/say on` already speaks every delivery.
- **Parameters Needed:** <content>The text to read aloud. Plain prose; code blocks are announced, not performed.</content>

Speech is capped so a long document is not recited in full -- the rest stays
on screen. If the machine has no speech engine the skill says so rather than
failing silently.

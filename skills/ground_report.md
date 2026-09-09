## Ground Report

- **Action Keyword:** ground_report
- **Description:** States where the chain is standing: the ground path, the agent workspace, the active session, and what is resident on the card right now. Deterministic — read from the harness, never from a model. Use for "where are we", "what is the working dir", "what ground is this".
- **Parameters Needed:** None

The answer to "where am I" must never be generated. Sitting 24 asked for the
working directory and a seat guessed "empty" — the harness knew the true
answer the whole time and was never asked.

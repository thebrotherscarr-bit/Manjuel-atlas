# Skill: Index the Ground
- **Action Keyword:** index_ground
- **Description:** Builds or refreshes the semantic index over the configured roots (see index_roots.txt). Reads documents, splits them into passages, and embeds each one. Unchanged files are skipped by hash, so re-running is cheap. Use this before semantic_search, or after files have changed. Say `rebuild` to discard the old vectors and start from scratch — needed when the embedder changes, since vectors from two models are not comparable.
- **Says:** index the ground, index the record, run the index, rebuild the index, reindex the ground, index_ground
- **Takes:** rebuild | reindex | from scratch | start over | fresh -> content
- **Parameters Needed:** <content>Blank for a normal refresh, or `rebuild` to discard the old index and build it again from nothing.</content>

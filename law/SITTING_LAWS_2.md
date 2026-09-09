# THE SITTING LAWS, continued (the operator's, for the hands)

```
type:     DIRECT (sovereign law of the house)
by:       the operator's word, 2026-09-08; each law dated to the sitting that earned it
cites:    covenant 65118a147dd49ed9 · SITTING_LAWS.md (laws 1-4, sealed) ·
          CLAUDE.md (the standing rules) · ESTATE_LAWS.md (naming)
status:   DRAFTED FOR THE OPERATOR'S SEAL -- `python law\law.py direct law\SITTING_LAWS_2.md`
```

SITTING_LAWS.md is sealed and its bytes may not change; a new law is a new
link (its own Amendment clause). The operator's ruling on where: "put all
the law files together" -- so this file sits in `law/` beside the four it
continues, and is cited as **SITTING LAW n** like them.

## THE SITTING LAWS, 5 and 6

5. **Nothing is edited while the operator's sitting is open.** The REPL
   watches the ground: a changed seat, skill, pipeline or command is
   hot-reloaded into his running session at the next turn; any changed
   text is re-embedded into his live index; a code edit sits on disk
   under running code. So while `sessions/sessions.jsonl`'s last line has
   no `ended`, or he has said he is in the REPL, no file in this ground is
   edited. A hand asks, waits for "closed" or "go", then edits; a code
   edit is delivered with "restart required" in the same sentence.
   Earned 2026-09-04, sitting 84 (a hand reseated the door and half the
   rack under him) and 2026-09-08 (a hand wrote DAYBOOK and TASKS with
   sitting 96 open, in the same command that checked the ledger).

6. **Every law, directive and context file is read, and the hand's line
   is opened, before the first command.** A hand's first acts in this
   ground, in order: read CLAUDE.md; read every file in `law/`; read
   DAYBOOK's last entry, HANDOFF's newest block, CHANGELOG's Unreleased,
   the open lines of TASKS, and SPEC; then write the opening line of
   `sessions/hands.jsonl` (`python -m chainkit.seatlog hand-open`) with
   the rules' fingerprints as read. No command comes before them -- and
   `git status` or `git diff` from a sandbox never, at any point. The last
   act is the closing line. Earned 2026-09-04 (a lock left at 15:28 by a
   suite run from a sandbox) and 2026-09-08 three times: at 07:27 a hand
   ran `git status` as its first act and left the lock CLAUDE.md warns
   of; at 12:56 the tool that hand built to keep hands in line ran `git
   status` itself and left another; and its findings were added to the
   operator's task list from transcripts he had not asked to be mined --
   "you are picking shit to add to your task list from an arbitrary
   source." A hand reads the record; it does not invent work from it.

## Amendment

A further sitting law is a new link, not an edit: write it, seal it with
`python law\law.py direct`, and cite this file and SITTING_LAWS.md.

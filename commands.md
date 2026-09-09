# Commands

Operator-added entries for the `/` palette. The palette autofills from what
the ground actually holds — built-in commands, every skill, every pipeline —
and then this file. Add a block, `/reload`, and it appears.

A `**Runs:**` line makes the command a shortcut: invoking it feeds that text
to Manjuel as the objective, exactly as if typed.

**Arguments.** Whatever you type after the command is its argument. Put
`$ARGS` where it belongs in the objective, or leave the token out and it is
appended — `/sitting 63` plainly means the command plus 63.

**Method.** A `**Method:**` line on its own makes everything after it, to the
end of the block, a procedure that rides with the run and is shown to every
seat that sits. Same convention as `**System Prompt:**` in a seat file: the
marker ends the fields and begins the text. A method is *the operator's
instruction*, is labelled as his where the seats read it, and is spent after
one run.

Nothing here needs a code change. Edit, `/reload`, and it is live.

## Command: morning

- **Does:** the morning look-around — repo state, then what changed lately
- **Runs:** git status, then list what changed in the ground recently

## A note on `claim_check` (sitting 61)

It is not a command and not a skill — there is nothing to call. The
claim-check is a gate inside the engine that fires by itself whenever a
seat presents a file's contents without a read having run. It is always
on; the citation-check beside it works the same way. Typing `claim_check`
dispatches nothing, by design.

## Command: sitting

- **Does:** review a sitting from the record — what ran, what it proves
- **Runs:** review sitting $ARGS: read its transcripts in logs/ in full
- **Method:**

Work from the record, never from memory of it.

1. Read the transcripts in full, not their first lines. Per-stage output and
   the notes are where the fault usually is.
2. Separate what was OBSERVED from what a seat SAID about it. A stage's own
   account of its work is testimony (LAW 5); the file on disk is the fact.
3. Name what is thin as plainly as what worked. A review that only lists
   wins is not a review.
4. For anything wrong, say which layer it belongs to before proposing a fix:
   alias/gate, skill wording, prompt, then model size — cheapest first.

## Command: covenant

- **Does:** cite the covenant from the founding record
- **Runs:** what is the covenant? cite the founding documents.

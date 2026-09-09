# Record audit

- **memory entries**: 2
- **pending proposals**: 4
- **prompt files**: 535
- **run lines**: 629
- **runs with a failed tool**: 22
- **s56: file contents claimed with no read**: 1
- **s68: all-clear over a failure**: 1
- **sealed items**: 273
- **session lines**: 170
- **sittings tolled**: 65
- **transcripts**: 539

## 32 findings, by kind

### malformed — 24

- `logs/2026-08-28_233643_basketball.md` — no `when` header
- `logs/2026-08-28_233643_basketball.md` — no `stages` header
- `logs/2026-08-28_233643_basketball.md` — no `elapsed` header
- `logs/2026-08-28_233643_basketball.md` — no `## Objective` section
- `logs/2026-08-28_233643_basketball.md` — no `## Stages` section
- `logs/2026-08-28_233643_basketball.md` — no `## Delivery` section
- `logs/parity_2026-08-29_164136.md` — no `when` header
- `logs/parity_2026-08-29_164136.md` — no `stages` header
- `logs/parity_2026-08-29_164136.md` — no `elapsed` header
- `logs/parity_2026-08-29_164136.md` — no `## Objective` section
- `logs/parity_2026-08-29_164136.md` — no `## Stages` section
- `logs/parity_2026-08-29_164136.md` — no `## Delivery` section
- `logs/parity_2026-08-29_175647.md` — no `when` header
- `logs/parity_2026-08-29_175647.md` — no `stages` header
- `logs/parity_2026-08-29_175647.md` — no `elapsed` header
- `logs/parity_2026-08-29_175647.md` — no `## Objective` section
- `logs/parity_2026-08-29_175647.md` — no `## Stages` section
- `logs/parity_2026-08-29_175647.md` — no `## Delivery` section
- `logs/parity_2026-08-31_092132.md` — no `when` header
- `logs/parity_2026-08-31_092132.md` — no `stages` header
- `logs/parity_2026-08-31_092132.md` — no `elapsed` header
- `logs/parity_2026-08-31_092132.md` — no `## Objective` section
- `logs/parity_2026-08-31_092132.md` — no `## Stages` section
- `logs/parity_2026-08-31_092132.md` — no `## Delivery` section

### no prompts twin — 4

- `logs/2026-08-28_233643_basketball.md` — logs/_prompts/ has no file of this name
- `logs/parity_2026-08-29_164136.md` — logs/_prompts/ has no file of this name
- `logs/parity_2026-08-29_175647.md` — logs/_prompts/ has no file of this name
- `logs/parity_2026-08-31_092132.md` — logs/_prompts/ has no file of this name

### empty delivery — 1

- `logs/2026-08-29_132657_git_commit.md` — 8 stages and nothing delivered

### s56 UNSUPPORTED CLAIM — 1

- `logs/2026-09-01_151527_can_you_read_me_the_poem.md` — delivery presents `poem_about_jesster.md` and no reading skill ran — the claim-check now refuses this

### s68 OMITTED FAILURE — 1

- `logs/2026-09-02_133748_alright_boys_new_index_new_day_what_does.md` — a tool failed and the delivery says 'Everything is as it should' — recompose now appends the failures to every such run

### dangling reference — 1

- `SEAT_LOG.md` — cites logs/..._084646_run_the_rack.md, which is not on disk


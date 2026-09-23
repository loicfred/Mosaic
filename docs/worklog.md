# Mosaic — Work Log

Session-by-session record of what was built, what broke and why, and the decisions taken along the way.
**The entries live in `worklog`, one file per entry — this file is only the convention.**

Companion files: `requirements.md` (the requirements and the open list) and `../.claude/CLAUDE.md` (how to work
on the code). Those say what the product must be and how to build it; the log says what has happened so far.

## Writing an entry

**Add one at the end of every session.** Create a new file:

```
docs/worklog/YYYY-MM-DD<letter>-<kebab-title>.md
```

The letter is that day's entry order — `a` for the first entry written that day, `b` for the next. The title
is the heading in lowercase with everything but letters and digits turned into hyphens, cut at a word boundary
around sixty characters. The file opens on a single `#` heading carrying the dated title, then the author:

```markdown
# 2026-09-23a — Every model call moved into the Spring app

Author: Claude
```

Then `## Why`, `## What changed` and `## Verification`, saying plainly what was and was not checked.

## Reading it

`ls docs/worklog/` is the index; `grep -rn "<term>" docs/worklog/` finds the session; then read that one file.

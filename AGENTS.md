# agents.md — Blender Helper Skill

## Project Purpose

This project develops a **Claude Code skill** — a Markdown file that is injected into Claude's context to enable specialized behavior when invoked via `/skill-name`. Skills are not applications; they are context-injection documents that shape how Claude responds within a session.

## Planning Phase Behavior

**Be critical.** This is the user's first skill. Apply extra scrutiny to ideas before accepting them:

- Push back if a proposed feature is better handled by a CLAUDE.md instruction, a hook, or a settings entry rather than a skill.
- Ask whether the trigger condition is specific enough. A skill that fires too broadly pollutes context for every session.
- Flag scope creep early. Skills should do one thing well. If an idea requires two unrelated behaviors, question whether it should be two separate skills.
- Challenge assumptions about what a skill *needs* to contain. Every line added to the skill file costs context window space in every invocation.
- Do not accept "nice to have" additions during initial design. Lock the core behavior first.

## Skill Development Guidelines

### File Constraints

| Constraint | Limit | Reason |
|---|---|---|
| Skill file total characters | ≤ 4 000 chars | Skills are injected into context on every invocation; bloat is paid repeatedly |
| Single instruction length | ≤ 120 chars | Keeps instructions scannable and avoids ambiguity |
| Number of top-level sections | ≤ 6 | More sections signal the skill is doing too much |
| Nested bullet depth | ≤ 2 levels | Deeper nesting is usually a sign of over-specification |

### Content Rules

- **No prose explanations.** Write imperatives, not descriptions. "Return X" not "The skill should return X."
- **No examples inside the skill file** unless the behavior cannot be understood without one. Examples consume space and are often stale.
- **Trigger condition must be explicit.** The skill file must state exactly when it applies and when it does not.
- **No redundancy with CLAUDE.md.** If a rule already lives in CLAUDE.md, reference it there — do not copy it into the skill.
- **Version the skill file via git**, not via inline changelogs. Do not add a "Changelog" section.

### Structure Template

Every skill file should follow this order:

1. **One-line purpose** — what the skill does, ≤ 80 chars
2. **Trigger** — when Claude should apply this skill
3. **Behavior** — the concrete steps Claude must follow
4. **Constraints** — hard limits and things Claude must not do
5. *(Optional)* **Output format** — only if the output shape is non-obvious

### Testing a Skill

Before considering a skill done:

- Invoke it in a clean session and verify it fires correctly.
- Invoke it in a session where it should *not* fire and verify it stays silent.
- Check total character count: `wc -c skill-file.md` must be ≤ 4 000.
- Read the skill aloud. If any sentence sounds like documentation rather than an instruction, rewrite it.

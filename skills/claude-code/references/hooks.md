# Hooks — Lifecycle Automation

Hooks are shell commands triggered by lifecycle events. Configure in `settings.json` under `hooks`. Hook command receives event JSON on stdin and may write decision JSON to stdout.

## Lifecycle events (27 total — most useful)

| Event | When fires | Typical use |
|---|---|---|
| `SessionStart` | Session begins | Inject context, warm caches |
| `UserPromptSubmit` | User sends a message | Rewrite prompts, append context |
| `PreToolUse` | Before each tool call | Block dangerous patterns, audit |
| `PostToolUse` | After each tool call | Format/lint after Edit/Write |
| `SubagentStart` | A subagent is spawned | Log spawns, gate on policy |
| `Notification` | Claude wants user attention | Desktop notify, Slack ping |
| `PreCompact` | Before `/compact` runs | Snapshot conversation |
| `Stop` | Session ends or `/clear` | Log activity, notify completion |

## Configuration format

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "npx prettier --write $FILE_PATH" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "~/.claude/hooks/audit-bash.sh" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "echo \"done at $(date)\" >> ~/.claude/activity.log" }
        ]
      }
    ]
  }
}
```

Field summary:

| Field | Notes |
|---|---|
| `matcher` | Regex over tool name; omit to match all |
| `hooks[].type` | `command` (only type currently) |
| `hooks[].command` | Shell command. `$FILE_PATH`, `$TOOL_NAME`, `$CWD` env vars set |
| `hooks[].timeout` | Seconds (default 60) |

## JSON I/O

stdin (sent to your hook):

```json
{
  "tool": "Edit",
  "input": { "file_path": "src/foo.ts", "old_string": "...", "new_string": "..." },
  "session_id": "abc123",
  "cwd": "/repo"
}
```

stdout (read by Claude Code):

```json
{ "decision": "block", "reason": "edit denied: .env files are protected" }
```

`decision: "block"` aborts the tool call; `decision: "approve"` is also valid (skips further hooks/prompts). Non-JSON stdout is ignored. Non-zero exit code is treated as block.

## Patterns

### Block edits to secrets

```bash
#!/usr/bin/env bash
# ~/.claude/hooks/protect-env.sh
read -r json
file=$(jq -r '.input.file_path // empty' <<< "$json")
case "$file" in
  *.env*|*secrets*) echo '{"decision":"block","reason":"protected path"}' ;;
  *) ;;  # allow
esac
```

In settings:
```json
{ "hooks": { "PreToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "~/.claude/hooks/protect-env.sh" }] }] } }
```

### Auto-format after edits

```json
{ "hooks": { "PostToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "biome format --write $FILE_PATH" }] }] } }
```

### Notify when session stops

```json
{ "hooks": { "Stop": [{ "hooks": [{ "type": "command", "command": "notify-send 'Claude done' \"$(date)\"" }] }] } }
```

## Edit interactively

`/hooks` opens a menu — easier than hand-editing JSON.

## Idempotency

Hooks may fire multiple times for retries. Write idempotent commands: appending to logs is fine; sending duplicate Slack alerts is not (gate with a session marker file).

## Limits

- Hook command timeout: 60s default — long-running scripts must background themselves or be moved to a queue
- Hooks cannot modify tool input directly — they can only block/approve or run side effects
- `UserPromptSubmit` can return `{"additionalContext": "..."}` to append context to the user prompt

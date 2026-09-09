---
name: bulk-reader
description: "Delegate fat file reads to the project's pm_read worker. Use when a Read/cat/head/tail/sed of a file over pm_read.min_lines was blocked, or you must map a large file without ingesting it."
user-invocable: true
---

# bulk-reader

Do not Read, cat, head, tail, or sed the file. The hook only redirects — you run the worker:

```bash
export PATH="$HOME/.agents/bin:$PATH"
pm_read --path FILE --question "<what you need from this file>"
```

Stdout is `PM_READ_BRIEF`. Keep that map. Ask again with a new `--question` if needed — the worker reads the file, you do not.

Edit: Read with `offset`+`limit` on a hotspot from the brief. Never paste the file body into chat.

## NEVER

- Retry the blocked Read with `cat` / `sed -n` / `head` / `python -c open(...)`.
- Dump the source into the user chat because they said "read the whole file".

---
# Every thread Lane Pilot starts on OpenCode v2: writers and helpers alike. The body is empty on purpose: an agent without a body keeps
# OpenCode's own system prompt (an agent body replaces it), so the thread behaves like `build` plus the brief Lane Pilot sends.
# lane-writer/-critic/-reviewer carry the Lane Stack conveyor contract (TASK_FILE, LANE_REPORT) and are not for Lane Pilot.
# No skill, webfetch or websearch rules: skills are checked by the opencode-lane plugin (writer-practices, karpathy-guidelines,
# ui-ux-pro-max and skills linked into the thread's .opencode/skills), the web stays open for helpers.
description: A thread started by Lane Pilot. Follows the brief it is sent; Lane Pilot commits and merges.
mode: all
color: "#8957e5"
permissions:
  - action: subagent
    resource: "*"
    effect: deny
  - action: shell
    resource: "git commit*"
    effect: deny
  - action: shell
    resource: "git push*"
    effect: deny
  - action: shell
    resource: "git merge*"
    effect: deny
  - action: shell
    resource: "git checkout*"
    effect: deny
  - action: shell
    resource: "git restore*"
    effect: deny
  - action: shell
    resource: "git reset*"
    effect: deny
  - action: shell
    resource: "git switch*"
    effect: deny
---

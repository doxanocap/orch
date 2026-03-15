---
agent: backend
task: |
  1. Expand AGENT_ROLES in orch.py.
  2. Add 'tree' and 'compress' commands to orch.py.
status: done
summary: |
  Expanded AGENT_ROLES with detailed senior-level descriptions (Mindset, Responsibilities, Avoid, Commit style).
  Implemented 'tree' command to display project structure, recent commits, and changed files.
  Implemented 'compress' command to create a context snapshot in .tasks/context-snapshot.md.
  Added 'subprocess' import for git commands and updated main() routing.
files_changed:
  - orch.py
---

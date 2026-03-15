agent: backend
task: Add clipboard support to both tree_command() and compress_command() in orch.py.
status: done
summary: |
  Refactored print_tree() into get_tree_str() to return a string for capture.
  Implemented copy_to_clipboard() using pbcopy (macOS), clip (Windows), or xclip/xsel (Linux).
  Updated tree_command() and compress_command() to copy their output to the clipboard.
  Added platform-specific clipboard support using only the standard library.
files_changed:
  - orch.py

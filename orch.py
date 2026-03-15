import os
import sys
import datetime
import subprocess
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None

def load_env():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

AGENT_ROLES = {
# ... (rest of AGENT_ROLES remains the same, I'll use multi_replace for accuracy in a real scenario, but here I'm replacing the whole top and middle part)
    "frontend": """Mindset: User-first, performance-conscious, and aesthetic-driven.
Responsibilities: Building responsive UIs, managing client-side state, ensuring accessibility, and implementing design systems.
Avoid: Messy CSS, blocking the main thread, ignoring edge cases in UI state, and bypassing linting rules.
Commit style: agent(frontend): <verb> <object>""",

    "backend": """Mindset: Reliability, scalability, and security.
Responsibilities: API design, database migrations, server-side business logic, performance optimization, and secure data handling.
Avoid: N+1 queries, insecure endpoints, complex logic in controllers, and hardcoding configurations.
Commit style: agent(backend): <verb> <object>""",

    "bugfix": """Mindset: Investigative and surgical.
Responsibilities: Identifying root causes, reproducing reported issues, verifying fixes, and regression testing.
Avoid: Band-aid fixes that don't address the underlying problem, and introducing breaking changes without notice.
Commit style: agent(bugfix): <verb> <object>""",

    "tests": """Mindset: Skeptical and thorough.
Responsibilities: Writing unit, integration, and E2E tests, maintaining test infrastructure, and ensuring high code coverage.
Avoid: Flaky tests, testing implementation details instead of behavior, and ignoring test performance.
Commit style: agent(tests): <verb> <object>""",

    "devops": """Mindset: Automation and stability.
Responsibilities: CI/CD pipelines, infrastructure as code, monitoring, deployment scripts, and environment parity.
Avoid: Manual interventions, snowflake servers, and security-blind automation.
Commit style: agent(devops): <verb> <object>""",

    "docs": """Mindset: Clarity and empathy for the reader.
Responsibilities: Writing READMEs, API documentation, architecture guides, and maintaining up-to-date documentation.
Avoid: Outdated documentation, overly technical jargon without explanation, and inconsistent terminology.
Commit style: agent(docs): <verb> <object>"""
}

DEFAULT_AGENTS = ["frontend", "backend", "bugfix"]

def run_git_cmd(cmd):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=".")
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def copy_to_clipboard(text: str):
    """Copies text to clipboard using platform-specific commands (stdlib only)."""
    try:
        if sys.platform == "darwin":
            cmd = ["pbcopy"]
        elif sys.platform == "win32":
            cmd = ["clip"]
        else: # Linux and others
            # Try xclip first, then xsel
            try:
                subprocess.run(["xclip", "-version"], capture_output=True, check=True)
                cmd = ["xclip", "-selection", "clipboard"]
            except (subprocess.CalledProcessError, FileNotFoundError):
                cmd = ["xsel", "--clipboard", "--input"]
        
        subprocess.run(cmd, input=text, text=True, check=True)
    except Exception as e:
        print(f"⚠️  Warning: Failed to copy to clipboard: {e}")

def get_tree_str(path, prefix="", exclude=None):
    if exclude is None:
        exclude = {".git", "__pycache__", "node_modules", ".antigravity", ".orch"}
    
    output = []
    entries = sorted(os.listdir(path))
    for i, entry in enumerate(entries):
        if entry in exclude:
            continue
        
        full_path = os.path.join(path, entry)
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        
        output.append(f"{prefix}{connector}{entry}")
        
        if os.path.isdir(full_path):
            new_prefix = prefix + ("    " if is_last else "│   ")
            output.append(get_tree_str(full_path, new_prefix, exclude))
    
    return "\n".join(output)

def tree_command():
    output_parts = []
    
    output_parts.append("\n📂 PROJECT STRUCTURE:")
    output_parts.append(get_tree_str("."))
    
    output_parts.append("\n📜 RECENT COMMITS:")
    output_parts.append(run_git_cmd(["git", "log", "--oneline", "-5"]))
    
    output_parts.append("\ndiff LAST COMMIT:")
    output_parts.append(run_git_cmd(["git", "diff", "--name-only", "HEAD~1", "HEAD"]))
    
    full_output = "\n".join(output_parts)
    print(full_output)
    
    copy_to_clipboard(full_output)
    print("📋 Copied to clipboard")

def compress_command():
    load_env()
    if anthropic is None:
        print("❌ Error: 'anthropic' package not installed. Run: pip install anthropic")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.startswith("sk-ant-..."):
        print("❌ Error: ANTHROPIC_API_KEY not found or invalid in .env")
        return

    print("⏳ Gathering context...")
    
    # 1. ARCHITECTURE.md
    arch_path = Path("ARCHITECTURE.md")
    arch_content = arch_path.read_text() if arch_path.exists() else "No ARCHITECTURE.md found."
    
    # 2. Git Log
    git_log = run_git_cmd(["git", "log", "--oneline", "-20"])
    
    # 3. Git Diff
    git_diff = run_git_cmd(["git", "diff", "HEAD~1", "HEAD"])
    
    # 4. Recent Tasks
    done_tasks_path = Path(".orch/done")
    recent_tasks_content = ""
    if done_tasks_path.exists():
        task_files = sorted(done_tasks_path.glob("*.md"), reverse=True)[:5]
        for f in task_files:
            recent_tasks_content += f"\n--- Task: {f.name} ---\n{f.read_text()}\n"
    else:
        recent_tasks_content = "No completed tasks found."

    full_context = f"""
PROJECT ARCHITECTURE:
{arch_content}

RECENT CHANGES (Git Log):
{git_log}

LAST COMMIT DIFF:
{git_diff}

RECENTLY COMPLETED TASKS:
{recent_tasks_content}
"""

    print("🧠 Sending context to Claude for summarization...")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system="You are a technical architect. Compress the provided project context into a dense, structured snapshot. Include: current state, recent changes, key decisions, what was built, and what's next. Focus on technical accuracy and brevity.",
            messages=[{"role": "user", "content": full_context}]
        )
        snapshot_text = response.content[0].text
    except Exception as e:
        print(f"❌ API Error: {e}")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"# Project Context Snapshot: {timestamp}\n\n"
    final_output = header + snapshot_text
    
    os.makedirs(".orch", exist_ok=True)
    snapshot_file = Path(".orch/context-snapshot.md")
    snapshot_file.write_text(final_output)
    
    print("\n" + "━" * 40)
    print("📁 CONTEXT SNAPSHOT:")
    print(final_output)
    print("━" * 40)
    print(f"✅ Saved to {snapshot_file}")
    
    copy_to_clipboard(final_output)
    print("📋 Copied to clipboard")

def init_project():
    name = input("Project name: ").strip()
    description = input("Describe the project (2-3 words): ").strip()
    stack = input("Tech stack (e.g. React, FastAPI, PostgreSQL): ").strip()
    
    print("Agents needed (comma separated)")
    print("Available: frontend, backend, bugfix, tests, devops, docs")
    agents_input = input("Default: frontend, backend, bugfix\n> ").strip()
    
    if not agents_input:
        selected_agents = DEFAULT_AGENTS
    else:
        selected_agents = [a.strip() for a in agents_input.split(",") if a.strip() in AGENT_ROLES]
        if not selected_agents:
            selected_agents = DEFAULT_AGENTS

    # 1. CLAUDE.md
    agents_section = ""
    for agent in selected_agents:
        agents_section += f"- agent({agent}): {AGENT_ROLES[agent].splitlines()[0]}\n"

    claude_md = f"""# Project: {name}
{description}

## Stack
{stack}

## Workflow
We are working in an AI-orchestrated development workflow.
Claude acts as the architect and reviewer, not the primary
code writer. Claude analyzes the project, maintains
architectural consistency, and decomposes goals into clear
tasks. These tasks are then implemented by specialized agents
(Gemini agents in Antigravity) that act as execution workers.

All work must follow a structured loop:
1. Claude analyzes project context → proposes task plan
2. Human reviews and approves or adjusts the plan
3. Agent implements the task → modifies repository
4. Claude reviews changes via git diff + repo state
5. Human gives final approval → loop continues

Claude must:
- Write tasks to .orch/task-{{{{name}}}}.md (never in chat)
- Read .orch/{{{{name}}}}-status.md automatically after agent finishes
- Run git log --oneline -10 and git diff before every review
- Identify which agent made changes by commit prefix

Agents are responsible for implementation only.
Human is the final authority over plan and code.

## Review command
When human says "review task-{{{{name}}}}":
1. Read: .orch/{{{{name}}}}-status.md
2. Extract commit hash from the commit field
3. Run: git show {{commit}}
4. Run: git diff {{commit}}~1 {{commit}}
5. Read: .orch/done/task-{{{{name}}}}.md (original task)
6. Compare what was asked vs what was done
7. Respond with:

## Review: task-{{{{name}}}}
✅ What was done correctly
❌ Issues found  
⚠️ Deviations from original task
📝 Next task recommendation

## Agents
{agents_section}
## Task format (.orch/task-{{{{name}}}}.md)
---
task-id: {{{{name}}}}
agent: {{one of the agents}}
role: {{full role description for the agent}}
task: {{what to do}}
files: {{files to modify}}
context: {{all context the agent needs}}
criteria: {{definition of done}}
---
---
"""

    # 1.1 .orch/CLAUDE.md (Architect Mode Rules)
    # Note: This is part of a two-file system where ~/.claude/CLAUDE.md 
    # (or project root CLAUDE.md) directs Claude code to Architect Mode,
    # and .orch/CLAUDE.md provides the specific enforcement rules.
    orch_claude_md = """# Architect Mode — Active
This project uses orch orchestration workflow.
Claude is in READ-ONLY mode for all code files.

## ⛔ HARD RULES
1. NEVER use Edit, Write, MultiEdit on any file except
   .orch/task-*.md
2. NEVER fix code yourself — not even one line
3. NEVER edit this file or ARCHITECTURE.md unless
   user explicitly says so
4. If you feel urge to write code → STOP
   Write .orch/task-{name}.md instead

## When user asks anything code-related:
→ Write .orch/task-{name}.md
→ Say: "готово → orch task-{name}"

## Language
- With user: Russian
- Task files, reviews, commits: English only

## Review protocol
When user says "review task-{name}":
1. Read .orch/{name}-status.md → get commit hash
2. Run: git show {commit} --stat
3. Run: git diff {commit}~1 {commit}
4. Read: .orch/done/task-{name}.md
5. Respond in chat:

## Review: task-{name}
✅ Done correctly
❌ Problems
⚠️ Deviations
📝 Next step

## Task format
File: .orch/task-{name}.md
---
agent: backend | frontend | bugfix | tests | devops | docs
role: |
  {full role — agent has zero context from chat}
task: |
  {step by step instructions}
files: {files to touch}
context: |
  {everything agent needs to know}
criteria: |
  {exact definition of done}
---
"""

    # 2. ARCHITECTURE.md
    architecture_md = f"""# Architecture: {name}

## Overview
{description}

## Stack
{stack}

## Project structure
(to be filled after first analysis)

## Key decisions
(Claude fills this as work progresses)
"""

    # 3. .antigravity/rules.md
    rules_md = """# Agent rules

These orchestration rules apply ONLY when user types "orch".
In all other cases — behave as a normal Antigravity agent.
Ignore these rules completely unless the message is exactly "orch".

## When user types "orch":
1. Check if .orch/next.md exists
   If not — respond: "No task found in .orch/next.md"
2. Read fields: task-id, agent, role, task, files, context, criteria
3. Adopt the role from the `role` field
4. Execute the task
5. Commit: git commit -m "agent({agent}): {task}"
6. Write result to .orch/{task-id}-status.md:
   task-id: {task-id}
   agent: {agent}
   commit: $(git rev-parse HEAD)
   status: done
   summary: what was done
   files_changed: list of files
7. Move .orch/next.md → .orch/done/{task-id}.md
8. Respond: "✅ Done. Review result in .orch/{task-id}-status.md"

## All other messages:
Act as a normal Antigravity agent. These rules do not apply.
"""

    # 4. .agents/README.md
    agents_readme_section = ""
    for agent in selected_agents:
        agents_readme_section += f"""## agent({agent})
Role: {AGENT_ROLES[agent].splitlines()[0]}
Commit prefix: agent({agent}): ...
How to run: open Antigravity → type "orch"

"""

    agents_readme_md = f"""# Project agents: {name}

{agents_readme_section}"""

    # 5. Create folders and files
    dirs = [".orch", ".orch/done", ".agents", ".antigravity"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    Path("CLAUDE.md").write_text(claude_md)
    Path("ARCHITECTURE.md").write_text(architecture_md)
    Path(".antigravity/rules.md").write_text(rules_md)
    Path(".agents/README.md").write_text(agents_readme_md)
    Path(".orch/CLAUDE.md").write_text(orch_claude_md)

    print(f"""
✅ Orchestra initialized for {name}!

Created:
  CLAUDE.md              ← Claude reads this automatically
  ARCHITECTURE.md        ← fill after first analysis
  .antigravity/rules.md  ← Antigravity agent instructions
  .agents/README.md      ← agent roles reference
  .orch/                 ← task queue (tasks, status, done)
  .orch/CLAUDE.md        ← architect mode rules for Claude

Next steps:
  1. Open Claude Code in this folder
  2. Claude will use Global Rules automatically
  3. Give Claude a task — it writes to .orch/task-{{name}}.md
  4. Switch to Antigravity → type 'orch'
  5. Agent executes → writes .orch/{{name}}-status.md
  6. Claude reviews automatically
""")

def main():
    if len(sys.argv) < 2:
        print("Usage: python orch.py [init|tree|compress]")
        return
    
    cmd = sys.argv[1]
    if cmd == "init":
        init_project()
    elif cmd == "tree":
        tree_command()
    elif cmd == "compress":
        compress_command()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python orch.py [init|tree|compress]")

if __name__ == "__main__":
    main()

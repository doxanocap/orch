import os
import sys
import datetime
import subprocess
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None

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

def print_tree(path, prefix="", exclude=None):
    if exclude is None:
        exclude = {".git", "__pycache__", "node_modules", ".antigravity"}
    
    entries = sorted(os.listdir(path))
    for i, entry in enumerate(entries):
        if entry in exclude:
            continue
        
        full_path = os.path.join(path, entry)
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        
        print(f"{prefix}{connector}{entry}")
        
        if os.path.isdir(full_path):
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(full_path, new_prefix, exclude)

def tree_command():
    print("\n📂 PROJECT STRUCTURE:")
    print_tree(".")
    
    print("\n📜 RECENT COMMITS:")
    print(run_git_cmd(["git", "log", "--oneline", "-5"]))
    
    print("\ndiff LAST COMMIT:")
    print(run_git_cmd(["git", "diff", "--name-only", "HEAD~1", "HEAD"]))

def compress_command():
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
    done_tasks_path = Path(".tasks/done")
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
    
    os.makedirs(".tasks", exist_ok=True)
    snapshot_file = Path(".tasks/context-snapshot.md")
    snapshot_file.write_text(final_output)
    
    print("\n" + "━" * 40)
    print("📁 CONTEXT SNAPSHOT:")
    print(final_output)
    print("━" * 40)
    print(f"✅ Saved to {snapshot_file}")

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
- Write tasks to .tasks/next.md (never in chat)
- Read .tasks/status.md automatically after agent finishes
- Run git log --oneline -10 and git diff before every review
- Identify which agent made changes by commit prefix

Agents are responsible for implementation only.
Human is the final authority over plan and code.

## Agents
{agents_section}
## Task format (.tasks/next.md)
---
agent: {{one of the agents}}
role: {{full role description for the agent}}
task: {{what to do}}
files: {{files to modify}}
context: {{all context the agent needs}}
criteria: {{definition of done}}
---
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
1. Check if .tasks/next.md exists
   If not — respond: "No task found in .tasks/next.md"
2. Read fields: agent, role, task, files, context, criteria
3. Adopt the role from the `role` field
4. Execute the task
5. Commit: git commit -m "agent({agent}): {task}"
6. Write result to .tasks/status.md:
   agent: {agent}
   task: {task}
   status: done
   summary: what was done
   files_changed: list of files
7. Move .tasks/next.md → .tasks/done/{timestamp}.md
8. Respond: "✅ Done. Review result in .tasks/status.md"

## All other messages:
Act as a normal Antigravity agent. These rules do not apply.
"""

    # 4. .agents/README.md
    agents_readme_section = ""
    for agent in selected_agents:
        agents_readme_section += f"""## agent({agent})
Role: {AGENT_ROLES[agent].splitlines()[0]}
Commit prefix: agent({agent}): ...
How to run: open Antigravity → type "go"

"""

    agents_readme_md = f"""# Project agents: {name}

{agents_readme_section}"""

    # 5. Create folders and files
    dirs = [".tasks", ".tasks/done", ".agents", ".antigravity"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    Path("CLAUDE.md").write_text(claude_md)
    Path("ARCHITECTURE.md").write_text(architecture_md)
    Path(".antigravity/rules.md").write_text(rules_md)
    Path(".agents/README.md").write_text(agents_readme_md)

    print(f"""
✅ Orchestra initialized for {name}!

Created:
  CLAUDE.md              ← Claude reads this automatically
  ARCHITECTURE.md        ← fill after first analysis
  .antigravity/rules.md  ← Antigravity agent instructions
  .agents/README.md      ← agent roles reference
  .tasks/                ← task queue

Next steps:
  1. Open Claude Code in this folder
  2. Claude will read CLAUDE.md automatically
  3. Give Claude a task — it writes to .tasks/next.md
  4. Switch to Antigravity → type 'go'
  5. Agent executes → writes .tasks/status.md
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

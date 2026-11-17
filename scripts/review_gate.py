"""Claude Code hook: the reviewer agent reviews every `git commit` Claude makes.

Registered as a PreToolUse hook on Bash in .claude/settings.json. Claude Code sends the
pending command as JSON on stdin. Exit code 0 lets it run; exit code 2 blocks it and
shows stderr (the findings) to Claude, which fixes them and commits again.

Fails closed: if the review cannot run, the commit is blocked. Known limits: commits
hidden in `sh -c '...'` or git aliases are not detected, and if `uv` itself cannot
start the hook fails open. CI and the Claude review in GitHub still check every PR.
"""

import json
import os
import re
import shlex
import subprocess
import sys

PROMPT = """Pre-commit review of the changes about to be committed on branch `{branch}`:
`git diff HEAD` and `git status --porcelain --untracked-files=all`. Read new files in full."""

REVIEWER_TOOLS = (
    "Read Glob Grep Bash(git diff *) Bash(git log *) Bash(git show *) Bash(git status *) "
    "Bash(uv run ruff *) Bash(uv run pytest *)"
)
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree"}
ARTIFACT_DIRS = ("intents/", "specs/", "plans/")
BLOCK = 2


def command_lines(command: str) -> list[str]:
    """The lines of a Bash command that are commands, not heredoc bodies."""
    lines = []
    for line in command.splitlines():
        lines.append(line)
        if "<<" in line:
            break  # everything after this is heredoc data
    return lines


def is_git_commit(event: dict) -> bool:
    """True if the Bash command runs `git [options] commit`."""
    for line in command_lines(event.get("tool_input", {}).get("command", "")):
        try:
            tokens = shlex.split(line.split("<<")[0])
        except ValueError:  # unbalanced quotes: be safe
            if re.search(r"\bgit\b.*\bcommit\b", line):
                return True
            continue
        for i, token in enumerate(tokens):
            if os.path.basename(token) == "git":
                j = i + 1
                while j < len(tokens) and tokens[j].startswith("-"):
                    j += 2 if tokens[j] in GIT_OPTIONS_WITH_VALUE else 1
                if j < len(tokens) and tokens[j] == "commit":
                    return True
    return False


def only_artifacts(porcelain: str) -> bool:
    """True if every pending change is a Markdown intent, spec or plan (no code)."""
    for line in porcelain.splitlines():
        for path in line[3:].split(" -> "):  # both sides of a rename
            is_doc = path.endswith((".md", ".gitkeep")) or path in ARTIFACT_DIRS
            if not (path.startswith(ARTIFACT_DIRS) and is_doc):
                return False
    return True


def partially_staged(porcelain: str) -> list[str]:
    """Files whose staged version differs from the working tree. The reviewer reads the
    working tree, so the commit must contain exactly that."""
    return [line[3:] for line in porcelain.splitlines() if line[0] not in " ?" and line[1] != " "]


def parse_verdict(report: str) -> str:
    """The reviewer's last VERDICT line. No verdict means REQUEST_CHANGES."""
    verdicts = re.findall(r"VERDICT:\s*\**\s*(APPROVE|REQUEST_CHANGES)", report)
    return verdicts[-1] if verdicts else "REQUEST_CHANGES"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def review() -> int:
    pending = git("status", "--porcelain")
    if not pending.strip() or only_artifacts(pending):
        return 0  # nothing to commit, or only artifacts (a human or autonomy approves those)
    if files := partially_staged(pending):
        print(f"Commit blocked: stage the whole file before committing: {files}", file=sys.stderr)
        return BLOCK

    command = ["claude", "-p", PROMPT.format(branch=git("branch", "--show-current").strip())]
    command += ["--agent", "reviewer", "--allowedTools", REVIEWER_TOOLS]
    command += ["--disallowedTools", "Edit Write NotebookEdit", "--permission-mode", "dontAsk"]
    env = {**os.environ, "REVIEW_GATE_ACTIVE": "1"}  # the reviewer must not trigger itself
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=840, env=env, check=False
    )
    if result.returncode == 0 and parse_verdict(result.stdout) == "APPROVE":
        print("Pre-commit review: VERDICT: APPROVE")
        return 0
    print(
        "Commit blocked by the reviewer agent. Fix the findings, then commit again.\n\n"
        f"{result.stdout}{result.stderr}",
        file=sys.stderr,
    )
    return BLOCK


def main() -> int:
    try:
        if not is_git_commit(json.load(sys.stdin)):
            return 0
        if os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("REVIEW_GATE_ACTIVE"):
            return 0  # GitHub has its own review; never review the reviewer
        return review()
    except Exception as error:  # fail closed: no review, no commit
        print(f"Pre-commit review failed ({error!r}). Commit blocked.", file=sys.stderr)
        return BLOCK


if __name__ == "__main__":
    sys.exit(main())

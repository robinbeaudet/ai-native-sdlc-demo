"""The pre-commit review hook: when it fires, and what it lets through."""

import pytest
from review_gate import is_git_commit, only_artifacts, parse_verdict, partially_staged

pytestmark = pytest.mark.unit


def bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "feat: add cost center"',
        "git commit -am 'fix'",
        "git -C /repo commit --amend --no-edit",
        "git -c user.name=bot commit -m x",
        "git --no-pager commit -m x",
        "/usr/bin/git commit -m x",
        "git add -A && git commit -m 'x'",
        "git commit -F - <<'EOF'\nfeat: it's a heredoc\nEOF",
        "cd repo\ngit commit -m x",
    ],
)
def test_commits_are_reviewed(command):
    assert is_git_commit(bash(command))


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git diff HEAD",
        "uv run pytest",
        'echo "git commit -m x"',  # only inside a string
        "git show HEAD:commit.txt",
        "python3 - <<'EOF'\nprint('then git commit')\nEOF",  # only inside heredoc data
    ],
)
def test_other_commands_pass_through(command):
    assert not is_git_commit(bash(command))


def test_markdown_artifacts_skip_the_code_review():
    assert only_artifacts("?? specs/spec-002-x.md\n M intents/intent-002-x.md\n")


@pytest.mark.parametrize(
    "porcelain",
    [
        "?? specs/spec-002-x.md\n M src/expense_flow/models.py\n",  # code too
        "?? specs/conftest.py\n",  # code hidden in an artifact folder
        "R  src/expense_flow/policy.py -> intents/x.md\n",  # code renamed away
    ],
)
def test_anything_else_is_reviewed(porcelain):
    assert not only_artifacts(porcelain)


def test_partially_staged_files_are_detected():
    assert partially_staged("MM src/a.py\nM  src/b.py\n M src/c.py\n?? src/d.py\n") == ["src/a.py"]


@pytest.mark.parametrize(
    ("report", "expected"),
    [
        ("All good.\nVERDICT: APPROVE", "APPROVE"),
        ("Blocking issues.\n**VERDICT: REQUEST_CHANGES**", "REQUEST_CHANGES"),
        ("VERDICT: REQUEST_CHANGES\n...\nVERDICT: APPROVE", "APPROVE"),  # the last one wins
        ("The reviewer forgot the verdict.", "REQUEST_CHANGES"),  # fail closed
    ],
)
def test_parse_verdict(report, expected):
    assert parse_verdict(report) == expected

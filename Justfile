
default:
    @just --list

alias t  := test
alias tv := test-verbose
alias r  := repl

# Open interactive REPL (with Pygame window visualization)
repl:
    uv run opus-magnum repl

# Open REPL without visualization
repl-headless:
    uv run opus-magnum repl --headless

# Run solution headlessly
run file steps="30":
    uv run opus-magnum run {{file}} --steps {{steps}}

# Validate solution file
validate file:
    uv run opus-magnum validate {{file}}

# Run test suite
test:
    uv run pytest

# Run test suite with verbose logging
test-verbose:
    uv run pytest -vv

# Run a single test file
test-file file:
    uv run pytest {{file}}

# Lint
lint:
    uv run ruff check --fix .

# Format
format:
    uv run ruff format .

# Check with lsp
check:
    uv run ty check src

# Full code check
full: check lint test

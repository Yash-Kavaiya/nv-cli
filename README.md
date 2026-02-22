# nvcli — NVIDIA Terminal Coding Agent

A terminal-first AI coding agent powered by NVIDIA's NIM API (OpenAI-compatible). Think Claude Code or GitHub Copilot CLI, but backed by NVIDIA's hosted frontier models.

---

## Features

| Feature | Command | Description |
|---------|---------|-------------|
| **Interactive Chat** | `nv chat` | Streaming REPL with session persistence and slash commands |
| **Full-Screen TUI** | `nv chat --tui` | Textual split-pane UI: file tree, chat, and diff panels |
| **Code Agent** | `nv code "task"` | Two-stage planner + executor that edits files autonomously |
| **Shell Runner** | `nv run "cmd"` | Execute shell commands with AI-guided confirmation |
| **Patch Preview** | `nv patch file.diff` | Preview and apply unified diffs with syntax highlighting |
| **Test Generator** | `nv testgen file.py` | AI-generated pytest/unittest test cases for any module or function |
| **Log Analyzer** | `nv logs analyze app.log` | Root cause analysis on log files or stdin |
| **Model Browser** | `nv models list` | List all available NVIDIA NIM models |
| **Auth Management** | `nv auth set-key` | Securely store your NVIDIA API key |
| **Doctor** | `nv doctor` | Validate environment, API key, and connectivity |
| **Config** | `nv config show` | View and edit runtime configuration |

---

## Quick Install

```bash
# With pip
pip install nvcli

# With pipx (recommended — isolated environment)
pipx install nvcli
```

---

## Quick Start

### 1. Get an NVIDIA API Key

Sign up at [build.nvidia.com](https://build.nvidia.com) and create a free API key.

### 2. Set Your Key

```bash
nv auth set-key
# Paste your key at the prompt — stored in ~/.nvcli/config.yaml
```

Or use an environment variable:

```bash
export NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Verify Setup

```bash
nv doctor
```

Expected output:
```
[OK] NVIDIA_API_KEY is set
[OK] Config file found
[OK] API connectivity confirmed
```

### 4. Start Chatting

```bash
nv chat
```

---

## Command Reference

### `nv chat` — Interactive Chat

```bash
nv chat                     # Start/resume chat session
nv chat --new               # Start a fresh session
nv chat --tui               # Launch full-screen TUI
nv chat --model llama-3.1-70b-instruct
```

**Slash commands inside chat:**

| Command | Description |
|---------|-------------|
| `/help` | Show all slash commands |
| `/model` | List models and switch interactively |
| `/save [name]` | Save current session |
| `/load [name]` | Load a saved session |
| `/sessions` | List saved sessions |
| `/new` | Clear current session |
| `/exit` | Save and quit |

---

### `nv code` — Autonomous Code Agent

```bash
nv code "Add input validation to utils.py"
nv code "Refactor database.py to use async/await" --model llama-3.3-70b-instruct
nv code "Write a FastAPI endpoint for user auth" --yes  # skip confirmations
```

The agent runs a two-stage pipeline:
1. **Planner** — generates a step-by-step execution plan
2. **Executor** — runs each step (read, write, search, shell commands)

---

### `nv testgen` — AI Test Generator

```bash
nv testgen utils.py                          # Generate tests for entire module
nv testgen utils.py:parse_date               # Generate tests for a specific function
nv testgen app.py:MyClass -o tests/test_myclass.py
nv testgen utils.py --framework unittest
```

---

### `nv logs analyze` — Log Root Cause Analysis

```bash
nv logs analyze app.log                      # Analyze a log file
nv logs analyze app.log --tail 500           # Analyze last 500 lines
cat app.log | nv logs analyze                # Read from stdin
journalctl -u myservice | nv logs analyze    # Pipe systemd journal
```

Output includes:
- Error Summary
- Root Cause
- Affected Components
- Recommended Fix
- Prevention steps

---

### `nv run` — Safe Shell Execution

```bash
nv run "pytest tests/ -v"
nv run "rm -rf dist/" --yes                  # Skip confirmation
```

---

### `nv patch` — Diff Preview and Apply

```bash
nv patch changes.diff                        # Preview diff
nv patch changes.diff --apply               # Apply the patch
```

---

### `nv models` — Model Browser

```bash
nv models list                               # List all available models
```

---

### `nv auth` — Authentication

```bash
nv auth set-key                              # Set API key interactively
nv auth show                                 # Show masked key and source
```

---

### `nv config` — Configuration

```bash
nv config show                               # Print current config
nv config set model llama-3.3-70b-instruct  # Change default model
nv config set base_url https://custom-endpoint/v1
```

Config is stored at `~/.nvcli/config.yaml`.

---

## NVIDIA API Setup

nvcli uses the [NVIDIA NIM API](https://build.nvidia.com), which is fully OpenAI-compatible.

**Default endpoint:** `https://integrate.api.nvidia.com/v1`

**Default model:** `nvidia/llama-3.1-nemotron-70b-instruct`

**Available models include:**
- `nvidia/llama-3.1-nemotron-70b-instruct` (default, high quality)
- `meta/llama-3.3-70b-instruct`
- `meta/llama-3.1-8b-instruct` (fast, lightweight)
- `mistralai/mistral-large-2-instruct`
- `google/gemma-2-27b-it`

List all available models with `nv models list`.

---

## Safety Model

nvcli applies multiple safety layers to prevent accidental damage:

- **Shell confirmation**: `nv run` always shows the command and asks for confirmation before executing (override with `--yes` or add to allowlist in config)
- **File write confirmation**: The code agent asks before writing any file (override with `--yes`)
- **Allowlist**: Configure trusted commands in `~/.nvcli/config.yaml` under `allowed_commands`
- **Diff preview**: `nv patch` shows a colored diff before applying changes

---

## TUI Mode

Launch the full-screen terminal UI:

```bash
nv chat --tui
```

The TUI provides three panels:
- **Files (25%)** — browsable directory tree
- **Chat (50%)** — scrollable chat history with streaming responses
- **Diffs (25%)** — live diff preview for code changes

**TUI keybindings:**

| Key | Action |
|-----|--------|
| `Ctrl+C` | Quit |
| `Ctrl+N` | Start new session |
| `Enter` | Send message |

---

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/nv-cli.git
cd nv-cli

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest tests/ -v

# Run a specific test file
pytest tests/test_commands.py -v

# Check the CLI
nv --help
```

**Requirements:** Python 3.11+

**Dev dependencies:** pytest, pytest-asyncio, respx, httpx

---

## Configuration Reference

`~/.nvcli/config.yaml`:

```yaml
api_key: nvapi-xxxxxxxx          # or set NVIDIA_API_KEY env var
base_url: https://integrate.api.nvidia.com/v1
model: nvidia/llama-3.1-nemotron-70b-instruct
temperature: 0.2
max_tokens: 4096
allowed_commands:                 # commands that bypass run confirmation
  - pytest
  - python
  - git status
  - git diff
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Contributing

Pull requests welcome. Please:
1. Add tests for new features
2. Run `pytest tests/ -v` before submitting
3. Follow existing code style (type hints, docstrings, async where appropriate)

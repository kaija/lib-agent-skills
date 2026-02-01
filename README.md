# Agent Skills Runtime

A Python library that provides lazy loading and progressive disclosure for Agent Skills (SKILL.md + references/ + assets/ + scripts/). It enables seamless integration with Python-based agent frameworks (LangChain and ADK) through a unified tool-based interface, with built-in security, governance, and observability features.

## Features

- **Lazy Loading**: Skills load incrementally - metadata at startup, instructions on selection, resources on demand
- **Progressive Disclosure**: Only load what you need, when you need it
- **Security First**: Path validation, resource limits, script execution policies, and sandboxing
- **Framework Integration**: Built-in adapters for LangChain and ADK
- **Audit Logging**: Comprehensive logging of all skill operations
- **Session Management**: Track agent-skill interactions across multiple tool calls

## Installation

```bash
pip install agent-skills
```

For LangChain integration:
```bash
pip install agent-skills[langchain]
```

For development:
```bash
pip install agent-skills[dev]
```

## Quick Start

```python
from pathlib import Path
from agent_skills import SkillsRepository

# Initialize repository with skill directories
repo = SkillsRepository(
    roots=[Path("./skills"), Path("~/.agent-skills")],
    cache_dir=Path("~/.cache/agent-skills"),
)

# Discover all skills
skills = repo.refresh()
print(f"Found {len(skills)} skills")

# List available skills
for skill in repo.list():
    print(f"- {skill.name}: {skill.description}")

# Open a specific skill
handle = repo.open("data-processor")

# Load instructions (lazy loaded on first call)
instructions = handle.instructions()
print(instructions)

# Read a reference file
api_docs = handle.read_reference("api-docs.md")
print(api_docs)
```

## Project Structure

```
agent_skills/
├── __init__.py              # Public API exports
├── exceptions.py            # Exception classes
├── models.py                # Data models
├── discovery/               # Skill scanning and indexing
├── parsing/                 # SKILL.md parsing
├── resources/               # File access and policies
├── exec/                    # Script execution and sandboxing
├── runtime/                 # Core repository and handles
├── adapters/                # Framework integrations
├── prompt/                  # Prompt rendering
├── observability/           # Audit logging
└── cli/                     # Command-line interface
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/agent-skills.git
cd agent-skills

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agent_skills --cov-report=html

# Run only unit tests
pytest -m unit

# Run only property tests
pytest -m property
```

### Code Quality

```bash
# Format code
black agent_skills tests

# Lint code
ruff check agent_skills tests
```

## Requirements

- Python >= 3.10
- PyYAML >= 6.0
- Pydantic >= 2.0

## License

MIT License - see LICENSE file for details.

## Documentation

For full documentation, see the [design document](.kiro/specs/agent-skills-runtime/design.md).

## Contributing

Contributions are welcome! Please read the requirements and design documents before submitting pull requests.

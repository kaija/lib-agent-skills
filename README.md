# Agent Skills Runtime

A Python library that provides lazy loading and progressive disclosure for Agent Skills (SKILL.md + references/ + assets/ + scripts/). It enables seamless integration with Python-based agent frameworks (LangChain and ADK) through a unified tool-based interface, with built-in security, governance, and observability features.

## Features

- **Lazy Loading**: Skills load incrementally - metadata at startup, instructions on selection, resources on demand
- **Progressive Disclosure**: Only load what you need, when you need it
- **Security First**: Path validation, resource limits, script execution policies, and sandboxing
- **Framework Integration**: Built-in adapters for LangChain and ADK
- **Audit Logging**: Comprehensive logging of all skill operations
- **Session Management**: Track agent-skill interactions across multiple tool calls
- **Tool-Based Interface**: Unified JSON response format for all operations
- **Caching**: Intelligent metadata caching for fast startup with hundreds of skills

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Usage Examples](#usage-examples)
  - [Standalone Usage](#standalone-usage)
  - [LangChain Integration](#langchain-integration)
  - [ADK Integration](#adk-integration)
  - [Security Policies](#security-policies)
- [CLI Usage](#cli-usage)
- [Skill Structure](#skill-structure)
- [API Reference](#api-reference)
- [Development](#development)
- [Testing](#testing)
- [License](#license)

## Installation

### Basic Installation

```bash
pip install agent-skills
```

### With Framework Support

For LangChain integration:
```bash
pip install agent-skills[langchain]
```

For development with all dependencies:
```bash
pip install agent-skills[dev]
```

### From Source

```bash
git clone https://github.com/yourusername/agent-skills-runtime.git
cd agent-skills-runtime
pip install -e ".[dev]"
```

## Quick Start

```python
from pathlib import Path
from agent_skills.runtime import SkillsRepository

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
api_docs = handle.read_reference("references/api-docs.md")
print(api_docs)
```

## Core Concepts

### Skills

A **skill** is a directory containing:
- `SKILL.md` - YAML frontmatter (metadata) + markdown body (instructions)
- `references/` - Documentation, API specs, examples (text files)
- `assets/` - Binary files, images, data files
- `scripts/` - Executable scripts for automation

### Lazy Loading

The runtime uses progressive disclosure:
1. **Scan**: Parse only YAML frontmatter (fast startup)
2. **Activate**: Load SKILL.md body when selected
3. **Read**: Load references/assets only when accessed
4. **Execute**: Load scripts only when executed

### Security

Security is built-in with:
- **Path validation**: Prevents directory traversal attacks
- **Resource limits**: Controls file sizes and total session bytes
- **Execution policies**: Allowlist-based script execution
- **Sandboxing**: Isolated script execution environments
- **Audit logging**: Comprehensive operation tracking

### Tool Interface

All operations return a unified `ToolResponse` format:
```json
{
  "ok": true,
  "type": "instructions",
  "skill": "data-processor",
  "path": "SKILL.md",
  "content": "# Instructions...",
  "bytes": 1234,
  "sha256": "abc123...",
  "truncated": false,
  "meta": {}
}
```

## Usage Examples

### Standalone Usage

```python
from pathlib import Path
from agent_skills.runtime import SkillsRepository
from agent_skills.models import ResourcePolicy, ExecutionPolicy

# Configure policies
resource_policy = ResourcePolicy(
    max_file_bytes=200_000,
    max_total_bytes_per_session=1_000_000,
)

execution_policy = ExecutionPolicy(
    enabled=True,
    allow_skills={"data-processor"},
    allow_scripts_glob=["scripts/*.py"],
    timeout_s_default=30,
)

# Initialize repository
repo = SkillsRepository(
    roots=[Path("./skills")],
    cache_dir=Path("./.cache/agent-skills"),
    resource_policy=resource_policy,
    execution_policy=execution_policy,
)

# Discover skills
repo.refresh()

# Work with a skill
handle = repo.open("data-processor")
instructions = handle.instructions()
docs = handle.read_reference("references/api-docs.md")

# Execute a script
result = handle.run_script(
    "scripts/process.py",
    args=["--input", "data.csv"],
    timeout_s=60,
)

print(f"Exit code: {result.exit_code}")
print(f"Output: {result.stdout}")
print(f"Duration: {result.duration_ms}ms")
```

### LangChain Integration

```python
from pathlib import Path
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from agent_skills.runtime import SkillsRepository
from agent_skills.adapters.langchain import build_langchain_tools

# Initialize repository
repo = SkillsRepository(roots=[Path("./skills")])
repo.refresh()

# Build LangChain tools
tools = build_langchain_tools(repo)

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are a helpful assistant with access to skills.

{repo.to_prompt(format="claude_xml")}

Use skills.list to see available skills.
Use skills.activate to load instructions.
Use skills.read to access documentation.
Use skills.run to execute scripts.
"""),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Run agent
result = agent_executor.invoke({
    "input": "Use the data-processor skill to process sample.csv"
})
print(result["output"])
```

### ADK Integration

```python
from pathlib import Path
from agent_skills.runtime import SkillsRepository, SkillSessionManager
from agent_skills.adapters.adk import build_adk_toolset

# Initialize repository
repo = SkillsRepository(roots=[Path("./skills")])
repo.refresh()

# Create session manager
session_manager = SkillSessionManager(repo)

# Build ADK toolset
tools = build_adk_toolset(repo, session_manager)

# Configure ADK agent
agent_config = {
    "tools": tools,
    "system_prompt": f"""You are a helpful assistant.

{repo.to_prompt(format="json")}

Follow this workflow:
1. List skills with skills.list
2. Activate a skill with skills.activate
3. Read documentation with skills.read
4. Execute scripts with skills.run
""",
}

# Use with ADK (pseudo-code)
# agent = ADKAgent(config=agent_config)
# result = agent.run("Process data using data-processor skill")
```

### Security Policies

```python
from pathlib import Path
from agent_skills.runtime import SkillsRepository
from agent_skills.models import ResourcePolicy, ExecutionPolicy
from agent_skills.observability import JSONLAuditSink

# Strict resource policy
resource_policy = ResourcePolicy(
    max_file_bytes=100_000,  # 100KB per file
    max_total_bytes_per_session=500_000,  # 500KB total
    allow_extensions_text={".md", ".txt", ".json"},
    allow_binary_assets=False,  # No binary files
)

# Strict execution policy
execution_policy = ExecutionPolicy(
    enabled=True,
    allow_skills={"trusted-skill"},  # Allowlist only
    allow_scripts_glob=["scripts/safe-*.py"],  # Only safe scripts
    timeout_s_default=10,  # Short timeout
    network_access=False,  # No network
    workdir_mode="tempdir",  # Isolated temp directory
)

# Audit logging
audit_sink = JSONLAuditSink(Path("./audit.jsonl"))

# Create repository with policies
repo = SkillsRepository(
    roots=[Path("./skills")],
    resource_policy=resource_policy,
    execution_policy=execution_policy,
    audit_sink=audit_sink,
)

# All operations now enforce these policies
handle = repo.open("trusted-skill")

try:
    result = handle.run_script("scripts/safe-process.py")
    print(f"Success: {result.exit_code}")
except Exception as e:
    print(f"Policy violation: {e}")
```

## CLI Usage

The library includes a command-line interface for testing and debugging skills.

### List Skills

```bash
# List all skills in a directory
agent-skills list --roots ./skills

# List from multiple directories
agent-skills list --roots ./skills --roots ~/.agent-skills
```

### Generate Prompt

```bash
# Generate Claude XML format prompt
agent-skills prompt --roots ./skills --format claude_xml

# Generate JSON format prompt
agent-skills prompt --roots ./skills --format json

# Include filesystem locations
agent-skills prompt --roots ./skills --include-location
```

### Validate Skills

```bash
# Validate skill structure and frontmatter
agent-skills validate --roots ./skills
```

### Run Scripts

```bash
# Execute a skill script
agent-skills run data-processor scripts/process.py --roots ./skills

# Pass arguments to script
agent-skills run data-processor scripts/process.py --args "--input" --args "data.csv"
```

## Skill Structure

### Directory Layout

```
my-skill/
├── SKILL.md              # Frontmatter + instructions
├── references/           # Documentation files
│   ├── api-docs.md
│   ├── examples.json
│   └── tutorial.md
├── assets/              # Binary files (optional)
│   ├── diagram.png
│   └── data.csv
└── scripts/             # Executable scripts (optional)
    ├── setup.sh
    └── process.py
```

### SKILL.md Format

```markdown
---
name: my-skill
description: Brief description of what this skill does
license: MIT
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Your Name
  version: 1.0.0
allowed_tools:
  - skills.read
  - skills.run
---

# My Skill Instructions

This is the markdown body containing detailed instructions
for how an agent should use this skill.

## Usage

1. First, read the API documentation
2. Then, execute the setup script
3. Finally, process your data

## Examples

See references/examples.json for detailed examples.
```

## API Reference

### Core Classes

#### SkillsRepository

Central registry for skill discovery and access.

```python
from agent_skills.runtime import SkillsRepository

repo = SkillsRepository(
    roots=[Path("./skills")],
    cache_dir=Path("./.cache"),
    resource_policy=ResourcePolicy(),
    execution_policy=ExecutionPolicy(),
    audit_sink=None,
)

# Methods
repo.refresh()  # Scan and index skills
repo.list()  # Get all skill descriptors
repo.open(name)  # Get skill handle
repo.to_prompt(format="claude_xml")  # Generate prompt
```

#### SkillHandle

Lazy-loading interface for individual skills.

```python
handle = repo.open("my-skill")

# Methods
handle.descriptor()  # Get metadata
handle.instructions()  # Load SKILL.md body
handle.read_reference(path)  # Read reference file
handle.read_asset(path)  # Read binary asset
handle.run_script(path, args, stdin, timeout_s)  # Execute script
```

### Data Models

#### SkillDescriptor

Metadata-only representation of a skill.

```python
from agent_skills.models import SkillDescriptor

descriptor = SkillDescriptor(
    name="my-skill",
    description="Skill description",
    path=Path("/path/to/skill"),
    license="MIT",
    compatibility={"frameworks": ["langchain"]},
    metadata={"author": "Name"},
    allowed_tools=["skills.read"],
    hash="abc123",
    mtime=1234567890.0,
)
```

#### ExecutionResult

Result of script execution.

```python
from agent_skills.models import ExecutionResult

result = ExecutionResult(
    exit_code=0,
    stdout="Output text",
    stderr="",
    duration_ms=1234,
    meta={"sandbox": "local_subprocess"},
)
```

### Policy Models

#### ResourcePolicy

Configuration for resource access limits.

```python
from agent_skills.models import ResourcePolicy

policy = ResourcePolicy(
    max_file_bytes=200_000,
    max_total_bytes_per_session=1_000_000,
    allow_extensions_text={".md", ".txt", ".json"},
    allow_binary_assets=False,
    binary_max_bytes=2_000_000,
)
```

#### ExecutionPolicy

Configuration for script execution permissions.

```python
from agent_skills.models import ExecutionPolicy

policy = ExecutionPolicy(
    enabled=False,  # Disabled by default
    allow_skills={"trusted-skill"},
    allow_scripts_glob=["scripts/*.py"],
    timeout_s_default=60,
    network_access=False,
    env_allowlist={"PATH", "HOME"},
    workdir_mode="skill_root",  # or "tempdir"
)
```

## Development

### Project Structure

```
agent_skills/
├── __init__.py              # Public API exports
├── exceptions.py            # Exception classes
├── models.py                # Data models
├── discovery/               # Skill scanning and indexing
│   ├── scanner.py
│   ├── cache.py
│   └── index.py
├── parsing/                 # SKILL.md parsing
│   ├── frontmatter.py
│   └── markdown.py
├── resources/               # File access and policies
│   ├── resolver.py
│   ├── policy.py
│   └── reader.py
├── exec/                    # Script execution
│   ├── runner.py
│   ├── sandbox.py
│   └── local_sandbox.py
├── runtime/                 # Core runtime
│   ├── repository.py
│   ├── handle.py
│   └── session.py
├── adapters/                # Framework integrations
│   ├── langchain.py
│   ├── adk.py
│   └── tool_response.py
├── prompt/                  # Prompt rendering
│   ├── claude_xml.py
│   └── json_renderer.py
├── observability/           # Audit logging
│   └── audit.py
└── cli/                     # Command-line interface
    └── main.py
```

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/agent-skills-runtime.git
cd agent-skills-runtime

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agent_skills --cov-report=html

# Run specific test file
pytest tests/test_repository.py

# Run with verbose output
pytest -v

# Run only unit tests
pytest -m unit

# Run only property tests
pytest -m property
```

### Test Structure

The project uses both unit tests and property-based tests:

- **Unit tests**: Verify specific examples and edge cases
- **Property tests**: Verify universal properties across all inputs using Hypothesis

### Code Coverage

Aim for >= 90% code coverage:

```bash
pytest --cov=agent_skills --cov-report=term-missing
```

### Code Quality

```bash
# Format code with black
black agent_skills tests

# Lint with ruff
ruff check agent_skills tests

# Type checking with mypy
mypy agent_skills
```

## Requirements

- Python >= 3.10
- PyYAML >= 6.0
- Pydantic >= 2.0

### Optional Dependencies

- `langchain` - For LangChain integration
- `hypothesis` - For property-based testing
- `pytest` - For running tests
- `pytest-cov` - For coverage reports

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Documentation

- [Requirements Document](.kiro/specs/agent-skills-runtime/requirements.md)
- [Design Document](.kiro/specs/agent-skills-runtime/design.md)
- [Implementation Tasks](.kiro/specs/agent-skills-runtime/tasks.md)
- [Tool Response Helpers](docs/tool_response_helpers.md)

## Examples

See the [examples/](examples/) directory for:
- Standalone usage examples
- LangChain integration examples
- ADK integration examples
- Sample skills with references, assets, and scripts

## Contributing

Contributions are welcome! Please:

1. Read the requirements and design documents
2. Follow the existing code style
3. Add tests for new features
4. Ensure all tests pass
5. Update documentation as needed

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/yourusername/agent-skills-runtime/issues
- Documentation: See docs/ directory

## Acknowledgments

Built with security, observability, and developer experience in mind.

# Agent Skills Runtime - Examples

This directory contains comprehensive examples demonstrating various features and use cases of the Agent Skills Runtime library.

## Examples Overview

### 1. Standalone Usage (`standalone_usage.py`)

Demonstrates basic usage without any framework integration:
- Initializing a repository
- Discovering and listing skills
- Loading skill instructions
- Reading reference files
- Executing scripts
- Generating prompts

**Run:**
```bash
python examples/standalone_usage.py
```

### 2. LangChain Integration (`langchain_integration.py`)

Shows how to integrate skills with LangChain agents:
- Building LangChain tools from skills
- Creating agents with skill access
- Running queries through the agent
- Tool-based skill interaction

**Requirements:**
```bash
pip install agent-skills[langchain]
export OPENAI_API_KEY=your_key_here
```

**Run:**
```bash
python examples/langchain_integration.py
```

### 3. ADK Integration (`adk_integration.py`)

Demonstrates ADK framework integration:
- Building ADK toolsets
- Session management for stateful interactions
- State transitions and artifact storage
- ADK agent configuration

**Run:**
```bash
python examples/adk_integration.py
```

### 4. Security Policies (`security_policies.py`)

Comprehensive security features demonstration:
- Strict resource policies (file size limits)
- Execution policies (script allowlisting)
- Path traversal prevention
- Audit logging
- Combined security configurations

**Run:**
```bash
python examples/security_policies.py
```

### 5. Tool Response Usage (`tool_response_usage.py`)

Shows how to use tool response helper functions:
- Building metadata responses
- Building instruction responses
- Building reference/asset responses
- Building execution responses
- Error handling with safe_tool_call

**Run:**
```bash
python examples/tool_response_usage.py
```

## Sample Skills

### test-skill

A simple example skill located in `examples/test-skill/`:

```
test-skill/
├── SKILL.md              # Skill metadata and instructions
├── references/           # Documentation
│   └── example.md
└── scripts/             # Executable scripts
    └── hello.py
```

This skill is used by all the examples above.

## Running Examples

### Prerequisites

1. Install the library:
```bash
pip install -e .
```

2. For LangChain examples:
```bash
pip install -e ".[langchain]"
```

3. Set up environment (for LangChain):
```bash
export OPENAI_API_KEY=your_key_here
```

### Run All Examples

```bash
# Standalone usage
python examples/standalone_usage.py

# LangChain integration (requires API key)
python examples/langchain_integration.py

# ADK integration
python examples/adk_integration.py

# Security policies
python examples/security_policies.py

# Tool response helpers
python examples/tool_response_usage.py
```

## Creating Your Own Skills

To create a new skill:

1. Create a directory with your skill name
2. Add a `SKILL.md` file with frontmatter and instructions
3. Optionally add `references/`, `assets/`, and `scripts/` directories
4. Point the repository to your skills directory

### Minimal Skill Example

```markdown
---
name: my-skill
description: What this skill does
license: MIT
---

# My Skill

Instructions for using this skill...
```

### Complete Skill Example

See `examples/test-skill/` for a complete example with:
- Proper frontmatter
- Detailed instructions
- Reference documentation
- Executable scripts

## Example Output

Each example produces detailed output showing:
- Configuration and initialization
- Operations being performed
- Results and responses
- Error handling (where applicable)

## Troubleshooting

### Import Errors

If you get import errors:
```bash
pip install -e .
```

### LangChain Not Available

For LangChain examples:
```bash
pip install agent-skills[langchain]
```

### OpenAI API Key

For LangChain examples with LLM:
```bash
export OPENAI_API_KEY=your_key_here
```

### Permission Errors

For script execution:
```bash
chmod +x examples/test-skill/scripts/hello.py
```

## Next Steps

After exploring these examples:

1. Read the [main README](../README.md) for full documentation
2. Check the [design document](../.kiro/specs/agent-skills-runtime/design.md)
3. Review the [API reference](../README.md#api-reference)
4. Create your own skills
5. Integrate with your agent framework

## Contributing

To add new examples:

1. Create a new Python file in this directory
2. Follow the existing example structure
3. Add documentation to this README
4. Test your example thoroughly
5. Submit a pull request

## Support

For questions or issues:
- GitHub Issues: https://github.com/yourusername/agent-skills-runtime/issues
- Documentation: See main README and design docs

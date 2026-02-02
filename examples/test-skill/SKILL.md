---
name: test-skill
description: A simple test skill for CLI testing
license: MIT
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Test Author
  version: 1.0.0
---

# Test Skill

This is a simple test skill for demonstrating the CLI functionality.

## Usage

1. List skills using `agent-skills list`
2. View this prompt using `agent-skills prompt`
3. Validate the skill structure using `agent-skills validate`
4. Run scripts using `agent-skills run`

## Example

```bash
agent-skills list --roots examples
```

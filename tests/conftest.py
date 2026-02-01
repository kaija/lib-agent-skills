"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def skill_root(temp_dir: Path) -> Path:
    """Create a temporary skill root directory."""
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir(parents=True)
    return skill_dir


@pytest.fixture
def sample_skill_md(skill_root: Path) -> Path:
    """Create a sample SKILL.md file."""
    skill_md = skill_root / "SKILL.md"
    content = """---
name: test-skill
description: A test skill for unit tests
license: MIT
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Test Author
  version: 1.0.0
allowed_tools:
  - skills.read
  - skills.run
---

# Test Skill Instructions

This is a test skill for unit testing.

## Usage

1. Read the documentation
2. Execute the script
3. Verify results
"""
    skill_md.write_text(content)
    return skill_md


@pytest.fixture
def sample_skill_with_references(skill_root: Path, sample_skill_md: Path) -> Path:
    """Create a sample skill with references directory."""
    refs_dir = skill_root / "references"
    refs_dir.mkdir()
    
    # Create a sample reference file
    api_doc = refs_dir / "api-docs.md"
    api_doc.write_text("# API Documentation\n\nThis is sample API documentation.")
    
    return skill_root


@pytest.fixture
def sample_skill_with_assets(skill_root: Path, sample_skill_md: Path) -> Path:
    """Create a sample skill with assets directory."""
    assets_dir = skill_root / "assets"
    assets_dir.mkdir()
    
    # Create a sample asset file
    data_file = assets_dir / "data.txt"
    data_file.write_text("Sample data content")
    
    return skill_root


@pytest.fixture
def sample_skill_with_scripts(skill_root: Path, sample_skill_md: Path) -> Path:
    """Create a sample skill with scripts directory."""
    scripts_dir = skill_root / "scripts"
    scripts_dir.mkdir()
    
    # Create a sample script
    script_file = scripts_dir / "process.py"
    script_file.write_text("""#!/usr/bin/env python3
import sys
print("Processing complete")
sys.exit(0)
""")
    script_file.chmod(0o755)
    
    return skill_root

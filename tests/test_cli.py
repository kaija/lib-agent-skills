"""Tests for CLI functionality."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def test_skill_dir(tmp_path):
    """Create a test skill directory."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    
    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: A test skill for CLI testing
license: MIT
---

# Test Skill

This is a test skill.
""")
    
    # Create references directory
    references_dir = skill_dir / "references"
    references_dir.mkdir()
    (references_dir / "example.md").write_text("# Example\n\nTest reference.")
    
    # Create scripts directory
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "hello.py"
    script.write_text("""#!/usr/bin/env python3
import sys
print("Hello, World!")
sys.exit(0)
""")
    script.chmod(0o755)
    
    return tmp_path


def run_cli(*args):
    """Run the CLI and return the result."""
    cmd = [sys.executable, "-m", "agent_skills"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    return result


class TestCLI:
    """Test CLI commands."""
    
    def test_list_command(self, test_skill_dir):
        """Test the list command."""
        result = run_cli("list", "--roots", str(test_skill_dir))
        
        assert result.returncode == 0
        assert "test-skill" in result.stdout
        assert "A test skill for CLI testing" in result.stdout
    
    def test_list_command_no_skills(self, tmp_path):
        """Test list command with no skills."""
        result = run_cli("list", "--roots", str(tmp_path))
        
        assert result.returncode == 0
        assert "No skills found" in result.stdout
    
    def test_prompt_command_claude_xml(self, test_skill_dir):
        """Test prompt command with Claude XML format."""
        result = run_cli(
            "prompt",
            "--roots", str(test_skill_dir),
            "--format", "claude_xml",
        )
        
        assert result.returncode == 0
        assert "<available_skills>" in result.stdout
        assert 'name="test-skill"' in result.stdout
        assert 'description="A test skill for CLI testing"' in result.stdout
    
    def test_prompt_command_json(self, test_skill_dir):
        """Test prompt command with JSON format."""
        result = run_cli(
            "prompt",
            "--roots", str(test_skill_dir),
            "--format", "json",
            "--no-location",
        )
        
        assert result.returncode == 0
        assert '"name": "test-skill"' in result.stdout
        assert '"description": "A test skill for CLI testing"' in result.stdout
    
    def test_validate_command(self, test_skill_dir):
        """Test validate command."""
        result = run_cli("validate", "--roots", str(test_skill_dir))
        
        assert result.returncode == 0
        assert "test-skill: Valid" in result.stdout
        assert "references/: ✓" in result.stdout
        assert "scripts/: ✓" in result.stdout
    
    def test_validate_command_invalid_skill(self, tmp_path):
        """Test validate command with invalid skill."""
        # Create a skill with invalid frontmatter
        skill_dir = tmp_path / "invalid-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: invalid-skill
# Missing description
---

# Invalid Skill
""")
        
        result = run_cli("validate", "--roots", str(tmp_path))
        
        # Should still succeed but show validation errors
        assert "invalid-skill" in result.stdout
    
    def test_run_command(self, test_skill_dir):
        """Test run command."""
        result = run_cli(
            "run",
            "test-skill",
            "hello.py",
            "--roots", str(test_skill_dir),
        )
        
        assert result.returncode == 0
        assert "Hello, World!" in result.stdout
        assert "Exit code: 0" in result.stdout
    
    def test_run_command_skill_not_found(self, test_skill_dir):
        """Test run command with non-existent skill."""
        result = run_cli(
            "run",
            "nonexistent-skill",
            "hello.py",
            "--roots", str(test_skill_dir),
        )
        
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()
    
    def test_help_command(self):
        """Test help command."""
        result = run_cli("--help")
        
        assert result.returncode == 0
        assert "agent-skills" in result.stdout
        assert "list" in result.stdout
        assert "prompt" in result.stdout
        assert "validate" in result.stdout
        assert "run" in result.stdout
    
    def test_list_help(self):
        """Test list command help."""
        result = run_cli("list", "--help")
        
        assert result.returncode == 0
        assert "Display all skills" in result.stdout
        assert "--roots" in result.stdout

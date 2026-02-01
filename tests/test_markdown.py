"""Tests for SkillMarkdownLoader."""

from pathlib import Path

import pytest

from agent_skills.exceptions import SkillParseError
from agent_skills.parsing import FrontmatterParser, SkillMarkdownLoader


class TestSkillMarkdownLoader:
    """Test suite for SkillMarkdownLoader."""
    
    def test_load_body_basic(self, skill_root: Path):
        """Test loading markdown body from a standard SKILL.md file."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Instructions

This is the body content.
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify body content
        assert body.strip() == "# Instructions\n\nThis is the body content."
        assert "# Instructions" in body
        assert "This is the body content." in body
    
    def test_load_body_preserves_formatting(self, skill_root: Path):
        """Test that markdown formatting is preserved."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Main Title

## Subsection

- List item 1
- List item 2

```python
def example():
    return "code block"
```

**Bold text** and *italic text*.
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify formatting is preserved
        assert "# Main Title" in body
        assert "## Subsection" in body
        assert "- List item 1" in body
        assert "- List item 2" in body
        assert "```python" in body
        assert "def example():" in body
        assert "**Bold text**" in body
        assert "*italic text*" in body
    
    def test_load_body_empty(self, skill_root: Path):
        """Test loading body when SKILL.md has only frontmatter (empty body)."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Should return empty string for empty body
        assert body == ''
    
    def test_load_body_whitespace_only(self, skill_root: Path):
        """Test loading body when it contains only whitespace."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

   
\t
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Should return empty string for whitespace-only body
        assert body == ''
    
    def test_load_body_with_newlines(self, skill_root: Path):
        """Test that leading/trailing newlines are preserved in non-empty bodies."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Content

Some text here.

"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Body should contain the content (not be empty)
        assert body != ''
        assert "# Content" in body
        assert "Some text here." in body
    
    def test_load_body_multiline_content(self, skill_root: Path):
        """Test loading body with multiple paragraphs and sections."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Introduction

This is the first paragraph.

This is the second paragraph.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify all sections are present
        assert "# Introduction" in body
        assert "This is the first paragraph." in body
        assert "This is the second paragraph." in body
        assert "## Section 1" in body
        assert "Content for section 1." in body
        assert "## Section 2" in body
        assert "Content for section 2." in body
    
    def test_load_body_special_characters(self, skill_root: Path):
        """Test loading body with special characters and unicode."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Special Characters

Unicode: café, naïve, 日本語
Symbols: @#$%^&*()
Quotes: "double" and 'single'
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify special characters are preserved
        assert "café" in body
        assert "naïve" in body
        assert "日本語" in body
        assert "@#$%^&*()" in body
        assert '"double"' in body
        assert "'single'" in body
    
    def test_load_body_missing_skill_md(self, skill_root: Path):
        """Test that loading body raises error when SKILL.md doesn't exist."""
        loader = SkillMarkdownLoader()
        
        with pytest.raises(SkillParseError) as exc_info:
            loader.load_body(skill_root, 0)
        
        assert "SKILL.md not found" in str(exc_info.value)
    
    def test_load_body_with_code_blocks(self, skill_root: Path):
        """Test loading body with code blocks containing triple backticks."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Code Example

```python
def hello():
    print("Hello, world!")
    return True
```

```bash
echo "test"
ls -la
```
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify code blocks are preserved
        assert "```python" in body
        assert "def hello():" in body
        assert '    print("Hello, world!")' in body
        assert "```bash" in body
        assert "echo \"test\"" in body
    
    def test_load_body_with_tables(self, skill_root: Path):
        """Test loading body with markdown tables."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Table Example

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify table is preserved
        assert "| Column 1 | Column 2 | Column 3 |" in body
        assert "|----------|----------|----------|" in body
        assert "| Value 1  | Value 2  | Value 3  |" in body
    
    def test_load_body_integration_with_frontmatter_parser(self, skill_root: Path):
        """Test that SkillMarkdownLoader works correctly with FrontmatterParser offset."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: integration-test
description: Testing integration
license: MIT
---

# Integration Test

This tests that the offset from FrontmatterParser
works correctly with SkillMarkdownLoader.

## Details

The body should start exactly after the second '---' delimiter.
"""
        skill_md.write_text(content)
        
        # Parse frontmatter
        parser = FrontmatterParser()
        metadata, body_offset = parser.parse(skill_root)
        
        # Verify metadata
        assert metadata['name'] == 'integration-test'
        assert metadata['description'] == 'Testing integration'
        
        # Load body using the offset
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify body content
        assert "# Integration Test" in body
        assert "This tests that the offset from FrontmatterParser" in body
        assert "works correctly with SkillMarkdownLoader." in body
        assert "## Details" in body
        
        # Verify frontmatter is NOT in the body
        assert "name: integration-test" not in body
        assert "description: Testing integration" not in body
        assert "---" not in body.strip()[:10]  # No delimiter at start
    
    def test_load_body_large_content(self, skill_root: Path):
        """Test loading body with large content."""
        skill_md = skill_root / "SKILL.md"
        
        # Create a large body with many lines
        large_body = "\n".join([f"Line {i}: This is content line number {i}" for i in range(1000)])
        
        content = f"""---
name: large-skill
description: A skill with large body
---

{large_body}
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify content
        assert "Line 0: This is content line number 0" in body
        assert "Line 500: This is content line number 500" in body
        assert "Line 999: This is content line number 999" in body
        assert body.count("Line") == 1000
    
    def test_load_body_offset_zero(self, skill_root: Path):
        """Test behavior when offset is 0 (edge case)."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Body Content
"""
        skill_md.write_text(content)
        
        # Load body from offset 0 (should read entire file)
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, 0)
        
        # Should contain everything including frontmatter
        assert "---" in body
        assert "name: test-skill" in body
        assert "# Body Content" in body
    
    def test_load_body_preserves_indentation(self, skill_root: Path):
        """Test that indentation in code blocks and lists is preserved."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
---

# Indentation Test

1. First item
   - Nested item 1
   - Nested item 2
2. Second item
   - Another nested item

```python
class Example:
    def __init__(self):
        self.value = 42
    
    def method(self):
        if self.value > 0:
            return True
        return False
```
"""
        skill_md.write_text(content)
        
        # Parse frontmatter to get offset
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Load body
        loader = SkillMarkdownLoader()
        body = loader.load_body(skill_root, body_offset)
        
        # Verify indentation is preserved
        assert "   - Nested item 1" in body
        assert "    def __init__(self):" in body
        assert "        self.value = 42" in body
        assert "        if self.value > 0:" in body

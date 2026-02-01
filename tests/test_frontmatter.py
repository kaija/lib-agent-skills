"""Tests for frontmatter parsing."""

import hashlib
from pathlib import Path

import pytest

from agent_skills.exceptions import SkillParseError
from agent_skills.parsing import FrontmatterParser


class TestFrontmatterParser:
    """Test suite for FrontmatterParser."""
    
    def test_parse_valid_frontmatter(self, skill_root: Path):
        """Test parsing valid frontmatter with all fields."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: A test skill
license: MIT
compatibility:
  frameworks: ["langchain"]
metadata:
  version: 1.0.0
allowed_tools:
  - skills.read
---

# Instructions

Body content here.
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        metadata, body_offset = parser.parse(skill_root)
        
        # Check metadata fields
        assert metadata['name'] == 'test-skill'
        assert metadata['description'] == 'A test skill'
        assert metadata['license'] == 'MIT'
        assert metadata['compatibility'] == {'frameworks': ['langchain']}
        assert metadata['metadata'] == {'version': '1.0.0'}
        assert metadata['allowed_tools'] == ['skills.read']
        
        # Check hash is present
        assert '_frontmatter_hash' in metadata
        assert len(metadata['_frontmatter_hash']) == 64  # SHA256 hex length
        
        # Check body offset points to correct location
        with open(skill_md, 'r') as f:
            f.seek(body_offset)
            body = f.read()
            assert body.startswith('\n# Instructions')
    
    def test_parse_minimal_frontmatter(self, skill_root: Path):
        """Test parsing frontmatter with only required fields."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: minimal-skill
description: Minimal test skill
---

Body content.
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        metadata, body_offset = parser.parse(skill_root)
        
        assert metadata['name'] == 'minimal-skill'
        assert metadata['description'] == 'Minimal test skill'
        assert '_frontmatter_hash' in metadata
    
    def test_parse_empty_body(self, skill_root: Path):
        """Test parsing frontmatter with no body content."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: no-body-skill
description: Skill with no body
---
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        metadata, body_offset = parser.parse(skill_root)
        
        assert metadata['name'] == 'no-body-skill'
        
        # Body should be empty or just whitespace
        with open(skill_md, 'r') as f:
            f.seek(body_offset)
            body = f.read()
            assert body.strip() == ''
    
    def test_missing_skill_md(self, skill_root: Path):
        """Test error when SKILL.md doesn't exist."""
        parser = FrontmatterParser()
        
        with pytest.raises(SkillParseError, match="SKILL.md not found"):
            parser.parse(skill_root)
    
    def test_missing_first_delimiter(self, skill_root: Path):
        """Test error when first --- delimiter is missing."""
        skill_md = skill_root / "SKILL.md"
        content = """name: test-skill
description: Missing delimiter
---
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        
        with pytest.raises(SkillParseError, match="must start with '---'"):
            parser.parse(skill_root)
    
    def test_missing_second_delimiter(self, skill_root: Path):
        """Test error when second --- delimiter is missing."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: Missing second delimiter
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        
        with pytest.raises(SkillParseError, match="ended before finding second"):
            parser.parse(skill_root)
    
    def test_invalid_yaml(self, skill_root: Path):
        """Test error when frontmatter contains invalid YAML."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
description: [invalid yaml
  missing bracket
---
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        
        with pytest.raises(SkillParseError, match="Invalid YAML"):
            parser.parse(skill_root)
    
    def test_missing_name_field(self, skill_root: Path):
        """Test error when name field is missing."""
        skill_md = skill_root / "SKILL.md"
        content = """---
description: Missing name field
---
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        
        with pytest.raises(SkillParseError, match="missing required field: name"):
            parser.parse(skill_root)
    
    def test_missing_description_field(self, skill_root: Path):
        """Test error when description field is missing."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: test-skill
---
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        
        with pytest.raises(SkillParseError, match="missing required field: description"):
            parser.parse(skill_root)
    
    def test_frontmatter_not_dict(self, skill_root: Path):
        """Test error when frontmatter is not a dictionary."""
        skill_md = skill_root / "SKILL.md"
        content = """---
- item1
- item2
---
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        
        with pytest.raises(SkillParseError, match="must be a YAML dictionary"):
            parser.parse(skill_root)
    
    def test_hash_computation(self, skill_root: Path):
        """Test that hash is computed correctly from frontmatter content."""
        skill_md = skill_root / "SKILL.md"
        frontmatter_content = """name: test-skill
description: Test hash computation
"""
        content = f"---\n{frontmatter_content}---\n\nBody"
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        metadata, _ = parser.parse(skill_root)
        
        # Compute expected hash
        expected_hash = hashlib.sha256(frontmatter_content.encode('utf-8')).hexdigest()
        
        assert metadata['_frontmatter_hash'] == expected_hash
    
    def test_identical_frontmatter_same_hash(self, temp_dir: Path):
        """Test that identical frontmatter produces identical hashes."""
        # Create two skills with identical frontmatter
        skill1 = temp_dir / "skill1"
        skill1.mkdir()
        skill1_md = skill1 / "SKILL.md"
        
        skill2 = temp_dir / "skill2"
        skill2.mkdir()
        skill2_md = skill2 / "SKILL.md"
        
        frontmatter = """---
name: identical-skill
description: Same frontmatter
license: MIT
---

Different body content for skill 1.
"""
        skill1_md.write_text(frontmatter)
        
        frontmatter2 = """---
name: identical-skill
description: Same frontmatter
license: MIT
---

Different body content for skill 2.
"""
        skill2_md.write_text(frontmatter2)
        
        parser = FrontmatterParser()
        metadata1, _ = parser.parse(skill1)
        metadata2, _ = parser.parse(skill2)
        
        # Hashes should be identical (body doesn't affect hash)
        assert metadata1['_frontmatter_hash'] == metadata2['_frontmatter_hash']
    
    def test_different_frontmatter_different_hash(self, temp_dir: Path):
        """Test that different frontmatter produces different hashes."""
        skill1 = temp_dir / "skill1"
        skill1.mkdir()
        skill1_md = skill1 / "SKILL.md"
        
        skill2 = temp_dir / "skill2"
        skill2.mkdir()
        skill2_md = skill2 / "SKILL.md"
        
        skill1_md.write_text("""---
name: skill-one
description: First skill
---
""")
        
        skill2_md.write_text("""---
name: skill-two
description: Second skill
---
""")
        
        parser = FrontmatterParser()
        metadata1, _ = parser.parse(skill1)
        metadata2, _ = parser.parse(skill2)
        
        # Hashes should be different
        assert metadata1['_frontmatter_hash'] != metadata2['_frontmatter_hash']
    
    def test_body_offset_accuracy(self, skill_root: Path):
        """Test that body offset points to exact start of body content."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: offset-test
description: Test body offset
---
# First Line of Body
Second line of body.
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        _, body_offset = parser.parse(skill_root)
        
        # Read from offset and verify it's the body
        with open(skill_md, 'r') as f:
            f.seek(body_offset)
            body = f.read()
            # Body should start right after the second --- (newline is consumed by readline)
            # So the body starts with the first content line
            assert body.startswith('# First Line of Body')
    
    def test_multiline_values(self, skill_root: Path):
        """Test parsing frontmatter with multiline YAML values."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: multiline-skill
description: |
  This is a multiline
  description that spans
  multiple lines.
metadata:
  notes: >
    This is a folded
    multiline string.
---

Body content.
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        metadata, _ = parser.parse(skill_root)
        
        assert metadata['name'] == 'multiline-skill'
        assert 'multiline' in metadata['description']
        assert 'description' in metadata['description']
        assert 'notes' in metadata['metadata']
    
    def test_special_characters_in_values(self, skill_root: Path):
        """Test parsing frontmatter with special characters."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: special-chars-skill
description: "Skill with special chars: @#$%^&*()"
metadata:
  emoji: "🚀 Rocket skill"
  quotes: 'Single "quotes" inside'
---
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        metadata, _ = parser.parse(skill_root)
        
        assert '@#$%^&*()' in metadata['description']
        assert '🚀' in metadata['metadata']['emoji']
        assert 'quotes' in metadata['metadata']['quotes']
    
    def test_empty_frontmatter(self, skill_root: Path):
        """Test parsing with empty frontmatter (should fail validation)."""
        skill_md = skill_root / "SKILL.md"
        content = """---
---

Body content.
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        
        # Should fail because required fields are missing
        with pytest.raises(SkillParseError, match="missing required field"):
            parser.parse(skill_root)

"""Integration tests for frontmatter parsing with SkillDescriptor."""

from pathlib import Path

import pytest

from agent_skills.models import SkillDescriptor
from agent_skills.parsing import FrontmatterParser


class TestFrontmatterIntegration:
    """Test integration between FrontmatterParser and SkillDescriptor."""
    
    def test_create_skill_descriptor_from_frontmatter(self, skill_root: Path):
        """Test creating a SkillDescriptor from parsed frontmatter."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: integration-test-skill
description: Test skill for integration testing
license: Apache-2.0
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Integration Test
  version: 2.0.0
allowed_tools:
  - skills.list
  - skills.activate
  - skills.read
---

# Integration Test Skill

This skill is used for integration testing.
"""
        skill_md.write_text(content)
        
        # Parse frontmatter
        parser = FrontmatterParser()
        metadata, body_offset = parser.parse(skill_root)
        
        # Get mtime
        mtime = skill_md.stat().st_mtime
        
        # Create SkillDescriptor
        descriptor = SkillDescriptor(
            name=metadata['name'],
            description=metadata['description'],
            path=skill_root,
            license=metadata.get('license'),
            compatibility=metadata.get('compatibility'),
            metadata=metadata.get('metadata'),
            allowed_tools=metadata.get('allowed_tools'),
            hash=metadata['_frontmatter_hash'],
            mtime=mtime,
        )
        
        # Verify descriptor fields
        assert descriptor.name == 'integration-test-skill'
        assert descriptor.description == 'Test skill for integration testing'
        assert descriptor.license == 'Apache-2.0'
        assert descriptor.compatibility == {
            'frameworks': ['langchain', 'adk'],
            'python': '>=3.10'
        }
        assert descriptor.metadata == {
            'author': 'Integration Test',
            'version': '2.0.0'
        }
        assert descriptor.allowed_tools == ['skills.list', 'skills.activate', 'skills.read']
        assert len(descriptor.hash) == 64  # SHA256 hex
        assert descriptor.mtime > 0
        
        # Test serialization round-trip
        descriptor_dict = descriptor.to_dict()
        restored_descriptor = SkillDescriptor.from_dict(descriptor_dict)
        
        assert restored_descriptor.name == descriptor.name
        assert restored_descriptor.description == descriptor.description
        assert restored_descriptor.hash == descriptor.hash
    
    def test_body_offset_for_instructions_loading(self, skill_root: Path):
        """Test that body offset can be used to load instructions."""
        skill_md = skill_root / "SKILL.md"
        instructions_text = """# Skill Instructions

This is the instruction body.

## Step 1
Do this first.

## Step 2
Do this second.
"""
        content = f"""---
name: body-test-skill
description: Test body loading
---
{instructions_text}"""
        skill_md.write_text(content)
        
        # Parse frontmatter
        parser = FrontmatterParser()
        metadata, body_offset = parser.parse(skill_root)
        
        # Load body using offset
        with open(skill_md, 'r') as f:
            f.seek(body_offset)
            loaded_body = f.read()
        
        # Verify body content
        assert loaded_body == instructions_text
        assert '# Skill Instructions' in loaded_body
        assert '## Step 1' in loaded_body
        assert '## Step 2' in loaded_body
    
    def test_minimal_skill_descriptor(self, skill_root: Path):
        """Test creating SkillDescriptor with minimal frontmatter."""
        skill_md = skill_root / "SKILL.md"
        content = """---
name: minimal-skill
description: Minimal skill with only required fields
---

Minimal instructions.
"""
        skill_md.write_text(content)
        
        parser = FrontmatterParser()
        metadata, _ = parser.parse(skill_root)
        
        # Create descriptor with minimal fields
        descriptor = SkillDescriptor(
            name=metadata['name'],
            description=metadata['description'],
            path=skill_root,
            hash=metadata['_frontmatter_hash'],
            mtime=skill_md.stat().st_mtime,
        )
        
        assert descriptor.name == 'minimal-skill'
        assert descriptor.description == 'Minimal skill with only required fields'
        assert descriptor.license is None
        assert descriptor.compatibility is None
        assert descriptor.metadata is None
        assert descriptor.allowed_tools is None
        assert len(descriptor.hash) == 64

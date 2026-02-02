#!/usr/bin/env python3
"""Example: Standalone usage of Agent Skills Runtime.

This example demonstrates basic usage without any framework integration.
"""

from pathlib import Path
from agent_skills.runtime import SkillsRepository
from agent_skills.models import ResourcePolicy, ExecutionPolicy
from agent_skills.observability import StdoutAuditSink


def main():
    """Demonstrate standalone usage."""
    print("=" * 60)
    print("Agent Skills Runtime - Standalone Usage Example")
    print("=" * 60)
    print()
    
    # Configure policies
    resource_policy = ResourcePolicy(
        max_file_bytes=200_000,
        max_total_bytes_per_session=1_000_000,
        allow_extensions_text={".md", ".txt", ".json", ".yaml", ".yml"},
        allow_binary_assets=False,
    )
    
    execution_policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=["scripts/*.py"],
        timeout_s_default=30,
    )
    
    # Create audit sink for logging
    audit_sink = StdoutAuditSink()
    
    # Initialize repository
    print("Initializing repository...")
    repo = SkillsRepository(
        roots=[Path("examples")],
        cache_dir=Path(".cache/agent-skills"),
        resource_policy=resource_policy,
        execution_policy=execution_policy,
        audit_sink=audit_sink,
    )
    
    # Discover skills
    print("\nDiscovering skills...")
    skills = repo.refresh()
    print(f"Found {len(skills)} skill(s)")
    print()
    
    # List all skills
    print("Available skills:")
    for skill in repo.list():
        print(f"  - {skill.name}: {skill.description}")
        if skill.license:
            print(f"    License: {skill.license}")
        if skill.metadata:
            print(f"    Metadata: {skill.metadata}")
    print()
    
    # Open a specific skill
    print("Opening 'test-skill'...")
    handle = repo.open("test-skill")
    print()
    
    # Load instructions (lazy loaded)
    print("Loading instructions...")
    instructions = handle.instructions()
    print(f"Instructions ({len(instructions)} bytes):")
    print("-" * 60)
    print(instructions[:300] + "..." if len(instructions) > 300 else instructions)
    print("-" * 60)
    print()
    
    # Read a reference file
    print("Reading reference file...")
    try:
        reference = handle.read_reference("references/example.md")
        print(f"Reference content ({len(reference)} bytes):")
        print("-" * 60)
        print(reference[:200] + "..." if len(reference) > 200 else reference)
        print("-" * 60)
    except Exception as e:
        print(f"Error reading reference: {e}")
    print()
    
    # Execute a script
    print("Executing script...")
    try:
        result = handle.run_script(
            "scripts/hello.py",
            args=["Agent"],
            timeout_s=10,
        )
        print(f"Exit code: {result.exit_code}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Errors: {result.stderr}")
    except Exception as e:
        print(f"Error executing script: {e}")
    print()
    
    # Generate prompt for agent
    print("Generating prompt for agent...")
    prompt = repo.to_prompt(format="claude_xml", include_location=False)
    print("Claude XML format:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)
    print()
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

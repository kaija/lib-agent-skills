"""Command-line interface for Agent Skills Runtime.

This module provides a CLI for testing and managing skills without writing code.
It supports listing skills, rendering prompts, validating skill structure, and
executing scripts.

Commands:
    list: Display all discovered skills
    prompt: Render available skills prompt
    validate: Check skill structure and frontmatter
    run: Execute a skill script

Example:
    $ agent-skills list --roots ./skills
    $ agent-skills prompt --format claude_xml --include-location
    $ agent-skills validate --roots ./skills
    $ agent-skills run data-processor scripts/process.py --args "--input" --args "data.csv"
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from agent_skills.exceptions import (
    AgentSkillsError,
    SkillNotFoundError,
    SkillParseError,
)
from agent_skills.models import ExecutionPolicy, ResourcePolicy
from agent_skills.parsing.frontmatter import FrontmatterParser
from agent_skills.runtime.repository import SkillsRepository


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="agent-skills",
        description="Command-line interface for Agent Skills Runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all discovered skills",
        description="Display all skills found in the specified root directories",
    )
    list_parser.add_argument(
        "--roots",
        type=Path,
        action="append",
        required=True,
        help="Root directory to scan for skills (can be specified multiple times)",
    )
    list_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Directory for caching skill metadata (optional)",
    )
    
    # Prompt command
    prompt_parser = subparsers.add_parser(
        "prompt",
        help="Render available skills prompt",
        description="Output skills in a format suitable for agent prompts",
    )
    prompt_parser.add_argument(
        "--roots",
        type=Path,
        action="append",
        required=True,
        help="Root directory to scan for skills (can be specified multiple times)",
    )
    prompt_parser.add_argument(
        "--format",
        choices=["claude_xml", "json"],
        default="claude_xml",
        help="Output format (default: claude_xml)",
    )
    prompt_parser.add_argument(
        "--include-location",
        action="store_true",
        default=True,
        help="Include filesystem path in output (default: True)",
    )
    prompt_parser.add_argument(
        "--no-location",
        action="store_false",
        dest="include_location",
        help="Exclude filesystem path from output",
    )
    prompt_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Directory for caching skill metadata (optional)",
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate skill structure",
        description="Check SKILL.md structure and frontmatter for all skills",
    )
    validate_parser.add_argument(
        "--roots",
        type=Path,
        action="append",
        required=True,
        help="Root directory to scan for skills (can be specified multiple times)",
    )
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Execute a skill script",
        description="Run a script from a skill's scripts/ directory",
    )
    run_parser.add_argument(
        "skill",
        help="Name of the skill",
    )
    run_parser.add_argument(
        "script",
        help="Relative path to script (e.g., 'hello.py' for scripts/hello.py)",
    )
    run_parser.add_argument(
        "--roots",
        type=Path,
        action="append",
        required=True,
        help="Root directory to scan for skills (can be specified multiple times)",
    )
    run_parser.add_argument(
        "--args",
        action="append",
        default=[],
        help="Script arguments (can be specified multiple times)",
    )
    run_parser.add_argument(
        "--stdin",
        help="Standard input to pass to script",
    )
    run_parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds (default: 60)",
    )
    run_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Directory for caching skill metadata (optional)",
    )
    
    return parser


def cmd_list(args: argparse.Namespace) -> int:
    """Execute the list command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Create repository
        repo = SkillsRepository(
            roots=args.roots,
            cache_dir=args.cache_dir,
        )
        
        # Discover skills
        skills = repo.refresh()
        
        # Display results
        if not skills:
            print("No skills found.")
            return 0
        
        print(f"Found {len(skills)} skill(s):\n")
        for skill in skills:
            print(f"  {skill.name}")
            print(f"    Description: {skill.description}")
            print(f"    Location: {skill.path}")
            if skill.license:
                print(f"    License: {skill.license}")
            if skill.compatibility:
                print(f"    Compatibility: {skill.compatibility}")
            print()
        
        return 0
        
    except AgentSkillsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_prompt(args: argparse.Namespace) -> int:
    """Execute the prompt command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Create repository
        repo = SkillsRepository(
            roots=args.roots,
            cache_dir=args.cache_dir,
        )
        
        # Discover skills
        repo.refresh()
        
        # Render prompt
        prompt = repo.to_prompt(
            format=args.format,
            include_location=args.include_location,
        )
        
        # Output prompt
        print(prompt)
        
        return 0
        
    except AgentSkillsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute the validate command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Create repository
        repo = SkillsRepository(roots=args.roots)
        
        # Discover skills
        skills = repo.refresh()
        
        if not skills:
            print("No skills found.")
            return 0
        
        # Validate each skill
        print(f"Validating {len(skills)} skill(s)...\n")
        
        errors = []
        for skill in skills:
            print(f"Validating {skill.name}...")
            
            # Check SKILL.md exists
            skill_md = skill.path / "SKILL.md"
            if not skill_md.exists():
                errors.append(f"  ✗ {skill.name}: SKILL.md not found")
                continue
            
            # Try to parse frontmatter
            try:
                parser = FrontmatterParser()
                metadata, _ = parser.parse(skill.path)
                
                # Check required fields
                if "name" not in metadata:
                    errors.append(f"  ✗ {skill.name}: Missing required field 'name'")
                if "description" not in metadata:
                    errors.append(f"  ✗ {skill.name}: Missing required field 'description'")
                
                # Check directories
                references_dir = skill.path / "references"
                assets_dir = skill.path / "assets"
                scripts_dir = skill.path / "scripts"
                
                has_references = references_dir.exists() and references_dir.is_dir()
                has_assets = assets_dir.exists() and assets_dir.is_dir()
                has_scripts = scripts_dir.exists() and scripts_dir.is_dir()
                
                print(f"  ✓ {skill.name}: Valid")
                print(f"    - references/: {'✓' if has_references else '✗'}")
                print(f"    - assets/: {'✓' if has_assets else '✗'}")
                print(f"    - scripts/: {'✓' if has_scripts else '✗'}")
                
            except SkillParseError as e:
                errors.append(f"  ✗ {skill.name}: Parse error - {e}")
        
        # Summary
        print()
        if errors:
            print("Validation errors:")
            for error in errors:
                print(error)
            return 1
        else:
            print(f"All {len(skills)} skill(s) validated successfully.")
            return 0
        
    except AgentSkillsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Create execution policy that allows the specified skill
        execution_policy = ExecutionPolicy(
            enabled=True,
            allow_skills={args.skill},
            allow_scripts_glob=["scripts/*", "scripts/**/*"],
            timeout_s_default=args.timeout,
        )
        
        # Create repository
        repo = SkillsRepository(
            roots=args.roots,
            cache_dir=args.cache_dir,
            execution_policy=execution_policy,
        )
        
        # Discover skills
        repo.refresh()
        
        # Open skill
        try:
            handle = repo.open(args.skill)
        except SkillNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            print(f"\nAvailable skills:", file=sys.stderr)
            for skill in repo.list():
                print(f"  - {skill.name}", file=sys.stderr)
            return 1
        
        # Execute script
        print(f"Executing {args.skill}/{args.script}...")
        print(f"Arguments: {args.args}")
        print(f"Timeout: {args.timeout}s")
        print()
        
        result = handle.run_script(
            relpath=args.script,
            args=args.args if args.args else None,
            stdin=args.stdin,
            timeout_s=args.timeout,
        )
        
        # Display results
        print(f"Exit code: {result.exit_code}")
        print(f"Duration: {result.duration_ms}ms")
        print()
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
            print()
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            print()
        
        # Return script's exit code
        return result.exit_code
        
    except AgentSkillsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def main() -> NoReturn:
    """Main entry point for the CLI.
    
    This function is called when the agent-skills command is executed.
    It parses command-line arguments and dispatches to the appropriate
    command handler.
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Dispatch to command handler
    if args.command == "list":
        exit_code = cmd_list(args)
    elif args.command == "prompt":
        exit_code = cmd_prompt(args)
    elif args.command == "validate":
        exit_code = cmd_validate(args)
    elif args.command == "run":
        exit_code = cmd_run(args)
    else:
        parser.print_help()
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

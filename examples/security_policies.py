#!/usr/bin/env python3
"""Example: Security policies and audit logging.

This example demonstrates how to configure strict security policies
and audit logging for production environments.
"""

from pathlib import Path
from agent_skills.runtime import SkillsRepository
from agent_skills.models import ResourcePolicy, ExecutionPolicy
from agent_skills.observability import JSONLAuditSink, StdoutAuditSink
from agent_skills.exceptions import (
    PolicyViolationError,
    PathTraversalError,
    ResourceTooLargeError,
    ScriptExecutionDisabledError,
)


def demonstrate_strict_resource_policy():
    """Demonstrate strict resource policy."""
    print("=" * 60)
    print("Strict Resource Policy Example")
    print("=" * 60)
    print()
    
    # Configure very strict resource policy
    resource_policy = ResourcePolicy(
        max_file_bytes=1000,  # Only 1KB per file
        max_total_bytes_per_session=5000,  # Only 5KB total
        allow_extensions_text={".md", ".txt"},  # Only markdown and text
        allow_binary_assets=False,  # No binary files
    )
    
    print("Resource Policy Configuration:")
    print(f"  Max file bytes: {resource_policy.max_file_bytes}")
    print(f"  Max session bytes: {resource_policy.max_total_bytes_per_session}")
    print(f"  Allowed extensions: {resource_policy.allow_extensions_text}")
    print(f"  Binary assets: {resource_policy.allow_binary_assets}")
    print()
    
    # Create repository with strict policy
    repo = SkillsRepository(
        roots=[Path("examples")],
        resource_policy=resource_policy,
    )
    repo.refresh()
    
    # Try to read a file
    handle = repo.open("test-skill")
    
    print("Attempting to read reference file...")
    try:
        content = handle.read_reference("references/example.md")
        print(f"Success! Read {len(content)} bytes")
        print(f"Truncated: {len(content) >= resource_policy.max_file_bytes}")
    except ResourceTooLargeError as e:
        print(f"Blocked by policy: {e}")
    print()


def demonstrate_strict_execution_policy():
    """Demonstrate strict execution policy."""
    print("=" * 60)
    print("Strict Execution Policy Example")
    print("=" * 60)
    print()
    
    # Configure very strict execution policy
    execution_policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},  # Only specific skills
        allow_scripts_glob=["scripts/hello.py"],  # Only specific scripts
        timeout_s_default=5,  # Short timeout
        network_access=False,  # No network
        env_allowlist={"PATH"},  # Minimal environment
        workdir_mode="tempdir",  # Isolated temp directory
    )
    
    print("Execution Policy Configuration:")
    print(f"  Enabled: {execution_policy.enabled}")
    print(f"  Allowed skills: {execution_policy.allow_skills}")
    print(f"  Allowed scripts: {execution_policy.allow_scripts_glob}")
    print(f"  Timeout: {execution_policy.timeout_s_default}s")
    print(f"  Network access: {execution_policy.network_access}")
    print(f"  Environment: {execution_policy.env_allowlist}")
    print(f"  Working directory: {execution_policy.workdir_mode}")
    print()
    
    # Create repository with strict policy
    repo = SkillsRepository(
        roots=[Path("examples")],
        execution_policy=execution_policy,
    )
    repo.refresh()
    
    handle = repo.open("test-skill")
    
    # Try to run allowed script
    print("Attempting to run allowed script (hello.py)...")
    try:
        result = handle.run_script("scripts/hello.py", args=["Security"])
        print(f"Success! Exit code: {result.exit_code}")
        print(f"Output: {result.stdout.strip()}")
    except PolicyViolationError as e:
        print(f"Blocked by policy: {e}")
    print()
    
    # Try to run disallowed script (would fail if it existed)
    print("Attempting to run disallowed script (other.py)...")
    try:
        result = handle.run_script("scripts/other.py")
        print(f"Success! Exit code: {result.exit_code}")
    except PolicyViolationError as e:
        print(f"Blocked by policy: {e}")
    except Exception as e:
        print(f"Error: {e}")
    print()


def demonstrate_disabled_execution():
    """Demonstrate disabled execution policy."""
    print("=" * 60)
    print("Disabled Execution Policy Example")
    print("=" * 60)
    print()
    
    # Execution disabled by default
    execution_policy = ExecutionPolicy(enabled=False)
    
    print("Execution Policy Configuration:")
    print(f"  Enabled: {execution_policy.enabled}")
    print()
    
    # Create repository
    repo = SkillsRepository(
        roots=[Path("examples")],
        execution_policy=execution_policy,
    )
    repo.refresh()
    
    handle = repo.open("test-skill")
    
    # Try to run any script
    print("Attempting to run script with execution disabled...")
    try:
        result = handle.run_script("scripts/hello.py")
        print(f"Success! Exit code: {result.exit_code}")
    except ScriptExecutionDisabledError as e:
        print(f"Blocked: {e}")
    print()


def demonstrate_path_traversal_prevention():
    """Demonstrate path traversal prevention."""
    print("=" * 60)
    print("Path Traversal Prevention Example")
    print("=" * 60)
    print()
    
    # Create repository
    repo = SkillsRepository(roots=[Path("examples")])
    repo.refresh()
    
    handle = repo.open("test-skill")
    
    # Try various path traversal attacks
    malicious_paths = [
        "../../../etc/passwd",
        "references/../../secrets.txt",
        "/etc/passwd",
        "references/../../../home/user/.ssh/id_rsa",
    ]
    
    for path in malicious_paths:
        print(f"Attempting to read: {path}")
        try:
            content = handle.read_reference(path)
            print(f"  WARNING: Read succeeded! {len(content)} bytes")
        except PathTraversalError as e:
            print(f"  Blocked: {e}")
        except Exception as e:
            print(f"  Error: {type(e).__name__}: {e}")
    print()


def demonstrate_audit_logging():
    """Demonstrate audit logging."""
    print("=" * 60)
    print("Audit Logging Example")
    print("=" * 60)
    print()
    
    # Create audit log file
    audit_file = Path(".cache/audit.jsonl")
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create audit sink
    audit_sink = JSONLAuditSink(audit_file)
    
    print(f"Audit log file: {audit_file}")
    print()
    
    # Create repository with audit logging
    repo = SkillsRepository(
        roots=[Path("examples")],
        execution_policy=ExecutionPolicy(
            enabled=True,
            allow_skills={"test-skill"},
            allow_scripts_glob=["scripts/*.py"],
        ),
        audit_sink=audit_sink,
    )
    
    # Perform operations (all will be audited)
    print("Performing operations (all audited)...")
    
    print("  1. Scanning skills...")
    repo.refresh()
    
    print("  2. Opening skill...")
    handle = repo.open("test-skill")
    
    print("  3. Loading instructions...")
    instructions = handle.instructions()
    
    print("  4. Reading reference...")
    try:
        reference = handle.read_reference("references/example.md")
    except Exception:
        pass
    
    print("  5. Running script...")
    try:
        result = handle.run_script("scripts/hello.py", args=["Audit"])
    except Exception:
        pass
    
    print()
    print(f"Audit log written to: {audit_file}")
    print("View with: cat .cache/audit.jsonl | jq")
    print()
    
    # Read and display audit log
    if audit_file.exists():
        print("Recent audit events:")
        with open(audit_file) as f:
            lines = f.readlines()
            for line in lines[-5:]:  # Last 5 events
                import json
                event = json.loads(line)
                print(f"  - {event['ts']}: {event['kind']} on {event['skill']}")
    print()


def demonstrate_combined_policies():
    """Demonstrate combining all security features."""
    print("=" * 60)
    print("Combined Security Policies Example")
    print("=" * 60)
    print()
    
    # Create comprehensive security configuration
    resource_policy = ResourcePolicy(
        max_file_bytes=100_000,
        max_total_bytes_per_session=500_000,
        allow_extensions_text={".md", ".txt", ".json"},
        allow_binary_assets=False,
    )
    
    execution_policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=["scripts/hello.py"],
        timeout_s_default=10,
        network_access=False,
        env_allowlist={"PATH", "HOME"},
        workdir_mode="tempdir",
    )
    
    audit_sink = StdoutAuditSink()
    
    print("Security Configuration:")
    print("  Resource Policy:")
    print(f"    - Max file: {resource_policy.max_file_bytes} bytes")
    print(f"    - Max session: {resource_policy.max_total_bytes_per_session} bytes")
    print(f"    - Allowed extensions: {resource_policy.allow_extensions_text}")
    print("  Execution Policy:")
    print(f"    - Enabled: {execution_policy.enabled}")
    print(f"    - Allowed skills: {execution_policy.allow_skills}")
    print(f"    - Timeout: {execution_policy.timeout_s_default}s")
    print("  Audit Logging:")
    print(f"    - Enabled: Yes (stdout)")
    print()
    
    # Create repository with all policies
    repo = SkillsRepository(
        roots=[Path("examples")],
        resource_policy=resource_policy,
        execution_policy=execution_policy,
        audit_sink=audit_sink,
    )
    
    print("Repository created with comprehensive security policies")
    print("All operations will be:")
    print("  - Size-limited")
    print("  - Path-validated")
    print("  - Execution-controlled")
    print("  - Fully audited")
    print()


def main():
    """Run all security demonstrations."""
    demonstrate_strict_resource_policy()
    demonstrate_strict_execution_policy()
    demonstrate_disabled_execution()
    demonstrate_path_traversal_prevention()
    demonstrate_audit_logging()
    demonstrate_combined_policies()
    
    print("=" * 60)
    print("Security examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

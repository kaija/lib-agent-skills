#!/usr/bin/env python3
"""Example: ADK integration with Agent Skills Runtime.

This example demonstrates how to integrate skills with ADK agents,
including session management for stateful interactions.

Note: This is a demonstration of the API. Actual ADK integration
would require the ADK framework to be installed and configured.
"""

from pathlib import Path
from agent_skills.runtime import SkillsRepository, SkillSessionManager
from agent_skills.adapters.adk import build_adk_toolset
from agent_skills.models import ExecutionPolicy


def demonstrate_adk_toolset():
    """Demonstrate ADK toolset creation."""
    print("=" * 60)
    print("Agent Skills Runtime - ADK Integration Example")
    print("=" * 60)
    print()
    
    # Initialize repository
    print("Initializing repository...")
    repo = SkillsRepository(
        roots=[Path("examples")],
        execution_policy=ExecutionPolicy(
            enabled=True,
            allow_skills={"test-skill"},
            allow_scripts_glob=["scripts/*.py"],
            timeout_s_default=30,
        )
    )
    repo.refresh()
    print(f"Found {len(repo.list())} skill(s)")
    print()
    
    # Create session manager
    print("Creating session manager...")
    session_manager = SkillSessionManager(repo)
    print()
    
    # Build ADK toolset
    print("Building ADK toolset...")
    tools = build_adk_toolset(repo, session_manager)
    
    print(f"Created {len(tools)} ADK tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
    print()
    
    return repo, session_manager, tools


def demonstrate_tool_calls(repo, session_manager, tools):
    """Demonstrate calling ADK tools."""
    print("=" * 60)
    print("Demonstrating Tool Calls")
    print("=" * 60)
    print()
    
    # Find tools by name
    tools_by_name = {tool["name"]: tool for tool in tools}
    
    # 1. List skills
    print("1. Calling skills.list...")
    list_tool = tools_by_name["skills.list"]
    result = list_tool["handler"]({})
    print(f"Result: {result['ok']}")
    print(f"Found {len(result['content'])} skill(s)")
    for skill in result["content"]:
        print(f"  - {skill['name']}: {skill['description']}")
    print()
    
    # 2. Activate skill
    print("2. Calling skills.activate...")
    activate_tool = tools_by_name["skills.activate"]
    result = activate_tool["handler"]({"name": "test-skill"})
    print(f"Result: {result['ok']}")
    print(f"Type: {result['type']}")
    print(f"Bytes: {result['bytes']}")
    print(f"Instructions preview: {result['content'][:100]}...")
    print()
    
    # 3. Read reference
    print("3. Calling skills.read...")
    read_tool = tools_by_name["skills.read"]
    result = read_tool["handler"]({
        "name": "test-skill",
        "path": "references/example.md"
    })
    print(f"Result: {result['ok']}")
    print(f"Type: {result['type']}")
    print(f"Path: {result['path']}")
    print(f"Content preview: {result['content'][:100]}...")
    print()
    
    # 4. Run script
    print("4. Calling skills.run...")
    run_tool = tools_by_name["skills.run"]
    result = run_tool["handler"]({
        "name": "test-skill",
        "script_path": "scripts/hello.py",
        "args": ["ADK"]
    })
    print(f"Result: {result['ok']}")
    print(f"Type: {result['type']}")
    print(f"Exit code: {result['content']['exit_code']}")
    print(f"Output: {result['content']['stdout'].strip()}")
    print()
    
    # 5. Search references
    print("5. Calling skills.search...")
    search_tool = tools_by_name["skills.search"]
    result = search_tool["handler"]({
        "name": "test-skill",
        "query": "example"
    })
    print(f"Result: {result['ok']}")
    print(f"Type: {result['type']}")
    print(f"Results: {result['meta']['result_count']}")
    print()


def demonstrate_session_management(session_manager):
    """Demonstrate session management."""
    print("=" * 60)
    print("Demonstrating Session Management")
    print("=" * 60)
    print()
    
    # Create a session
    print("Creating session for 'test-skill'...")
    session = session_manager.create_session("test-skill")
    print(f"Session ID: {session.session_id}")
    print(f"Initial state: {session.state.value}")
    print()
    
    # Simulate state transitions
    from agent_skills.models import SkillState
    
    print("Transitioning to INSTRUCTIONS_LOADED...")
    session.transition(SkillState.INSTRUCTIONS_LOADED)
    print(f"Current state: {session.state.value}")
    print()
    
    print("Adding artifact...")
    session.add_artifact("instructions", "# Test Skill\n\nInstructions...")
    print(f"Artifacts: {list(session.artifacts.keys())}")
    print()
    
    print("Transitioning to RESOURCE_NEEDED...")
    session.transition(SkillState.RESOURCE_NEEDED)
    print(f"Current state: {session.state.value}")
    print()
    
    print("Adding another artifact...")
    session.add_artifact("reference", "API documentation...")
    print(f"Artifacts: {list(session.artifacts.keys())}")
    print()
    
    print("Transitioning to DONE...")
    session.transition(SkillState.DONE)
    print(f"Final state: {session.state.value}")
    print()
    
    # Update session
    print("Updating session...")
    session_manager.update_session(session)
    print()
    
    # Retrieve session
    print("Retrieving session...")
    retrieved = session_manager.get_session(session.session_id)
    print(f"Retrieved session ID: {retrieved.session_id}")
    print(f"State: {retrieved.state.value}")
    print(f"Artifacts: {list(retrieved.artifacts.keys())}")
    print(f"Audit events: {len(retrieved.audit)}")
    print()
    
    # List all sessions
    print("Listing all sessions...")
    all_sessions = session_manager.list_sessions()
    print(f"Total sessions: {len(all_sessions)}")
    for s in all_sessions:
        print(f"  - {s.session_id}: {s.skill_name} ({s.state.value})")
    print()


def demonstrate_adk_config(repo, tools):
    """Demonstrate ADK agent configuration."""
    print("=" * 60)
    print("ADK Agent Configuration Example")
    print("=" * 60)
    print()
    
    # Generate system prompt
    system_prompt = f"""You are a helpful assistant with access to skills.

{repo.to_prompt(format="json")}

Available tools:
- skills.list: List all available skills
- skills.activate: Load skill instructions
- skills.read: Read references and documentation
- skills.run: Execute skill scripts
- skills.search: Search skill references

Workflow:
1. Use skills.list to see available skills
2. Use skills.activate to load instructions
3. Use skills.read to access documentation
4. Use skills.run to execute scripts
5. Verify results and complete the task
"""
    
    # ADK agent configuration (pseudo-code)
    agent_config = {
        "tools": tools,
        "system_prompt": system_prompt,
        "max_iterations": 10,
        "temperature": 0,
    }
    
    print("ADK Agent Configuration:")
    print(f"  Tools: {len(agent_config['tools'])}")
    print(f"  Max iterations: {agent_config['max_iterations']}")
    print(f"  Temperature: {agent_config['temperature']}")
    print()
    
    print("System Prompt:")
    print("-" * 60)
    print(system_prompt[:500] + "...")
    print("-" * 60)
    print()
    
    print("Note: To use this configuration with ADK:")
    print("  1. Install ADK framework")
    print("  2. Create ADK agent with this config")
    print("  3. Run agent with user queries")
    print()


def main():
    """Run all demonstrations."""
    # Create toolset
    repo, session_manager, tools = demonstrate_adk_toolset()
    
    # Demonstrate tool calls
    demonstrate_tool_calls(repo, session_manager, tools)
    
    # Demonstrate session management
    demonstrate_session_management(session_manager)
    
    # Demonstrate configuration
    demonstrate_adk_config(repo, tools)
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

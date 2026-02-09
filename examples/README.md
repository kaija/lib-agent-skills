# Agent Skills Runtime - Examples

This directory contains comprehensive examples demonstrating the Agent Skills Runtime workflow.

## Examples

### 1. Simple Example: CSV to JSON Conversion

**`full_autonomous_example.py`** - Basic autonomous workflow

Demonstrates a simple task where SKILL.md instructions are sufficient:
- ✅ Initialize repository and discover skills
- ✅ Create autonomous agent with LLM
- ✅ Agent autonomously selects appropriate skills
- ✅ Agent reads SKILL.md instructions
- ✅ Agent executes script (no reference reading needed)
- ✅ Agent returns final result

**When to use**: Learning the basics, simple data transformations

**Run**:
```bash
python full_autonomous_example.py
```

### 2. Complex Example: Data Validation with Schema

**`complex_validation_example.py`** - Advanced workflow requiring reference files

Demonstrates a complex task that REQUIRES reading reference documentation:
- ✅ Initialize repository and discover skills
- ✅ Create autonomous agent with LLM
- ✅ Agent reads SKILL.md instructions
- ✅ **Agent reads api-docs.md to understand schema format (REQUIRED)**
- ✅ **Agent reads examples.json to see validation patterns (REQUIRED)**
- ✅ Agent creates custom validation schema
- ✅ Agent uses skills_write_file to save schema
- ✅ Agent executes validation with schema
- ✅ Agent returns detailed validation report

**When to use**: Understanding complex workflows, schema validation, reference file usage

**Run**:
```bash
python complex_validation_example.py
```

**Why references are required**:
- Schema format is complex and not fully documented in SKILL.md
- Validation rules syntax must be learned from api-docs.md
- Examples in examples.json show proper schema structure
- Without references, agent cannot create a valid schema

### 3. Skill Creator Example: Using Skills to Create Skills

**`skill_creator_example.py`** - Using skill-creator skill to create new skills ✨ NEW

Demonstrates using the skill-creator skill to guide the creation of a new CSV-to-JSON converter skill:
- ✅ Agent activates the skill-creator skill
- ✅ Agent reads skill-creator's reference documentation (workflows.md, output-patterns.md)
- ✅ Agent runs init_skill.py to create skill structure
- ✅ Agent writes SKILL.md with proper YAML frontmatter
- ✅ Agent writes reference documentation (formats.md)
- ✅ Agent writes functional Python conversion script
- ✅ Agent runs package_skill.py to validate and package
- ✅ Creates distributable .skill file

**When to use**: Creating custom skills, learning skill structure, following best practices

**Run**:
```bash
python skill_creator_example.py
```

**What gets created**:
- Complete csv-json-converter skill following skill-creator's 6-step process
- SKILL.md with frontmatter and instructions
- references/formats.md with format documentation
- scripts/convert.py with working conversion logic
- csv-json-converter.skill package file (validated and ready to distribute)

## Comparison

| Feature | Simple | Complex | Skill Creator |
|---------|--------|---------|---------------|
| Task Complexity | Low | High | Very High |
| Reference Reading | ❌ Not needed | ✅ Required | ✅ Required |
| File Writing | ❌ No | ✅ Yes (schema) | ✅ Yes (multiple) |
| Script Execution | ✅ Yes | ✅ Yes | ✅ Yes (init & package) |
| SKILL.md Sufficient | ✅ Yes | ❌ No | ❌ No |
| Schema Creation | ❌ No | ✅ Yes | ❌ No |
| Skill Creation | ❌ No | ❌ No | ✅ Yes |
| Uses Existing Skill | ✅ Yes | ✅ Yes | ✅ Yes (skill-creator) |
| Iterations | 2-3 | 5-7 | 10-15 |
| Learning Value | Basic workflow | Advanced patterns | Skill creation process |

## Features Demonstrated

### All Examples
- **Skill Discovery**: Automatic scanning and indexing
- **Lazy Loading**: Progressive disclosure of skill content
- **Autonomous Selection**: LLM-driven skill selection
- **Instruction Loading**: Reading SKILL.md for guidance
- **Script Execution**: Running scripts with approval mechanism
- **Detailed Logging**: Step-by-step progress tracking
- **Security**: Execution policies and approval callbacks

### Complex Example Only
- **Reference Reading**: Accessing detailed documentation
- **Schema Creation**: Building validation schemas from requirements
- **File Writing**: Using skills_write_file tool
- **Complex Arguments**: Multi-parameter script execution
- **Error Analysis**: Detailed validation reporting

### Skill Creator Example Only
- **Using Existing Skills**: Leveraging skill-creator skill for guidance
- **Reference Reading**: Reading workflows.md and output-patterns.md
- **Script Execution**: Running init_skill.py and package_skill.py
- **Multi-file Creation**: Creating complete skill directory structure
- **YAML Frontmatter**: Proper skill metadata following conventions
- **Script Generation**: Creating functional Python code
- **Skill Packaging**: Validating and creating distributable .skill files
- **Verification**: Checking all files were created correctly

## Running the Examples

### Prerequisites

```bash
# Install the library
pip install -e ..

# Install LangChain and OpenAI
pip install langchain-openai

# Set OpenAI API key
export OPENAI_API_KEY='your-api-key-here'
```

### Run Simple Example

```bash
python full_autonomous_example.py
```

**Expected behavior**:
1. Creates sample CSV file
2. Agent selects data-processor skill
3. Agent reads SKILL.md
4. Agent executes conversion script
5. Outputs JSON file

**Time**: ~30-60 seconds

### Run Complex Example

```bash
python complex_validation_example.py
```

**Expected behavior**:
1. Creates sample CSV with validation issues
2. Agent selects data-processor skill
3. Agent reads SKILL.md
4. **Agent reads api-docs.md (schema format)**
5. **Agent reads examples.json (validation examples)**
6. Agent creates validation schema
7. Agent uses skills_write_file to save schema
8. Agent executes validation script
9. Outputs detailed validation report

**Time**: ~60-120 seconds

### Run Skill Creator Example

```bash
python skill_creator_example.py
```

**Expected behavior**:
1. Agent activates skill-creator skill
2. Agent reads skill-creator's SKILL.md
3. Agent reads workflows.md and output-patterns.md references
4. Agent runs init_skill.py to create directory structure
5. Agent writes SKILL.md with proper frontmatter
6. Agent writes references/formats.md with documentation
7. Agent writes scripts/convert.py with conversion logic
8. Agent runs package_skill.py to validate and package
9. Creates csv-json-converter.skill package file
10. Verifies all files created successfully

**Time**: ~90-180 seconds

## Sample Output

### Skill Creator Example Output

```
================================================================================
  SKILL CREATOR EXAMPLE
================================================================================

→ STEP 1: Initialize Skills Repository
   ✓ Found 4 existing skills

→ STEP 2: Initialize Language Model
   ✓ OpenAI GPT-4 initialized

→ STEP 3: Create Autonomous Agent
   ✓ Autonomous agent created

→ STEP 4: Define Skill Creation Task
   Task: Create csv-json-converter skill

[Agent execution with 10-15 iterations]

================================================================================
  STEP 6: VERIFY SKILL CREATION
================================================================================

🔍 Verifying skill files...
   ✅ csv-json-converter/SKILL.md (1234 bytes)
   ✅ csv-json-converter/references/formats.md (856 bytes)
   ✅ csv-json-converter/scripts/convert.py (2048 bytes)
   ✅ csv-json-converter.skill (4096 bytes)

✅ All skill files created successfully!

================================================================================
  STEP 7: TEST THE NEW SKILL
================================================================================

🧪 Testing the new skill...
   ✅ New skill discovered by repository!
   ✅ Skill activated successfully!
   ✅ Package file ready for distribution!
```

## Sample Skills

The `skills/` directory contains example skills:

- **`data-processor/`**: Process CSV data
  - SKILL.md with instructions
  - references/api-docs.md - Detailed API documentation
  - references/examples.json - Validation examples
  - scripts/process.py - Main processing script

- **`api-client/`**: Call external APIs
- **`web-scraper/`**: Web scraping skill
- **`file-manager/`**: File operations skill
- **`skill-creator/`**: Guide for creating new skills ✨
  - SKILL.md with 6-step creation process
  - references/workflows.md - Sequential and conditional workflow patterns
  - references/output-patterns.md - Template and example patterns
  - scripts/init_skill.py - Initialize new skill structure
  - scripts/package_skill.py - Validate and package skills
  - scripts/quick_validate.py - Quick validation utility

- **`csv-json-converter/`**: Created by skill_creator_example.py ✨
  - Example of a skill created using the skill-creator skill

## Creating Your Own Skills

### Manual Creation

1. Create a directory with your skill name
2. Add `SKILL.md` with frontmatter and instructions
3. Add `references/` directory with detailed documentation
4. Add `scripts/` directory with executable scripts
5. Optionally add `assets/` directory with binary files

### Using the Agent

Run the skill creator example and modify the task to create your desired skill!

```python
task = f"""Create a new skill called "my-custom-skill" in {skills_dir}/my-custom-skill

SKILL REQUIREMENTS:
1. Name: my-custom-skill
2. Description: What your skill does
3. License: MIT

[... rest of requirements ...]
"""
```

## Documentation

For more information, see:
- Main README: `../README.md`
- Quick Start: `../.kiro/specs/agent-skills-runtime/QUICK_START.md`
- When to Read References: `../docs/when_to_read_references.md`
- Requirements: `../.kiro/specs/agent-skills-runtime/requirements.md`
- Design: `../.kiro/specs/agent-skills-runtime/design.md`
- Autonomous Agent Guide: `../docs/autonomous_agent.md`
- File Operations: `../FILE_OPERATIONS_ADDED.md`

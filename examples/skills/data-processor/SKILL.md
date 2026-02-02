---
name: data-processor
description: Process CSV and JSON data files with validation and transformation
license: MIT
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Agent Skills Team
  version: 1.0.0
  category: data-processing
allowed_tools:
  - skills.read
  - skills.run
---

# Data Processor Skill

This skill provides tools for processing, validating, and transforming CSV and JSON data files.

## Overview

The data processor skill helps agents work with structured data by providing:
- CSV file parsing and validation
- JSON data transformation
- Data quality checks
- Format conversion utilities

## Usage Workflow

1. **Read the API documentation** from `references/api-docs.md` to understand available operations
2. **Review examples** in `references/examples.json` for common use cases
3. **Execute the setup script** if needed: `scripts/setup.py`
4. **Process your data** using `scripts/process.py`

## Available Operations

### Data Validation

Validate CSV or JSON files for:
- Schema compliance
- Data type correctness
- Required field presence
- Value range checks

### Data Transformation

Transform data between formats:
- CSV to JSON
- JSON to CSV
- Data filtering
- Column selection
- Row aggregation

### Data Quality

Check data quality:
- Missing value detection
- Duplicate detection
- Outlier identification
- Statistical summaries

## Script Usage

### Setup Script

```bash
scripts/setup.py
```

Initializes the data processing environment and validates dependencies.

### Process Script

```bash
scripts/process.py --input data.csv --output result.json --operation validate
```

**Arguments:**
- `--input`: Input file path (CSV or JSON)
- `--output`: Output file path
- `--operation`: Operation to perform (validate, transform, quality-check)
- `--schema`: Optional schema file for validation

## Examples

See `references/examples.json` for detailed examples of:
- Validating customer data
- Converting sales reports
- Checking data quality
- Filtering and aggregating records

## Error Handling

The skill provides clear error messages for:
- Invalid file formats
- Schema validation failures
- Missing required fields
- Type conversion errors

## Best Practices

1. Always validate data before transformation
2. Use schema files for consistent validation
3. Check data quality reports before processing
4. Handle missing values appropriately
5. Test with sample data first

## Limitations

- Maximum file size: 10MB
- Supported formats: CSV, JSON
- Requires Python 3.10+
- No support for Excel files (use CSV export)

## Support

For issues or questions:
- Check the API documentation in references/
- Review examples in references/examples.json
- Consult the troubleshooting guide in references/troubleshooting.md

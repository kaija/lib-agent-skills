# Data Processor API Documentation

## Overview

The Data Processor skill provides a command-line interface for processing structured data files.

## Command-Line Interface

### process.py

Main processing script for data operations.

#### Syntax

```bash
python scripts/process.py [OPTIONS]
```

#### Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--input` | string | Yes | Path to input file (CSV or JSON) |
| `--output` | string | Yes | Path to output file |
| `--operation` | string | Yes | Operation: validate, transform, quality-check |
| `--schema` | string | No | Path to schema file for validation |
| `--format` | string | No | Output format: csv, json (default: auto-detect) |
| `--verbose` | flag | No | Enable verbose output |

#### Operations

##### validate

Validates data against a schema.

**Example:**
```bash
python scripts/process.py \
  --input data.csv \
  --output report.json \
  --operation validate \
  --schema schema.json
```

**Output:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Missing optional field: phone"],
  "record_count": 1000
}
```

##### transform

Transforms data between formats or applies filters.

**Example:**
```bash
python scripts/process.py \
  --input data.csv \
  --output data.json \
  --operation transform \
  --format json
```

**Output:**
```json
{
  "records": [
    {"id": 1, "name": "Alice", "age": 30},
    {"id": 2, "name": "Bob", "age": 25}
  ],
  "count": 2
}
```

##### quality-check

Analyzes data quality and generates a report.

**Example:**
```bash
python scripts/process.py \
  --input data.csv \
  --output quality.json \
  --operation quality-check
```

**Output:**
```json
{
  "total_records": 1000,
  "missing_values": {
    "email": 50,
    "phone": 100
  },
  "duplicates": 5,
  "outliers": {
    "age": [150, 200]
  }
}
```

## Schema Format

Schemas are JSON files defining data structure and validation rules.

### Example Schema

```json
{
  "fields": [
    {
      "name": "id",
      "type": "integer",
      "required": true,
      "unique": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true,
      "min_length": 1,
      "max_length": 100
    },
    {
      "name": "email",
      "type": "string",
      "required": true,
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    },
    {
      "name": "age",
      "type": "integer",
      "required": false,
      "min": 0,
      "max": 150
    }
  ]
}
```

### Field Types

- `integer`: Whole numbers
- `float`: Decimal numbers
- `string`: Text values
- `boolean`: true/false values
- `date`: ISO 8601 date strings
- `datetime`: ISO 8601 datetime strings

### Validation Rules

| Rule | Types | Description |
|------|-------|-------------|
| `required` | All | Field must be present |
| `unique` | All | Values must be unique |
| `min` | integer, float | Minimum value |
| `max` | integer, float | Maximum value |
| `min_length` | string | Minimum string length |
| `max_length` | string | Maximum string length |
| `pattern` | string | Regex pattern match |
| `enum` | All | Value must be in list |

## Error Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Invalid arguments |
| 2 | File not found |
| 3 | Invalid file format |
| 4 | Validation failed |
| 5 | Transformation error |
| 6 | Quality check failed |

## Exit Codes

The script returns:
- `0` on success
- Non-zero on error (see error codes above)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATA_PROCESSOR_MAX_SIZE` | Maximum file size in MB | 10 |
| `DATA_PROCESSOR_ENCODING` | File encoding | utf-8 |
| `DATA_PROCESSOR_DELIMITER` | CSV delimiter | , |

## Performance

### File Size Limits

- Maximum file size: 10MB (configurable)
- Maximum records: 100,000
- Maximum field count: 100

### Processing Time

Typical processing times:
- 1,000 records: < 1 second
- 10,000 records: < 5 seconds
- 100,000 records: < 30 seconds

## Troubleshooting

### Common Issues

#### "File not found"

Ensure the input file path is correct and the file exists.

#### "Invalid file format"

Check that the file is valid CSV or JSON. Use a validator to verify.

#### "Validation failed"

Review the validation report for specific errors. Check schema definition.

#### "Memory error"

File may be too large. Try processing in chunks or increasing memory limits.

## Best Practices

1. **Always validate before transforming** - Catch errors early
2. **Use schemas** - Define clear data contracts
3. **Check quality first** - Understand your data before processing
4. **Handle errors gracefully** - Check exit codes and error messages
5. **Test with samples** - Validate logic with small datasets first

## Version History

- **1.0.0** (2024-01-01): Initial release
  - CSV and JSON support
  - Basic validation
  - Format transformation
  - Quality checking

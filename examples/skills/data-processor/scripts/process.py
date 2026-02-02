#!/usr/bin/env python3
"""Data processing script for validation, transformation, and quality checking.

This is a simplified demonstration script. A production version would include
more robust error handling, streaming for large files, and additional features.
"""

import sys
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Any


def validate_data(input_file: Path, schema: Dict) -> Dict:
    """Validate data against schema."""
    errors = []
    warnings = []
    record_count = 0
    
    # Read data
    with open(input_file) as f:
        if input_file.suffix == ".csv":
            reader = csv.DictReader(f)
            records = list(reader)
        else:
            data = json.load(f)
            records = data if isinstance(data, list) else data.get("records", [])
    
    record_count = len(records)
    
    # Validate each record
    for i, record in enumerate(records):
        for field in schema.get("fields", []):
            field_name = field["name"]
            
            # Check required fields
            if field.get("required") and field_name not in record:
                errors.append(f"Record {i}: Missing required field '{field_name}'")
            
            # Check field presence for optional fields
            if field_name in record:
                value = record[field_name]
                
                # Type validation (simplified)
                if field["type"] == "integer":
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        errors.append(f"Record {i}: Field '{field_name}' is not an integer")
                
                # Min/max validation
                if "min" in field:
                    try:
                        if float(value) < field["min"]:
                            errors.append(f"Record {i}: Field '{field_name}' below minimum")
                    except (ValueError, TypeError):
                        pass
                
                if "max" in field:
                    try:
                        if float(value) > field["max"]:
                            errors.append(f"Record {i}: Field '{field_name}' above maximum")
                    except (ValueError, TypeError):
                        pass
            elif not field.get("required"):
                warnings.append(f"Record {i}: Optional field '{field_name}' missing")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors[:10],  # Limit to first 10
        "warnings": warnings[:10],
        "record_count": record_count
    }


def transform_data(input_file: Path, output_format: str) -> Dict:
    """Transform data between formats."""
    # Read input
    with open(input_file) as f:
        if input_file.suffix == ".csv":
            reader = csv.DictReader(f)
            records = list(reader)
        else:
            data = json.load(f)
            records = data if isinstance(data, list) else data.get("records", [])
    
    # Return in requested format
    if output_format == "json":
        return {
            "records": records,
            "count": len(records)
        }
    else:
        # For CSV, return records as-is (will be written by caller)
        return {
            "records": records,
            "count": len(records)
        }


def quality_check(input_file: Path) -> Dict:
    """Check data quality."""
    # Read data
    with open(input_file) as f:
        if input_file.suffix == ".csv":
            reader = csv.DictReader(f)
            records = list(reader)
        else:
            data = json.load(f)
            records = data if isinstance(data, list) else data.get("records", [])
    
    # Analyze quality
    total_records = len(records)
    missing_values = {}
    seen_records = {}
    duplicates = 0
    
    for record in records:
        # Check missing values
        for key, value in record.items():
            if not value or value == "":
                missing_values[key] = missing_values.get(key, 0) + 1
        
        # Check duplicates (simplified - just by ID if present)
        if "id" in record:
            record_id = record["id"]
            if record_id in seen_records:
                duplicates += 1
            seen_records[record_id] = True
    
    return {
        "total_records": total_records,
        "missing_values": missing_values,
        "duplicates": duplicates,
        "outliers": {}  # Simplified - would need statistical analysis
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process data files")
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--operation", required=True,
                       choices=["validate", "transform", "quality-check"],
                       help="Operation to perform")
    parser.add_argument("--schema", help="Schema file for validation")
    parser.add_argument("--format", choices=["csv", "json"],
                       help="Output format")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_file = Path(args.output)
    
    # Check input exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        return 2
    
    try:
        # Perform operation
        if args.operation == "validate":
            if not args.schema:
                print("Error: --schema required for validation", file=sys.stderr)
                return 1
            
            with open(args.schema) as f:
                schema = json.load(f)
            
            result = validate_data(input_file, schema)
            
            # Write result
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            
            if args.verbose:
                print(f"Validation {'passed' if result['valid'] else 'failed'}")
                print(f"Records: {result['record_count']}")
                print(f"Errors: {len(result['errors'])}")
            
            return 0 if result["valid"] else 4
        
        elif args.operation == "transform":
            output_format = args.format or output_file.suffix[1:]
            result = transform_data(input_file, output_format)
            
            # Write result
            if output_format == "json":
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
            else:
                with open(output_file, "w", newline="") as f:
                    if result["records"]:
                        writer = csv.DictWriter(f, fieldnames=result["records"][0].keys())
                        writer.writeheader()
                        writer.writerows(result["records"])
            
            if args.verbose:
                print(f"Transformed {result['count']} records")
            
            return 0
        
        elif args.operation == "quality-check":
            result = quality_check(input_file)
            
            # Write result
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            
            if args.verbose:
                print(f"Quality check complete")
                print(f"Total records: {result['total_records']}")
                print(f"Missing values: {sum(result['missing_values'].values())}")
                print(f"Duplicates: {result['duplicates']}")
            
            return 0
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())

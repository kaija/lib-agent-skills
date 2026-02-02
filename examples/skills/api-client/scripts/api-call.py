#!/usr/bin/env python3
"""API client script for making HTTP requests.

This is a simplified demonstration script. A production version would use
the requests library and include more robust error handling.
"""

import sys
import json
import argparse
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Dict, Any, Optional


def make_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Make HTTP request."""
    if headers is None:
        headers = {}
    
    # Prepare request
    req_data = data.encode("utf-8") if data else None
    request = Request(url, data=req_data, headers=headers, method=method)
    
    start_time = time.time()
    
    try:
        with urlopen(request, timeout=timeout) as response:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Read response
            body = response.read().decode("utf-8")
            
            # Parse JSON if possible
            try:
                body_json = json.loads(body)
            except json.JSONDecodeError:
                body_json = body
            
            return {
                "success": True,
                "status_code": response.status,
                "headers": dict(response.headers),
                "body": body_json,
                "duration_ms": duration_ms,
                "retries": 0,
            }
    
    except HTTPError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Try to read error body
        try:
            error_body = e.read().decode("utf-8")
            try:
                error_json = json.loads(error_body)
            except json.JSONDecodeError:
                error_json = error_body
        except Exception:
            error_json = None
        
        return {
            "success": False,
            "error": f"HTTP {e.code}: {e.reason}",
            "status_code": e.code,
            "body": error_json,
            "duration_ms": duration_ms,
            "retries": 0,
        }
    
    except URLError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "error": f"Connection error: {e.reason}",
            "status_code": None,
            "duration_ms": duration_ms,
            "retries": 0,
        }
    
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "error": str(e),
            "status_code": None,
            "duration_ms": duration_ms,
            "retries": 0,
        }


def should_retry(response: Dict[str, Any]) -> bool:
    """Determine if request should be retried."""
    if response["success"]:
        return False
    
    status_code = response.get("status_code")
    
    # Retry on specific status codes
    if status_code in [429, 500, 502, 503, 504]:
        return True
    
    # Retry on connection errors
    if status_code is None:
        return True
    
    return False


def make_request_with_retry(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    timeout: int = 30,
    max_retries: int = 3,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Make HTTP request with retry logic."""
    retries = 0
    wait_time = 1
    
    while retries <= max_retries:
        if verbose and retries > 0:
            print(f"Retry attempt {retries}/{max_retries}...", file=sys.stderr)
        
        response = make_request(url, method, headers, data, timeout)
        
        if not should_retry(response):
            response["retries"] = retries
            return response
        
        retries += 1
        
        if retries <= max_retries:
            if verbose:
                print(f"Request failed, waiting {wait_time}s before retry...", file=sys.stderr)
            time.sleep(wait_time)
            wait_time = min(wait_time * 2, 60)  # Exponential backoff, max 60s
    
    response["retries"] = retries
    return response


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Make HTTP API calls")
    parser.add_argument("--url", required=True, help="API endpoint URL")
    parser.add_argument("--method", default="GET",
                       choices=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       help="HTTP method")
    parser.add_argument("--auth-token", help="Bearer token for authentication")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--headers", help="Additional headers as JSON")
    parser.add_argument("--data", help="Request body as JSON")
    parser.add_argument("--timeout", type=int, default=30,
                       help="Request timeout in seconds")
    parser.add_argument("--retries", type=int, default=3,
                       help="Maximum retry attempts")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Build headers
    headers = {
        "User-Agent": "AgentSkills-APIClient/1.0",
        "Accept": "application/json",
    }
    
    # Add authentication
    if args.auth_token:
        headers["Authorization"] = f"Bearer {args.auth_token}"
    
    if args.api_key:
        headers["X-API-Key"] = args.api_key
    
    # Add custom headers
    if args.headers:
        try:
            custom_headers = json.loads(args.headers)
            headers.update(custom_headers)
        except json.JSONDecodeError:
            print("Error: Invalid JSON in --headers", file=sys.stderr)
            return 1
    
    # Add content-type for POST/PUT/PATCH
    if args.method in ["POST", "PUT", "PATCH"] and args.data:
        headers["Content-Type"] = "application/json"
    
    if args.verbose:
        print(f"Making {args.method} request to {args.url}", file=sys.stderr)
        print(f"Headers: {json.dumps(headers, indent=2)}", file=sys.stderr)
        if args.data:
            print(f"Data: {args.data}", file=sys.stderr)
    
    # Make request
    response = make_request_with_retry(
        url=args.url,
        method=args.method,
        headers=headers,
        data=args.data,
        timeout=args.timeout,
        max_retries=args.retries,
        verbose=args.verbose,
    )
    
    # Output response
    print(json.dumps(response, indent=2))
    
    # Return appropriate exit code
    if response["success"]:
        return 0
    else:
        status_code = response.get("status_code")
        if status_code and 400 <= status_code < 500:
            return 1  # Client error
        else:
            return 2  # Server error or network error


if __name__ == "__main__":
    sys.exit(main())

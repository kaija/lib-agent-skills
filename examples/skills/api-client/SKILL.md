---
name: api-client
description: Make HTTP API calls with authentication, retry logic, and error handling
license: MIT
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Agent Skills Team
  version: 1.0.0
  category: api-integration
allowed_tools:
  - skills.read
  - skills.run
---

# API Client Skill

This skill provides tools for making HTTP API calls with built-in authentication, retry logic, and comprehensive error handling.

## Overview

The API client skill helps agents interact with REST APIs by providing:
- HTTP method support (GET, POST, PUT, DELETE, PATCH)
- Authentication (Bearer token, API key, Basic auth)
- Automatic retry with exponential backoff
- Request/response logging
- Error handling and status code interpretation

## Usage Workflow

1. **Read the API documentation** from `references/api-guide.md` to understand capabilities
2. **Review authentication methods** in `references/auth-methods.md`
3. **Check examples** in `references/examples.md` for common patterns
4. **Make API calls** using `scripts/api-call.py`

## Available Features

### HTTP Methods

Supports all standard HTTP methods:
- **GET**: Retrieve resources
- **POST**: Create resources
- **PUT**: Update resources (full replacement)
- **PATCH**: Update resources (partial update)
- **DELETE**: Remove resources

### Authentication

Multiple authentication methods:
- **Bearer Token**: OAuth 2.0 and JWT tokens
- **API Key**: Header or query parameter
- **Basic Auth**: Username and password
- **Custom Headers**: Any custom authentication scheme

### Retry Logic

Automatic retry with:
- Exponential backoff
- Configurable max retries
- Retry on specific status codes (429, 500, 502, 503, 504)
- Timeout handling

### Error Handling

Comprehensive error handling for:
- Network errors
- Timeout errors
- Authentication failures
- Rate limiting (429)
- Server errors (5xx)
- Client errors (4xx)

## Script Usage

### API Call Script

```bash
scripts/api-call.py --url https://api.example.com/users --method GET --auth-token YOUR_TOKEN
```

**Arguments:**
- `--url`: API endpoint URL (required)
- `--method`: HTTP method (default: GET)
- `--auth-token`: Bearer token for authentication
- `--api-key`: API key (header or query param)
- `--headers`: Additional headers as JSON
- `--data`: Request body as JSON (for POST/PUT/PATCH)
- `--timeout`: Request timeout in seconds (default: 30)
- `--retries`: Maximum retry attempts (default: 3)
- `--verbose`: Enable verbose output

## Examples

### Simple GET Request

```bash
python scripts/api-call.py \
  --url https://api.example.com/users/123 \
  --method GET \
  --auth-token abc123
```

### POST with JSON Data

```bash
python scripts/api-call.py \
  --url https://api.example.com/users \
  --method POST \
  --auth-token abc123 \
  --data '{"name": "Alice", "email": "alice@example.com"}'
```

### Custom Headers

```bash
python scripts/api-call.py \
  --url https://api.example.com/data \
  --method GET \
  --headers '{"X-Custom-Header": "value", "Accept": "application/json"}'
```

See `references/examples.md` for more detailed examples.

## Response Format

The script returns JSON with:
```json
{
  "success": true,
  "status_code": 200,
  "headers": {...},
  "body": {...},
  "duration_ms": 123,
  "retries": 0
}
```

## Error Handling

Errors are returned as:
```json
{
  "success": false,
  "error": "Connection timeout",
  "status_code": null,
  "retries": 3
}
```

## Best Practices

1. **Always use authentication** - Never make unauthenticated calls to protected APIs
2. **Handle rate limits** - Respect 429 responses and retry-after headers
3. **Validate responses** - Check status codes and response structure
4. **Use timeouts** - Set appropriate timeouts for your use case
5. **Log requests** - Enable verbose mode for debugging
6. **Secure credentials** - Never hardcode tokens or API keys

## Rate Limiting

The skill respects rate limits:
- Automatically retries on 429 (Too Many Requests)
- Honors Retry-After header
- Implements exponential backoff
- Configurable max retries

## Security Considerations

- Credentials are passed as arguments (not stored)
- HTTPS is enforced for authenticated requests
- Sensitive data is not logged by default
- Timeout prevents hanging requests

## Limitations

- Maximum request size: 10MB
- Maximum response size: 10MB
- Timeout range: 1-300 seconds
- Max retries: 10
- No support for file uploads (use multipart/form-data separately)

## Troubleshooting

### Connection Errors

- Check network connectivity
- Verify URL is correct
- Ensure firewall allows outbound connections

### Authentication Errors

- Verify token/API key is valid
- Check token hasn't expired
- Ensure correct authentication method

### Timeout Errors

- Increase timeout value
- Check API endpoint performance
- Verify network latency

### Rate Limit Errors

- Reduce request frequency
- Implement backoff strategy
- Check API rate limit documentation

## Support

For issues or questions:
- Check the API guide in references/api-guide.md
- Review authentication methods in references/auth-methods.md
- Consult examples in references/examples.md

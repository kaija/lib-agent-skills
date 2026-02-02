# API Client Guide

## Overview

The API Client skill provides a command-line interface for making HTTP API calls with authentication, retry logic, and error handling.

## Quick Start

### Basic GET Request

```bash
python scripts/api-call.py --url https://api.example.com/users
```

### Authenticated Request

```bash
python scripts/api-call.py \
  --url https://api.example.com/users \
  --auth-token YOUR_TOKEN_HERE
```

### POST Request with Data

```bash
python scripts/api-call.py \
  --url https://api.example.com/users \
  --method POST \
  --auth-token YOUR_TOKEN \
  --data '{"name": "Alice", "email": "alice@example.com"}'
```

## Command-Line Options

### Required Options

| Option | Description |
|--------|-------------|
| `--url` | API endpoint URL |

### Optional Options

| Option | Default | Description |
|--------|---------|-------------|
| `--method` | GET | HTTP method (GET, POST, PUT, PATCH, DELETE) |
| `--auth-token` | None | Bearer token for authentication |
| `--api-key` | None | API key for authentication |
| `--headers` | {} | Additional headers as JSON string |
| `--data` | None | Request body as JSON string |
| `--timeout` | 30 | Request timeout in seconds |
| `--retries` | 3 | Maximum retry attempts |
| `--verbose` | False | Enable verbose output |

## HTTP Methods

### GET - Retrieve Resources

Retrieve data from the API.

```bash
python scripts/api-call.py \
  --url https://api.example.com/users/123 \
  --method GET
```

**Use cases:**
- Fetch user data
- List resources
- Get status information

### POST - Create Resources

Create new resources.

```bash
python scripts/api-call.py \
  --url https://api.example.com/users \
  --method POST \
  --data '{"name": "Bob", "email": "bob@example.com"}'
```

**Use cases:**
- Create new users
- Submit forms
- Upload data

### PUT - Update Resources (Full)

Replace entire resource.

```bash
python scripts/api-call.py \
  --url https://api.example.com/users/123 \
  --method PUT \
  --data '{"name": "Bob Updated", "email": "bob@example.com", "age": 30}'
```

**Use cases:**
- Full resource updates
- Replace configuration
- Update all fields

### PATCH - Update Resources (Partial)

Update specific fields.

```bash
python scripts/api-call.py \
  --url https://api.example.com/users/123 \
  --method PATCH \
  --data '{"email": "newemail@example.com"}'
```

**Use cases:**
- Partial updates
- Change specific fields
- Incremental modifications

### DELETE - Remove Resources

Delete resources.

```bash
python scripts/api-call.py \
  --url https://api.example.com/users/123 \
  --method DELETE
```

**Use cases:**
- Remove users
- Delete records
- Clean up resources

## Authentication

### Bearer Token

Most common for OAuth 2.0 and JWT.

```bash
python scripts/api-call.py \
  --url https://api.example.com/protected \
  --auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Adds header: `Authorization: Bearer <token>`

### API Key

For API key authentication.

```bash
python scripts/api-call.py \
  --url https://api.example.com/data \
  --api-key your-api-key-here
```

Adds header: `X-API-Key: <key>`

### Custom Headers

For custom authentication schemes.

```bash
python scripts/api-call.py \
  --url https://api.example.com/data \
  --headers '{"X-Custom-Auth": "custom-value"}'
```

## Retry Logic

The client automatically retries failed requests with exponential backoff.

### Retry Conditions

Retries occur for:
- Network errors (connection timeout, DNS failure)
- HTTP 429 (Too Many Requests)
- HTTP 500 (Internal Server Error)
- HTTP 502 (Bad Gateway)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)

### Retry Strategy

1. **First retry**: Wait 1 second
2. **Second retry**: Wait 2 seconds
3. **Third retry**: Wait 4 seconds
4. **Subsequent retries**: Double wait time (max 60 seconds)

### Configuring Retries

```bash
python scripts/api-call.py \
  --url https://api.example.com/data \
  --retries 5
```

## Response Format

### Success Response

```json
{
  "success": true,
  "status_code": 200,
  "headers": {
    "content-type": "application/json",
    "content-length": "123"
  },
  "body": {
    "id": 123,
    "name": "Alice",
    "email": "alice@example.com"
  },
  "duration_ms": 234,
  "retries": 0
}
```

### Error Response

```json
{
  "success": false,
  "error": "Connection timeout after 30 seconds",
  "status_code": null,
  "retries": 3,
  "duration_ms": 90000
}
```

## Status Codes

### 2xx Success

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 204 | No Content | Success with no response body |

### 4xx Client Errors

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Check authentication |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Check URL |
| 429 | Too Many Requests | Retry with backoff |

### 5xx Server Errors

| Code | Meaning | Action |
|------|---------|--------|
| 500 | Internal Server Error | Retry |
| 502 | Bad Gateway | Retry |
| 503 | Service Unavailable | Retry |
| 504 | Gateway Timeout | Retry |

## Error Handling

### Network Errors

```json
{
  "success": false,
  "error": "Connection refused",
  "status_code": null
}
```

**Causes:**
- Server is down
- Incorrect URL
- Network connectivity issues

### Timeout Errors

```json
{
  "success": false,
  "error": "Request timeout after 30 seconds",
  "status_code": null
}
```

**Solutions:**
- Increase timeout value
- Check server performance
- Verify network latency

### Authentication Errors

```json
{
  "success": false,
  "error": "Unauthorized",
  "status_code": 401
}
```

**Solutions:**
- Verify token is valid
- Check token hasn't expired
- Ensure correct authentication method

## Best Practices

### 1. Always Use HTTPS

```bash
# Good
--url https://api.example.com/data

# Bad (for sensitive data)
--url http://api.example.com/data
```

### 2. Set Appropriate Timeouts

```bash
# Quick operations
--timeout 10

# Long-running operations
--timeout 120
```

### 3. Handle Rate Limits

```bash
# Allow retries for rate limits
--retries 5
```

### 4. Validate Responses

Always check:
- `success` field
- `status_code`
- Response body structure

### 5. Use Verbose Mode for Debugging

```bash
--verbose
```

## Performance Tips

### Reduce Latency

1. Use appropriate timeouts
2. Minimize request size
3. Use compression (Accept-Encoding: gzip)
4. Cache responses when possible

### Handle Large Responses

1. Use pagination
2. Request only needed fields
3. Stream large responses
4. Set appropriate timeouts

## Security

### Credential Management

- Never hardcode credentials
- Use environment variables
- Rotate tokens regularly
- Use least-privilege tokens

### HTTPS Enforcement

- Always use HTTPS for authenticated requests
- Verify SSL certificates
- Use modern TLS versions

### Data Protection

- Don't log sensitive data
- Sanitize error messages
- Use secure headers

## Troubleshooting

### Common Issues

#### "Connection refused"

- Server is not running
- Incorrect URL or port
- Firewall blocking connection

#### "SSL certificate verify failed"

- Invalid or expired certificate
- Self-signed certificate
- Certificate chain issue

#### "Request timeout"

- Server is slow
- Network latency
- Timeout too short

#### "401 Unauthorized"

- Invalid token
- Expired token
- Wrong authentication method

#### "429 Too Many Requests"

- Rate limit exceeded
- Too many concurrent requests
- Need to implement backoff

## Examples

See `examples.md` for detailed examples of:
- REST API integration
- OAuth 2.0 authentication
- Pagination handling
- Error recovery
- Rate limit handling

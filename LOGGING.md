# API Logging Documentation

## Overview

The API includes comprehensive logging of all requests, responses, and operations. **PII (Personally Identifiable Information) is intentionally logged** for debugging and audit purposes.

## Log Locations

### Console Output
All logs are printed to the console (stdout) where the server is running.

### Log File
All logs are also written to: `wedding_api.log`

**Note:** This file is excluded from git via `.gitignore`

## Log Format

```
YYYY-MM-DD HH:MM:SS - __main__ - LEVEL - MESSAGE
```

Example:
```
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] ========== NEW GUEST REQUEST ==========
```

## Request ID

Each request gets a unique ID in format: `YYYYMMDD-HHMMSS-microseconds`

Example: `[20241119-210000-123456]`

This allows you to trace all log entries for a specific request.

## What Gets Logged

### Startup
- Database configuration status
- Google Sheets configuration status
- Database initialization result
- Server port

### Every Guest Registration (POST /api/guests)
1. **Request Details:**
   - Request ID
   - HTTP method and path
   - Remote IP address
   - User Agent
   - Full request body (including PII)

2. **Processing:**
   - Guest name (original and normalized)
   - Attendance and companion details
   - Duplicate check result
   - Database insertion result with guest ID

3. **Google Sheets Sync:**
   - Sync attempt
   - Request parameters sent
   - Response status and body
   - Success/failure result

4. **Response:**
   - Complete response JSON
   - HTTP status code

### Guest List Retrieval (GET /api/guests)
- Request ID
- Remote IP address
- Number of guests returned
- Success/failure

### Errors
- Full exception details with stack traces
- Error context (what operation failed)

## Log Levels

### INFO
- Normal operations
- Successful requests
- Configuration status

### WARNING
- Validation failures
- Duplicate guest attempts
- Missing configuration

### ERROR
- Database errors
- Google Sheets sync failures
- Unexpected exceptions

### DEBUG
- Detailed operation steps
- SQL queries
- Internal state

## Example Log Output

### Successful Guest Registration

```
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] ========== NEW GUEST REQUEST ==========
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] Method: POST, Path: /api/guests
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] Remote Address: 127.0.0.1
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] User Agent: Mozilla/5.0...
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] Request Data: {"nombre":"Juan","apellidos":"García López","asistencia":"si","acompanado":"si","adultos":2,"ninos":1,"autobus":"ida_y_vuelta","alergias":"Ninguna","comentarios":"¡Muy emocionados!"}
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] Guest: Juan García López
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] Normalized: juan garcia lopez
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] Attendance: si, Companions: si
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] ✓ Guest saved to database - ID: 1
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] Attempting Google Sheets sync...
2024-11-19 21:00:00 - __main__ - INFO - Syncing to Google Sheets - Guest: Juan García López
2024-11-19 21:00:00 - __main__ - INFO - Google Sheets response - Status: 200, Body: {"success":true}
2024-11-19 21:00:00 - __main__ - INFO - ✓ Successfully synced to Google Sheets: Juan García López
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] ✓ SUCCESS - Response: {"success":true,"message":"¡Confirmación recibida con éxito!","guest":{"id":1,"nombre":"Juan","apellidos":"García López","created_at":"2024-11-19T21:00:00"},"synced_to_sheets":true}
2024-11-19 21:00:00 - __main__ - INFO - [20241119-210000-123456] ========================================
```

### Duplicate Detection

```
2024-11-19 21:01:00 - __main__ - INFO - [20241119-210100-789012] ========== NEW GUEST REQUEST ==========
2024-11-19 21:01:00 - __main__ - INFO - [20241119-210100-789012] Request Data: {"nombre":"JUAN","apellidos":"Garcia Lopez",...}
2024-11-19 21:01:00 - __main__ - INFO - [20241119-210100-789012] Guest: JUAN Garcia Lopez
2024-11-19 21:01:00 - __main__ - INFO - [20241119-210100-789012] Normalized: juan garcia lopez
2024-11-19 21:01:00 - __main__ - WARNING - [20241119-210100-789012] ✗ DUPLICATE DETECTED - Guest already exists: Juan García López (ID: 1)
```

### Google Sheets Sync Failure

```
2024-11-19 21:02:00 - __main__ - INFO - Syncing to Google Sheets - Guest: María López
2024-11-19 21:02:00 - __main__ - ERROR - ✗ Error syncing to Google Sheets - Status: 500, Response: Internal Server Error
```

## Viewing Logs

### Real-time (Console)
Logs appear in the terminal where you ran `./dev.sh`

### Log File
```bash
# View entire log
cat wedding_api.log

# Follow log in real-time
tail -f wedding_api.log

# Search for specific guest
grep "Juan García" wedding_api.log

# Search for errors
grep "ERROR" wedding_api.log

# Search by request ID
grep "20241119-210000-123456" wedding_api.log

# View last 50 lines
tail -n 50 wedding_api.log
```

## Log Rotation

For production, consider setting up log rotation to prevent the log file from growing too large.

### Using logrotate (Linux/Mac)

Create `/etc/logrotate.d/wedding-api`:

```
/path/to/wedding_web/backend/wedding_api.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 user group
}
```

## Privacy Considerations

⚠️ **Important:** Logs contain PII including:
- Full names
- Email addresses (if added)
- Comments and special requests
- IP addresses

**Recommendations:**
1. Restrict access to log files
2. Don't commit logs to git (already in .gitignore)
3. Implement log retention policy
4. Consider encrypting logs at rest in production
5. Comply with GDPR/privacy regulations

## Troubleshooting with Logs

### Guest says they registered but data is missing

1. Search for their name in logs:
   ```bash
   grep -i "juan garcia" wedding_api.log
   ```

2. Check if request was received
3. Check if database save succeeded
4. Check if Google Sheets sync succeeded

### Duplicate detection not working

1. Find the guest registration in logs
2. Check the "Normalized" line
3. Compare with existing guest's normalized name

### Google Sheets not syncing

1. Search for "Google Sheets" in logs
2. Check response status and error messages
3. Verify GOOGLE_APPS_SCRIPT_URL is set

## Log Analysis

### Count total requests
```bash
grep "NEW GUEST REQUEST" wedding_api.log | wc -l
```

### Count successful registrations
```bash
grep "✓ SUCCESS" wedding_api.log | wc -l
```

### Count duplicates
```bash
grep "DUPLICATE DETECTED" wedding_api.log | wc -l
```

### Count Google Sheets sync failures
```bash
grep "Error syncing to Google Sheets" wedding_api.log | wc -l
```

### List all registered guests
```bash
grep "✓ Guest saved to database" wedding_api.log | sed 's/.*Guest: //'
```

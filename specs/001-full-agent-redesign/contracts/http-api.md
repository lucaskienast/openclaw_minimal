# HTTP API Contract

**Date**: 2026-03-26
**Branch**: `001-full-agent-redesign`

## Base URL

`http://{host}:{port}/api/v1`

## Authentication

All endpoints require `X-User-Id` header (UUID string). The system trusts this header — external auth is out of scope.

---

## Endpoints

### Health

```
GET /health
```

**Response** `200`:
```json
{ "status": "ok" }
```

---

### Users

#### Create User

```
POST /users
```

**Request Body**:
```json
{ "user_id": "optional-uuid" }
```

**Response** `201`:
```json
{ "user_id": "uuid", "created_at": "2026-03-26T10:00:00Z" }
```

---

### Sessions

#### List Sessions

```
GET /users/{user_id}/sessions
Headers: X-User-Id: {user_id}
```

**Response** `200`:
```json
{
  "sessions": [
    { "session_id": "uuid", "title": "string", "created_at": "iso8601" }
  ]
}
```

#### Create Session

```
POST /users/{user_id}/sessions
Headers: X-User-Id: {user_id}
```

**Request Body**:
```json
{ "title": "optional-title" }
```

**Response** `201`:
```json
{ "session_id": "uuid", "title": "string", "created_at": "iso8601" }
```

#### Delete Session

```
DELETE /users/{user_id}/sessions/{session_id}
Headers: X-User-Id: {user_id}
```

**Response** `204`: No content. Cascade-deletes messages and session memories.

**Response** `403`: User does not own this session.

---

### Messages

#### Send Message

```
POST /users/{user_id}/sessions/{session_id}/messages
Headers: X-User-Id: {user_id}
```

**Request Body**:
```json
{ "content": "user message text" }
```

**Response** `200`:
```json
{
  "response": "agent response text",
  "session_id": "uuid",
  "correlation_id": "uuid",
  "tasks_completed": ["task description 1"],
  "tools_used": ["tool_name_1"]
}
```

**Response** `403`: User does not own this session.
**Response** `408`: Agent response exceeded 120-second timeout.

#### Get Session History

```
GET /users/{user_id}/sessions/{session_id}/messages
Headers: X-User-Id: {user_id}
Query: ?limit=50&offset=0
```

**Response** `200`:
```json
{
  "messages": [
    {
      "message_id": "uuid",
      "role": "user|assistant|tool",
      "content": "text",
      "created_at": "iso8601"
    }
  ],
  "total": 100
}
```

---

### User Memory

#### Get User Memories

```
GET /users/{user_id}/memories
Headers: X-User-Id: {user_id}
```

**Response** `200`:
```json
{
  "memories": [
    { "key": "name", "value": "Alice", "confidence": 0.95, "updated_at": "iso8601" }
  ]
}
```

#### Delete User Memory

```
DELETE /users/{user_id}/memories/{key}
Headers: X-User-Id: {user_id}
```

**Response** `204`: No content.

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

| Code              | HTTP Status | Description                        |
|-------------------|-------------|------------------------------------|
| NOT_FOUND         | 404         | Resource does not exist            |
| FORBIDDEN         | 403         | User does not own the resource     |
| VALIDATION_ERROR  | 422         | Invalid request body               |
| TIMEOUT           | 408         | Agent response exceeded 120s       |
| INTERNAL_ERROR    | 500         | Unexpected server error            |

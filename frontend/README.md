# RAG Frontend

Static frontend for a RAG-backed multilingual chat app with separate user and admin flows.

## Features

- Login screen with `User` and `Admin` role selection.
- User chat interface with chat history.
- Admin chat access.
- Admin knowledge upload by raw text or PDF.
- Demo mode when no backend URL is configured.
- Backend-ready API adapter in `api.js`.

## Run Locally

From this folder:

```bash
python3 -m http.server 5173
```

Then open:

```text
http://localhost:5173
```

## Connect Backend

Set the API base URL before `api.js` loads:

```html
<script>
  window.API_BASE_URL = "http://localhost:8000";
</script>
```

The expected endpoints and MongoDB shape are documented in `BACKEND_CONTRACT.md`.

## Auth Recommendation

Use email/password authentication with bcrypt password hashing, JWT access tokens, secure refresh tokens in `HttpOnly` cookies, and role-based authorization. This is the most direct fit for a custom user/admin product with MongoDB.

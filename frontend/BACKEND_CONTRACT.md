# RAG Frontend Backend Contract

## Recommended Stack

- Database: MongoDB with Mongoose.
- Authentication: email/password with `bcrypt` password hashing, short-lived JWT access tokens, and refresh tokens stored in secure `HttpOnly` cookies.
- Authorization: role-based access control with `role: "user" | "admin"` on the user document.
- File uploads: `multipart/form-data` through Multer or equivalent middleware.

This is simpler and more suitable than OAuth for a custom admin/user console. OAuth can be added later for Google login, but the first version should own user roles directly.

## MongoDB Collections

### users

```json
{
  "_id": "ObjectId",
  "email": "user@example.com",
  "passwordHash": "bcrypt hash",
  "role": "user",
  "createdAt": "Date",
  "updatedAt": "Date"
}
```

### chats

```json
{
  "_id": "ObjectId",
  "userId": "ObjectId",
  "title": "First query preview",
  "messages": [
    {
      "role": "user",
      "content": "Question text",
      "language": "en",
      "createdAt": "Date"
    },
    {
      "role": "assistant",
      "content": "RAG answer",
      "sources": [],
      "createdAt": "Date"
    }
  ],
  "createdAt": "Date",
  "updatedAt": "Date"
}
```

### knowledge_documents

```json
{
  "_id": "ObjectId",
  "uploadedBy": "ObjectId",
  "type": "text",
  "title": "Refund policy",
  "sourceFileName": null,
  "status": "indexed",
  "chunkCount": 8,
  "createdAt": "Date",
  "updatedAt": "Date"
}
```

Store vector embeddings either in MongoDB Atlas Vector Search or your existing vector store. Keep metadata in MongoDB so the admin dashboard can show upload status later.

## Endpoints

### `POST /auth/login`

Request:

```json
{
  "email": "user@example.com",
  "password": "password123",
  "role": "user"
}
```

Response:

```json
{
  "user": {
    "id": "user id",
    "email": "user@example.com",
    "role": "user"
  }
}
```

Set refresh token as a secure `HttpOnly` cookie. Return access token either as JSON or as another secure cookie. The frontend is already using `credentials: "include"`.

### `GET /chats`

Returns the logged-in user's chat history.

### `POST /chat`

Request:

```json
{
  "chatId": "optional existing chat id",
  "query": "User question in any language"
}
```

Response:

```json
{
  "chat": {
    "id": "chat id",
    "title": "Chat title",
    "updatedAt": "Date",
    "messages": []
  },
  "answer": "Assistant answer"
}
```

The backend should detect the query language, retrieve relevant chunks, ask the model to answer in that same language, then save both user and assistant messages.

### `POST /knowledge/text`

Admin only.

Request:

```json
{
  "title": "Document title",
  "text": "Raw knowledge text"
}
```

Response:

```json
{
  "status": "indexed",
  "chunks": 12
}
```

### `POST /knowledge/pdf`

Admin only. Accepts `multipart/form-data` with a field named `file`.

Response:

```json
{
  "status": "queued",
  "fileName": "document.pdf"
}
```

Recommended processing: upload PDF, extract text, chunk text, create embeddings, save chunks/vector metadata, then update `knowledge_documents.status`.

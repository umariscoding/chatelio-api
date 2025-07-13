# Multi-Tenant Chatbot API Documentation

## Overview
This API provides authentication, user management, and multi-tenant chat functionality for a chatbot platform. Companies can register, manage users, and provide AI-powered chatbot services to both registered users and guest sessions with company-specific knowledge bases.

## Base URL
```
http://localhost:8000
```

## Authentication
The API uses JWT (JSON Web Tokens) for authentication with two types of tokens:
- **Access Token**: Short-lived (30 minutes) for API access
- **Refresh Token**: Long-lived (7 days) for obtaining new access tokens

### Token Types
- `company`: Company authentication tokens
- `user`: Registered user tokens  
- `guest`: Guest session tokens

---

## Company Authentication Endpoints

### 1. Register Company
**POST** `/auth/company/register`

Register a new company account.

#### Request Body
```json
{
  "name": "string",        // Company name (required)
  "email": "string",       // Company email (required, must be unique)
  "password": "string"     // Company password (required)
}
```

#### Response (201 Created)
```json
{
  "message": "Company registered successfully",
  "company": {
    "company_id": "uuid",
    "name": "string",
    "email": "string",
    "plan": "free",
    "status": "active"
  },
  "tokens": {
    "access_token": "jwt_token_string",
    "refresh_token": "jwt_token_string",
    "token_type": "bearer"
  }
}
```

#### Error Responses
```json
// 400 Bad Request - Company already exists
{
  "detail": "Company with this email already exists"
}

// 422 Unprocessable Entity - Validation error
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

### 2. Company Login
**POST** `/auth/company/login`

Authenticate a company and receive tokens.

#### Request Body
```json
{
  "email": "string",       // Company email (required)
  "password": "string"     // Company password (required)
}
```

#### Response (200 OK)
```json
{
  "message": "Login successful",
  "company": {
    "company_id": "uuid",
    "name": "string",
    "email": "string",
    "plan": "free",
    "status": "active"
  },
  "tokens": {
    "access_token": "jwt_token_string",
    "refresh_token": "jwt_token_string",
    "token_type": "bearer"
  }
}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid credentials
{
  "detail": "Invalid email or password"
}
```

---

### 3. Get Company Profile
**GET** `/auth/company/profile`

Get current company profile information.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "company": {
    "company_id": "uuid",
    "name": "string",
    "email": "string",
    "plan": "free",
    "status": "active"
  }
}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid or expired token
{
  "detail": "Could not validate credentials"
}
```

---

### 4. Refresh Token
**POST** `/auth/refresh`

Get new access token using refresh token.

#### Request Body
```json
{
  "refresh_token": "jwt_refresh_token_string"
}
```

#### Response (200 OK)
```json
{
  "access_token": "new_jwt_token_string",
  "refresh_token": "new_refresh_token_string",
  "token_type": "bearer"
}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid refresh token
{
  "detail": "Invalid refresh token"
}
```

---

### 5. Verify Token
**GET** `/auth/verify`

Verify if current token is valid.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "valid": true,
  "user_type": "company",
  "company_id": "uuid",
  "email": "string"
}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid token
{
  "detail": "Invalid token"
}
```

---

### 6. Company Logout
**POST** `/auth/company/logout`

Logout current company session.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "message": "Logout successful"
}
```

---

### 7. Authentication Health Check
**GET** `/auth/health`

Check authentication service health.

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "authentication"
}
```

---

## User Management Endpoints

### 1. Create Guest Session
**POST** `/users/guest/create`

Create a new guest session for a company.

#### Request Body
```json
{
  "company_id": "uuid",           // Company ID (required)
  "ip_address": "string",         // User IP address (optional)
  "user_agent": "string"          // User agent string (optional)
}
```

#### Response (201 Created)
```json
{
  "message": "Guest session created successfully",
  "session": {
    "session_id": "uuid",
    "company_id": "uuid",
    "ip_address": "string",
    "user_agent": "string",
    "created_at": "2024-01-01T00:00:00.000000"
  },
  "tokens": {
    "access_token": "jwt_token_string",
    "refresh_token": "jwt_token_string",
    "token_type": "bearer"
  }
}
```

#### Error Responses
```json
// 404 Not Found - Company not found
{
  "detail": "Company not found"
}

// 500 Internal Server Error - Creation failed
{
  "detail": "Failed to create guest session: <error_message>"
}
```

---

### 2. Register User
**POST** `/users/register`

Register a new user directly for a company.

#### Request Body
```json
{
  "company_id": "uuid",           // Company ID (required)
  "email": "string",              // User email (required)
  "name": "string"                // User name (required)
}
```

#### Response (201 Created)
```json
{
  "message": "User registered successfully",
  "user": {
    "user_id": "uuid",
    "company_id": "uuid",
    "email": "string",
    "name": "string",
    "created_at": "2024-01-01T00:00:00.000000"
  },
  "tokens": {
    "access_token": "jwt_token_string",
    "refresh_token": "jwt_token_string",
    "token_type": "bearer"
  }
}
```

#### Error Responses
```json
// 400 Bad Request - User already exists
{
  "detail": "User with this email already exists"
}

// 404 Not Found - Company not found
{
  "detail": "Company not found"
}
```

---

### 3. Convert Guest to User
**POST** `/users/convert-guest-to-user`

Convert a guest session to a registered user (progressive enhancement).

#### Headers
```
Authorization: Bearer <guest_access_token>
```

#### Request Body
```json
{
  "email": "string",              // User email (required)
  "name": "string"                // User name (required)
}
```

#### Response (200 OK)
```json
{
  "message": "Guest converted to user successfully",
  "user": {
    "user_id": "uuid",
    "company_id": "uuid",
    "email": "string",
    "name": "string",
    "created_at": "2024-01-01T00:00:00.000000"
  },
  "tokens": {
    "access_token": "jwt_token_string",
    "refresh_token": "jwt_token_string",
    "token_type": "bearer"
  },
  "conversion_bonus": "Your chat history has been preserved!"
}
```

#### Error Responses
```json
// 400 Bad Request - User already exists
{
  "detail": "User with this email already exists"
}

// 401 Unauthorized - Invalid guest token
{
  "detail": "Invalid guest session"
}

// 404 Not Found - Guest session not found
{
  "detail": "Guest session not found or expired"
}
```

---

### 4. Get User Profile
**GET** `/users/profile`

Get current user profile (works for both registered users and guests).

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
// For registered users
{
  "user": {
    "user_id": "uuid",
    "company_id": "uuid",
    "email": "string",
    "name": "string",
    "created_at": "2024-01-01T00:00:00.000000"
  },
  "user_type": "user"
}

// For guest sessions
{
  "session": {
    "session_id": "uuid",
    "company_id": "uuid",
    "ip_address": "string",
    "user_agent": "string",
    "created_at": "2024-01-01T00:00:00.000000",
    "converted": false
  },
  "user_type": "guest"
}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid token
{
  "detail": "Could not validate credentials"
}

// 404 Not Found - User/session not found
{
  "detail": "User not found"
}
```

---

### 5. Check Session Validity
**GET** `/users/session/check`

Check if current session is valid.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "valid": true,
  "user_type": "user",           // or "guest"
  "company_id": "uuid",
  "expires_at": "2024-01-01T00:30:00.000000"
}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid or expired session
{
  "detail": "Session expired or invalid"
}
```

---

### 6. Get Company Info
**GET** `/users/company/{company_id}/info`

Get public company information (no authentication required).

#### Parameters
- `company_id` (path): Company UUID

#### Response (200 OK)
```json
{
  "company": {
    "company_id": "uuid",
    "name": "string",
    "status": "active"
  }
}
```

#### Error Responses
```json
// 404 Not Found - Company not found
{
  "detail": "Company not found"
}
```

---

### 7. User Management Health Check
**GET** `/users/health`

Check user management service health.

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "user_management"
}
```

---

## Multi-Tenant Chat Endpoints

### 1. Send Message
**POST** `/chat/send`

Send a message to the AI chatbot and receive a streaming response. Works for both registered users and guest sessions with company-specific knowledge bases.

#### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Request Body
```json
{
  "message": "string",           // User message (required)
  "chat_id": "string",           // Chat UUID (optional, auto-generated if not provided)
  "chat_title": "string",        // Chat title (optional, defaults to "New Chat")
  "model": "string"              // AI model to use (optional, defaults to "Gemini")
}
```

#### Response (200 OK)
**Server-Sent Events (SSE) Stream**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Chat-ID: <chat_id>

data: {"chat_id": "uuid", "type": "start"}

data: {"content": "Hello! How can I help you today?", "type": "chunk"}

data: {"content": " I'm here to assist with any questions.", "type": "chunk"}

data: {"type": "end"}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid token
{
  "detail": "Could not validate credentials"
}

// 500 Internal Server Error - Processing failed
{
  "detail": "Failed to send message: <error_message>"
}
```

---

### 2. Get Chat History
**GET** `/chat/history/{chat_id}`

Retrieve the complete message history for a specific chat. Only accessible by the chat owner.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Parameters
- `chat_id` (path): Chat UUID

#### Response (200 OK)
```json
{
  "messages": [
    {
      "message_id": "uuid",
      "chat_id": "uuid",
      "role": "human",
      "content": "Hello, how are you?",
      "timestamp": "2024-01-01T00:00:00.000000"
    },
    {
      "message_id": "uuid",
      "chat_id": "uuid",
      "role": "ai",
      "content": "Hello! I'm doing well, thank you for asking. How can I help you today?",
      "timestamp": "2024-01-01T00:00:05.000000"
    }
  ]
}
```

#### Error Responses
```json
// 404 Not Found - Chat not found or access denied
{
  "detail": "Chat not found or access denied"
}

// 500 Internal Server Error - Fetch failed
{
  "detail": "Failed to fetch chat history: <error_message>"
}
```

---

### 3. List Chats
**GET** `/chat/list`

Get a list of all chats for the current user or guest session. Only shows chats belonging to the same company.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "chats": [
    {
      "chat_id": "uuid",
      "company_id": "uuid",
      "title": "My First Chat",
      "user_id": "uuid",
      "session_id": null,
      "created_at": "2024-01-01T00:00:00.000000",
      "updated_at": "2024-01-01T00:05:00.000000"
    },
    {
      "chat_id": "uuid",
      "company_id": "uuid",
      "title": "Technical Support",
      "user_id": "uuid",
      "session_id": null,
      "created_at": "2024-01-01T01:00:00.000000",
      "updated_at": "2024-01-01T01:10:00.000000"
    }
  ]
}
```

#### Error Responses
```json
// 401 Unauthorized - Invalid token
{
  "detail": "Could not validate credentials"
}

// 500 Internal Server Error - Fetch failed
{
  "detail": "Failed to fetch chats: <error_message>"
}
```

---

### 4. Update Chat Title
**PUT** `/chat/title/{chat_id}`

Update the title of a specific chat. Only accessible by the chat owner.

#### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Parameters
- `chat_id` (path): Chat UUID

#### Request Body
```json
{
  "title": "string"             // New chat title (required)
}
```

#### Response (200 OK)
```json
{
  "message": "Chat title updated successfully"
}
```

#### Error Responses
```json
// 404 Not Found - Chat not found or access denied
{
  "detail": "Chat not found or access denied"
}

// 500 Internal Server Error - Update failed
{
  "detail": "Failed to update chat title: <error_message>"
}
```

---

### 5. Delete Chat
**DELETE** `/chat/{chat_id}`

Delete a specific chat and all its messages. Only accessible by the chat owner.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Parameters
- `chat_id` (path): Chat UUID

#### Response (200 OK)
```json
{
  "message": "Chat deleted successfully"
}
```

#### Error Responses
```json
// 404 Not Found - Chat not found or access denied
{
  "detail": "Chat not found or access denied"
}

// 500 Internal Server Error - Delete failed
{
  "detail": "Failed to delete chat: <error_message>"
}
```

---

### 6. Setup Knowledge Base
**POST** `/chat/setup-knowledge-base`

Set up the AI knowledge base for a company. Only accessible by company users (not guests).

#### Headers
```
Authorization: Bearer <company_access_token>
```

#### Response (200 OK)
```json
{
  "message": "Knowledge base set up successfully"
}
```

#### Error Responses
```json
// 403 Forbidden - Only company users can set up knowledge base
{
  "detail": "Only company users can set up knowledge base"
}

// 500 Internal Server Error - Setup failed
{
  "detail": "Failed to set up knowledge base: <error_message>"
}
```

---

### 7. Get Company Info
**GET** `/chat/company-info`

Get information about the current company context for the chat session.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "company": {
    "company_id": "uuid",
    "name": "string",
    "plan": "free",
    "status": "active"
  }
}
```

#### Error Responses
```json
// 404 Not Found - Company not found
{
  "detail": "Company not found"
}

// 500 Internal Server Error - Fetch failed
{
  "detail": "Failed to fetch company info: <error_message>"
}
```

---

### 8. Chat Service Health Check
**GET** `/chat/health`

Check the health status of the chat service.

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "chat"
}
```

---

## Document Upload & Knowledge Base Management

### 1. Upload Document File
**POST** `/chat/upload-document`

Upload a text document to the company's knowledge base. Only accessible by company users.

#### Headers
```
Authorization: Bearer <company_access_token>
Content-Type: multipart/form-data
```

#### Request Body (Form Data)
```
file: <text_file>             // Text file to upload (max 10MB)
```

#### Response (200 OK)
```json
{
  "message": "Document uploaded and processed successfully",
  "document": {
    "doc_id": "uuid",
    "kb_id": "uuid",
    "filename": "document.txt",
    "content_type": "text/plain",
    "file_size": 1024,
    "embeddings_status": "completed",
    "created_at": "2024-01-01T00:00:00.000000"
  },
  "knowledge_base": {
    "kb_id": "uuid",
    "company_id": "uuid",
    "name": "Default Knowledge Base",
    "description": "Company knowledge base",
    "status": "ready",
    "file_count": 1,
    "created_at": "2024-01-01T00:00:00.000000",
    "updated_at": "2024-01-01T00:00:00.000000"
  }
}
```

#### Error Responses
```json
// 400 Bad Request - Invalid file type
{
  "detail": "Only text files are supported"
}

// 400 Bad Request - File too large
{
  "detail": "File size too large. Maximum 10MB allowed."
}

// 400 Bad Request - Invalid encoding
{
  "detail": "File must be valid UTF-8 text"
}

// 403 Forbidden - Not a company user
{
  "detail": "Only company users can upload documents"
}

// 500 Internal Server Error - Processing failed
{
  "detail": "Failed to process document"
}
```

---

### 2. Upload Text Content
**POST** `/chat/upload-text`

Upload text content directly to the company's knowledge base. Only accessible by company users.

#### Headers
```
Authorization: Bearer <company_access_token>
Content-Type: application/json
```

#### Request Body
```json
{
  "content": "string",          // Text content to upload (required)
  "filename": "string"          // Filename for the document (optional, defaults to "document.txt")
}
```

#### Response (200 OK)
```json
{
  "message": "Text content uploaded and processed successfully",
  "document": {
    "doc_id": "uuid",
    "kb_id": "uuid",
    "filename": "document.txt",
    "content_type": "text/plain",
    "file_size": 1024,
    "embeddings_status": "completed",
    "created_at": "2024-01-01T00:00:00.000000"
  },
  "knowledge_base": {
    "kb_id": "uuid",
    "company_id": "uuid",
    "name": "Default Knowledge Base",
    "description": "Company knowledge base",
    "status": "ready",
    "file_count": 1,
    "created_at": "2024-01-01T00:00:00.000000",
    "updated_at": "2024-01-01T00:00:00.000000"
  }
}
```

#### Error Responses
```json
// 400 Bad Request - Content too large
{
  "detail": "Content size too large. Maximum 10MB allowed."
}

// 403 Forbidden - Not a company user
{
  "detail": "Only company users can upload documents"
}

// 500 Internal Server Error - Processing failed
{
  "detail": "Failed to process document"
}
```

---

### 3. List Documents
**GET** `/chat/documents`

List all documents in the company's knowledge base. Only accessible by company users.

#### Headers
```
Authorization: Bearer <company_access_token>
```

#### Response (200 OK)
```json
{
  "documents": [
    {
      "doc_id": "uuid",
      "kb_id": "uuid",
      "filename": "document1.txt",
      "content_type": "text/plain",
      "file_size": 1024,
      "embeddings_status": "completed",
      "created_at": "2024-01-01T00:00:00.000000"
    },
    {
      "doc_id": "uuid",
      "kb_id": "uuid",
      "filename": "document2.txt",
      "content_type": "text/plain",
      "file_size": 2048,
      "embeddings_status": "completed",
      "created_at": "2024-01-01T01:00:00.000000"
    }
  ]
}
```

#### Error Responses
```json
// 403 Forbidden - Not a company user
{
  "detail": "Only company users can access documents"
}

// 500 Internal Server Error - Fetch failed
{
  "detail": "Failed to fetch documents: <error_message>"
}
```

---

### 4. Get Knowledge Base Info
**GET** `/chat/knowledge-base`

Get information about the company's knowledge base. Only accessible by company users.

#### Headers
```
Authorization: Bearer <company_access_token>
```

#### Response (200 OK)
```json
{
  "kb_id": "uuid",
  "name": "Default Knowledge Base",
  "description": "Company knowledge base",
  "status": "ready",
  "file_count": 5,
  "created_at": "2024-01-01T00:00:00.000000",
  "updated_at": "2024-01-01T00:00:00.000000"
}
```

#### Error Responses
```json
// 403 Forbidden - Not a company user
{
  "detail": "Only company users can access knowledge base info"
}

// 500 Internal Server Error - Fetch failed
{
  "detail": "Failed to fetch knowledge base info: <error_message>"
}
```

---

### 5. Delete Document
**DELETE** `/chat/documents/{doc_id}`

Delete a document from the company's knowledge base. Only accessible by company users.

#### Headers
```
Authorization: Bearer <company_access_token>
```

#### Parameters
- `doc_id` (path): Document UUID

#### Response (200 OK)
```json
{
  "message": "Document deleted successfully"
}
```

#### Error Responses
```json
// 404 Not Found - Document not found
{
  "detail": "Document not found"
}

// 403 Forbidden - Not a company user
{
  "detail": "Only company users can delete documents"
}

// 500 Internal Server Error - Delete failed
{
  "detail": "Failed to delete document: <error_message>"
}
```

---

### 6. Clear Knowledge Base
**POST** `/chat/clear-knowledge-base`

Clear all content from the company's knowledge base. Only accessible by company users.

#### Headers
```
Authorization: Bearer <company_access_token>
```

#### Response (200 OK)
```json
{
  "message": "Knowledge base cleared successfully"
}
```

#### Error Responses
```json
// 403 Forbidden - Not a company user
{
  "detail": "Only company users can clear knowledge base"
}

// 500 Internal Server Error - Clear failed
{
  "detail": "Failed to clear knowledge base: <error_message>"
}
```

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Operation failed: <error_message>"
}
```

---

## Authentication Flow Examples

### Company Registration & Login Flow
```javascript
// 1. Register company
const registerResponse = await fetch('/auth/company/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Acme Corp',
    email: 'admin@acme.com',
    password: 'securepassword123'
  })
});

// 2. Store tokens
const { tokens } = await registerResponse.json();
localStorage.setItem('access_token', tokens.access_token);
localStorage.setItem('refresh_token', tokens.refresh_token);

// 3. Use token for authenticated requests
const profileResponse = await fetch('/auth/company/profile', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`
  }
});
```

### Guest Session Flow
```javascript
// 1. Create guest session
const guestResponse = await fetch('/users/guest/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    company_id: 'company-uuid',
    ip_address: '192.168.1.1',
    user_agent: navigator.userAgent
  })
});

// 2. Store guest tokens
const { tokens } = await guestResponse.json();
localStorage.setItem('guest_access_token', tokens.access_token);

// 3. Later, convert to registered user
const convertResponse = await fetch('/users/convert-guest-to-user', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'user@example.com',
    name: 'John Doe'
  })
});
```

### Token Refresh Flow
```javascript
// Check if token is about to expire and refresh
const refreshToken = localStorage.getItem('refresh_token');
const refreshResponse = await fetch('/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: refreshToken
  })
});

if (refreshResponse.ok) {
  const { access_token, refresh_token } = await refreshResponse.json();
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('refresh_token', refresh_token);
}
```

---

## Chat Flow Examples

### Basic Chat Flow
```javascript
// 1. Send a message
const response = await fetch('/chat/send', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Hello, how can you help me?',
    chat_title: 'Customer Support'
  })
});

// 2. Handle streaming response
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      
      if (data.type === 'start') {
        console.log('Chat ID:', data.chat_id);
      } else if (data.type === 'chunk') {
        console.log('AI Response:', data.content);
      } else if (data.type === 'end') {
        console.log('Response complete');
      }
    }
  }
}
```

### Chat Management Flow
```javascript
// 1. List all chats
const chatsResponse = await fetch('/chat/list', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
const { chats } = await chatsResponse.json();

// 2. Get chat history
const historyResponse = await fetch(`/chat/history/${chatId}`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
const { messages } = await historyResponse.json();

// 3. Update chat title
await fetch(`/chat/title/${chatId}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'Updated Chat Title'
  })
});

// 4. Delete chat
await fetch(`/chat/${chatId}`, {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
```

### Company Knowledge Base Setup
```javascript
// Company admin sets up knowledge base
const setupResponse = await fetch('/chat/setup-knowledge-base', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${companyAccessToken}`
  }
});

if (setupResponse.ok) {
  console.log('Knowledge base set up successfully');
}
```

### Document Upload and Management
```javascript
// 1. Upload a document file
const uploadDocumentFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('/chat/upload-document', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${companyAccessToken}`
    },
    body: formData
  });
  
  if (response.ok) {
    const result = await response.json();
    console.log('Document uploaded:', result.document);
    return result;
  }
};

// 2. Upload text content directly
const uploadTextContent = async (content, filename = 'document.txt') => {
  const response = await fetch('/chat/upload-text', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${companyAccessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      content: content,
      filename: filename
    })
  });
  
  if (response.ok) {
    const result = await response.json();
    console.log('Text content uploaded:', result.document);
    return result;
  }
};

// 3. List all documents
const listDocuments = async () => {
  const response = await fetch('/chat/documents', {
    headers: {
      'Authorization': `Bearer ${companyAccessToken}`
    }
  });
  
  if (response.ok) {
    const result = await response.json();
    console.log('Company documents:', result.documents);
    return result.documents;
  }
};

// 4. Get knowledge base information
const getKnowledgeBase = async () => {
  const response = await fetch('/chat/knowledge-base', {
    headers: {
      'Authorization': `Bearer ${companyAccessToken}`
    }
  });
  
  if (response.ok) {
    const kb = await response.json();
    console.log('Knowledge base info:', kb);
    return kb;
  }
};

// 5. Delete a document
const deleteDocument = async (docId) => {
  const response = await fetch(`/chat/documents/${docId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${companyAccessToken}`
    }
  });
  
  if (response.ok) {
    console.log('Document deleted successfully');
    return true;
  }
  return false;
};

// 6. Clear knowledge base
const clearKnowledgeBase = async () => {
  const response = await fetch('/chat/clear-knowledge-base', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${companyAccessToken}`
    }
  });
  
  if (response.ok) {
    console.log('Knowledge base cleared successfully');
    return true;
  }
  return false;
};

// Complete document management workflow
const documentManagementWorkflow = async () => {
  // Upload multiple documents
  const documents = [
    { content: 'Product documentation...', filename: 'product-guide.txt' },
    { content: 'FAQ content...', filename: 'faq.txt' },
    { content: 'Support procedures...', filename: 'support.txt' }
  ];
  
  for (const doc of documents) {
    await uploadTextContent(doc.content, doc.filename);
  }
  
  // Check knowledge base status
  const kb = await getKnowledgeBase();
  console.log(`Knowledge base has ${kb.file_count} documents`);
  
  // List all documents
  const allDocs = await listDocuments();
  console.log('All documents:', allDocs);
};
```

---

## Multi-Tenant Architecture

### Company Isolation
- Each company has its own isolated vector store/knowledge base
- Users and guests can only access chats within their company
- AI responses are generated using company-specific knowledge

### User Types & Access Control
- **Company Users**: Can set up knowledge base, manage company settings
- **Registered Users**: Can create and manage their own chats within the company
- **Guest Sessions**: Can chat but with limited access, can be converted to registered users

### Chat Ownership
- Registered users can only see their own chats
- Guest sessions can only see chats from their session
- Company admins cannot see individual user chats (privacy protection)

---

## Notes for Frontend Development

1. **Streaming Responses**: The `/chat/send` endpoint returns Server-Sent Events (SSE) for real-time chat experience
2. **Chat Management**: Implement proper chat list management with real-time updates
3. **Company Context**: All chat operations are scoped to the user's company
4. **Progressive Enhancement**: Encourage guest users to register after a few interactions
5. **Error Handling**: Implement proper error handling for all chat operations
6. **Knowledge Base**: Companies need to set up their knowledge base before users can chat
7. **Auto-save**: Chat history is automatically saved during streaming responses
8. **Document Upload**: Support both file upload and direct text content upload for knowledge base management
9. **File Validation**: Validate file types (text only) and sizes (max 10MB) on the frontend
10. **Document Management**: Provide UI for companies to view, manage, and delete their uploaded documents
11. **Knowledge Base Status**: Show knowledge base information and document count to companies
12. **Company-Only Access**: Document upload and management features are only available to company users, not regular users or guests
13. **Automatic Processing**: Documents are automatically processed and added to the vector store upon upload
14. **Real-time Updates**: Consider implementing real-time updates for document processing status

## Document Management Best Practices

1. **File Upload UI**: 
   - Use drag-and-drop interface for better UX
   - Show progress indicators during upload
   - Display file size and type validation messages

2. **Document List Management**:
   - Show document status (processing, completed, failed)
   - Allow sorting by date, name, or size
   - Implement search/filter functionality

3. **Knowledge Base Overview**:
   - Display total document count and storage used
   - Show knowledge base status and health
   - Provide clear actions for management

4. **Error Handling**:
   - Handle file upload errors gracefully
   - Show meaningful error messages for validation failures
   - Implement retry mechanisms for failed uploads

5. **User Experience**:
   - Show immediate feedback after document upload
   - Provide document preview capabilities
   - Allow bulk operations (multiple uploads, batch delete)

---

## Rate Limiting & Security

- All chat endpoints are protected by JWT authentication
- Company-specific vector stores ensure data isolation
- Chat access control prevents unauthorized access to other users' chats
- Streaming responses are properly terminated to prevent resource leaks
- Input validation on all chat messages and operations

---

This documentation covers the complete multi-tenant chatbot API including authentication, user management, and chat functionality. The system supports both registered users and guest sessions with company-specific AI knowledge bases and proper access control. 
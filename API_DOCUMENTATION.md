# Chatelio Multi-Tenant API Documentation

## Overview
This API provides a comprehensive multi-tenant chatbot platform with company-based data isolation, user management, and AI-powered chat functionality. Each company has its own knowledge base, users, and data that are completely isolated from other companies.

## Base URL
```
http://127.0.0.1:8000
```

## Authentication
The API uses JWT Bearer tokens for authentication. Include the token in the Authorization header:
```
Authorization: Bearer <token>
```

### Token Types
- **Company Tokens**: For company administrators (access all company endpoints)
- **User Tokens**: For registered users (access user-specific endpoints)
- **Guest Tokens**: For temporary sessions (limited access)

---

## 🏢 Authentication Endpoints

### 1. Company Registration
**POST** `/auth/company/register`

Register a new company and create admin account.

**Request Body:**
```json
{
  "name": "TechCorp Solutions Inc",
  "email": "admin@techcorp-solutions.com",
  "password": "TechCorpPass123!"
}
```

**Response (200):**
```json
{
  "company": {
    "company_id": "company_uuid",
    "name": "TechCorp Solutions Inc",
    "email": "admin@techcorp-solutions.com",
    "created_at": "2024-01-01T12:00:00Z",
    "slug": null,
    "is_published": false
  },
  "tokens": {
    "access_token": "jwt_access_token",
    "refresh_token": "jwt_refresh_token",
    "token_type": "bearer"
  }
}
```

**Error (400):**
```json
{
  "detail": "Email already registered"
}
```

---

### 2. Company Login
**POST** `/auth/company/login`

Authenticate company admin and get tokens.

**Request Body:**
```json
{
  "email": "admin@techcorp-solutions.com",
  "password": "TechCorpPass123!"
}
```

**Response (200):**
```json
{
  "company": {
    "company_id": "company_uuid",
    "name": "TechCorp Solutions Inc",
    "email": "admin@techcorp-solutions.com",
    "created_at": "2024-01-01T12:00:00Z",
    "slug": "techcorp-solutions",
    "is_published": true
  },
  "tokens": {
    "access_token": "jwt_access_token",
    "refresh_token": "jwt_refresh_token",
    "token_type": "bearer"
  }
}
```

**Error (401):**
```json
{
  "detail": "Invalid credentials"
}
```

---

### 3. Company Logout
**POST** `/auth/company/logout`

**Headers:** `Authorization: Bearer <company_token>`

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

---

### 4. Set Company Slug
**PUT** `/auth/company/slug`

Set or update company slug for public chatbot URL.

**Headers:** `Authorization: Bearer <company_token>`

**Request Body:**
```json
{
  "slug": "techcorp-solutions"
}
```

**Response (200):**
```json
{
  "message": "Slug updated successfully",
  "slug": "techcorp-solutions",
  "chatbot_url": "http://127.0.0.1:8000/public/chatbot/techcorp-solutions"
}
```

**Error (400):**
```json
{
  "detail": "Slug already taken"
}
```

---

### 5. Publish/Unpublish Chatbot
**POST** `/auth/company/publish-chatbot`

Control public chatbot visibility.

**Headers:** `Authorization: Bearer <company_token>`

**Request Body:**
```json
{
  "is_published": true,
  "chatbot_title": "TechCorp AI Assistant",
  "chatbot_description": "AI technology expert assistant"
}
```

**Response (200):**
```json
{
  "message": "Chatbot published successfully",
  "chatbot_url": "http://127.0.0.1:8000/public/chatbot/techcorp-solutions",
  "is_published": true
}
```

---

### 6. Refresh Token
**POST** `/auth/refresh`

Get new access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "jwt_refresh_token"
}
```

**Response (200):**
```json
{
  "access_token": "new_jwt_access_token",
  "token_type": "bearer"
}
```

---

### 7. Authentication Health Check
**GET** `/auth/health`

**Response (200):**
```json
{
  "status": "healthy",
  "service": "authentication"
}
```

---

## 👥 User Management Endpoints

### 1. User Registration
**POST** `/users/register`

Register a new user for a company.

**Request Body:**
```json
{
  "company_id": "company_uuid",
  "email": "alice@techcorp-solutions.com",
  "password": "AlicePass123!",
  "name": "Alice Johnson"
}
```

**Response (200):**
```json
{
  "user": {
    "user_id": "user_uuid",
    "company_id": "company_uuid",
    "email": "alice@techcorp-solutions.com",
    "name": "Alice Johnson",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "tokens": {
    "access_token": "jwt_access_token",
    "refresh_token": "jwt_refresh_token",
    "token_type": "bearer"
  }
}
```

**Error (400):**
```json
{
  "detail": "Email already registered"
}
```

---

### 2. User Login
**POST** `/users/login`

Authenticate user and get tokens.

**Request Body:**
```json
{
  "email": "alice@techcorp-solutions.com",
  "password": "AlicePass123!"
}
```

**Response (200):**
```json
{
  "user": {
    "user_id": "user_uuid",
    "company_id": "company_uuid",
    "email": "alice@techcorp-solutions.com",
    "name": "Alice Johnson",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "tokens": {
    "access_token": "jwt_access_token",
    "refresh_token": "jwt_refresh_token",
    "token_type": "bearer"
  }
}
```

---

### 3. Create Guest Session
**POST** `/users/guest/create`

Create temporary session for anonymous users.

**Request Body:**
```json
{
  "company_id": "company_uuid",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Test Guest)"
}
```

**Response (200):**
```json
{
  "guest": {
    "session_id": "session_uuid",
    "company_id": "company_uuid",
    "created_at": "2024-01-01T12:00:00Z",
    "expires_at": "2024-01-01T20:00:00Z"
  },
  "tokens": {
    "access_token": "jwt_access_token",
    "token_type": "bearer"
  }
}
```

---

### 4. Get Company Info
**GET** `/users/company/{company_id}/info`

Get company information (users can only access their own company).

**Headers:** `Authorization: Bearer <user_token>`

**Response (200):**
```json
{
  "company_id": "company_uuid",
  "name": "TechCorp Solutions Inc",
  "slug": "techcorp-solutions",
  "chatbot_title": "TechCorp AI Assistant",
  "chatbot_description": "AI technology expert assistant",
  "is_published": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Error (403):**
```json
{
  "detail": "Access denied: Cannot access other company's information"
}
```

---

### 5. Validate Session
**GET** `/users/validate-session`

Check if current session is valid.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "valid": true,
  "user_info": {
    "user_id": "user_uuid",
    "company_id": "company_uuid",
    "email": "alice@techcorp-solutions.com",
    "user_type": "user"
  }
}
```

---

### 6. User Management Health Check
**GET** `/users/health`

**Response (200):**
```json
{
  "status": "healthy",
  "service": "user_management"
}
```

---

## 💬 Chat Endpoints

### 1. Setup Knowledge Base
**POST** `/chat/setup-knowledge-base`

Initialize AI knowledge base for company.

**Headers:** `Authorization: Bearer <company_token>`

**Response (200):**
```json
{
  "message": "Knowledge base setup completed",
  "index_name": "company-uuid-index",
  "status": "ready"
}
```

---

### 2. Upload Text Document
**POST** `/chat/upload-text`

Upload text content to knowledge base.

**Headers:** `Authorization: Bearer <company_token>`

**Request Body:**
```json
{
  "content": "TechCorp Solutions Inc is a leading AI technology company...",
  "filename": "techcorp-company-info.txt"
}
```

**Response (200):**
```json
{
  "message": "Document uploaded successfully",
  "document": {
    "doc_id": "doc_uuid",
    "filename": "techcorp-company-info.txt",
    "content_length": 500,
    "uploaded_at": "2024-01-01T12:00:00Z"
  }
}
```

---

### 3. Send Chat Message
**POST** `/chat/send`

Send message to AI chatbot and get streaming response.

**Headers:** `Authorization: Bearer <user_token>` or `Bearer <guest_token>`

**Request Body:**
```json
{
  "message": "What is your company's annual revenue?",
  "chat_id": "chat_uuid",
  "chat_title": "Revenue Discussion",
  "model": "OpenAI"
}
```

**Response (200):** Streaming response with Server-Sent Events
```
Content-Type: text/plain
X-Chat-ID: chat_uuid

TechCorp Solutions Inc has an annual revenue of $10 million...
```

**Error (500):**
```json
{
  "detail": "OpenAI API key not configured"
}
```

---

### 4. List User Chats
**GET** `/chat/list`

Get all chats for current user/guest session.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "chats": [
    {
      "chat_id": "chat_uuid",
      "title": "Revenue Discussion",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:30:00Z",
      "message_count": 4
    }
  ]
}
```

---

### 5. Get Chat History
**GET** `/chat/history/{chat_id}`

Get all messages in a specific chat.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "chat_id": "chat_uuid",
  "title": "Revenue Discussion",
  "messages": [
    {
      "message_id": "msg_uuid",
      "role": "human",
      "content": "What is your company's annual revenue?",
      "timestamp": "2024-01-01T12:00:00Z"
    },
    {
      "message_id": "msg_uuid",
      "role": "ai",
      "content": "TechCorp Solutions Inc has an annual revenue of $10 million...",
      "timestamp": "2024-01-01T12:00:05Z"
    }
  ]
}
```

**Error (404):**
```json
{
  "detail": "Chat not found"
}
```

---

### 6. Update Chat Title
**PUT** `/chat/title/{chat_id}`

Update the title of a chat.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Updated Revenue Discussion"
}
```

**Response (200):**
```json
{
  "message": "Chat title updated successfully",
  "chat_id": "chat_uuid",
  "new_title": "Updated Revenue Discussion"
}
```

---

### 7. Delete Chat
**DELETE** `/chat/{chat_id}`

Delete a chat and all its messages.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Chat deleted successfully",
  "chat_id": "chat_uuid"
}
```

---

### 8. List Documents
**GET** `/chat/documents`

List all documents in company's knowledge base.

**Headers:** `Authorization: Bearer <company_token>`

**Response (200):**
```json
{
  "documents": [
    {
      "doc_id": "doc_uuid",
      "filename": "techcorp-company-info.txt",
      "content_length": 500,
      "uploaded_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

### 9. Delete Document
**DELETE** `/chat/documents/{doc_id}`

Delete a document from knowledge base.

**Headers:** `Authorization: Bearer <company_token>`

**Response (200):**
```json
{
  "message": "Document deleted successfully",
  "doc_id": "doc_uuid"
}
```

**Error (404):**
```json
{
  "detail": "Document not found"
}
```

---

### 10. Get Knowledge Base Info
**GET** `/chat/knowledge-base`

Get knowledge base statistics and info.

**Headers:** `Authorization: Bearer <company_token>`

**Response (200):**
```json
{
  "kb_id": "kb_uuid",
  "company_id": "company_uuid",
  "index_name": "company-uuid-index",
  "document_count": 5,
  "created_at": "2024-01-01T12:00:00Z",
  "last_updated": "2024-01-01T15:30:00Z"
}
```

---

### 11. Clear Knowledge Base
**POST** `/chat/clear-knowledge-base`

Remove all documents from knowledge base.

**Headers:** `Authorization: Bearer <company_token>`

**Response (200):**
```json
{
  "message": "Knowledge base cleared successfully",
  "documents_removed": 5
}
```

---

### 12. Upload File
**POST** `/chat/upload-file`

Upload file to knowledge base.

**Headers:** `Authorization: Bearer <company_token>`

**Request:** Form data with file upload
```
Content-Type: multipart/form-data

file: <uploaded_file>
```

**Response (200):**
```json
{
  "message": "File uploaded successfully",
  "document": {
    "doc_id": "doc_uuid",
    "filename": "document.pdf",
    "content_length": 2048,
    "uploaded_at": "2024-01-01T12:00:00Z"
  }
}
```

---

### 13. Chat Service Health Check
**GET** `/chat/health`

**Response (200):**
```json
{
  "status": "healthy",
  "service": "chat"
}
```

---

## 🌐 Public Endpoints

### 1. Public Chat (by Slug)
**POST** `/public/chatbot/{company_slug}/chat`

Send message to public chatbot without authentication.

**Request Body:**
```json
{
  "message": "How many companies have you served?",
  "chat_id": "optional_chat_uuid",
  "chat_title": "Guest Chat"
}
```

**Response (200):** Streaming response
```
Content-Type: text/plain
X-Chat-ID: chat_uuid

TechCorp Solutions has served over 500 companies worldwide...
```

**Error (404):**
```json
{
  "detail": "Chatbot not found or not published"
}
```

---

### 2. Get Public Chatbot Info
**GET** `/public/chatbot/{company_slug}`

Get public information about a chatbot.

**Response (200):**
```json
{
  "company_id": "company_uuid",
  "name": "TechCorp Solutions Inc",
  "slug": "techcorp-solutions",
  "chatbot_title": "TechCorp AI Assistant",
  "chatbot_description": "AI technology expert assistant",
  "published_at": "2024-01-01T12:00:00Z"
}
```

---

### 3. Get Public Company Info
**GET** `/public/company/{company_slug}/info`

Get basic public company information.

**Response (200):**
```json
{
  "company_id": "company_uuid",
  "name": "TechCorp Solutions Inc",
  "slug": "techcorp-solutions",
  "chatbot_title": "TechCorp AI Assistant",
  "chatbot_description": "AI technology expert assistant",
  "is_published": true,
  "published_at": "2024-01-01T12:00:00Z"
}
```

---

### 4. Public Service Health Check
**GET** `/public/health`

**Response (200):**
```json
{
  "status": "healthy",
  "service": "public_chatbot"
}
```

---

## 🔒 Security & Data Isolation

### Multi-Tenant Architecture
- **Company Isolation**: Each company's data is completely isolated
- **User Access Control**: Users can only access their company's data
- **Guest Sessions**: Temporary sessions tied to specific companies
- **JWT Authentication**: Secure token-based authentication

### Security Boundaries
- Users cannot access other companies' information
- Cross-company data access is blocked at the API level
- Guest sessions are company-specific and time-limited
- All operations enforce company-based authorization

---

## ❌ Error Handling

### Common HTTP Status Codes

**400 Bad Request**
- Invalid request body
- Missing required fields
- Invalid data format

**401 Unauthorized**
- Missing or invalid authentication token
- Expired token

**403 Forbidden**
- Insufficient permissions
- Cross-company access attempt

**404 Not Found**
- Resource not found
- Invalid ID

**500 Internal Server Error**
- Server configuration issues
- Database connection errors
- AI service unavailable

### Error Response Format
```json
{
  "detail": "Error description"
}
```

---

## 🔧 Environment Configuration

### Required Environment Variables
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Pinecone Configuration  
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment

# Domain Configuration
DOMAIN_URL=mysite.com
```

---

## 📊 Testing

### Postman Collection
Use the provided `POSTMAN_COLLECTION_COMPREHENSIVE.json` for complete API testing:

- **46 test requests** across 8 phases
- **Multi-tenant data isolation testing**
- **Security boundary validation**
- **Complete CRUD operations**
- **Error handling scenarios**
- **Health check monitoring**

### Test Coverage
- ✅ Company registration and management
- ✅ User registration and authentication  
- ✅ Guest session management
- ✅ Chat functionality with AI responses
- ✅ Knowledge base management
- ✅ Public chatbot access
- ✅ Data isolation between companies
- ✅ Security boundary enforcement
- ✅ Error handling and edge cases
- ✅ Service health monitoring

---

## 🚀 Getting Started

1. **Set up environment variables** in `app/.env`
2. **Start the API server**: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
3. **Import Postman collection** for testing
4. **Register a company** using `/auth/company/register`
5. **Set up knowledge base** using `/chat/setup-knowledge-base`
6. **Upload content** using `/chat/upload-text`
7. **Test chat functionality** using `/chat/send`
8. **Publish chatbot** using `/auth/company/publish-chatbot`

Your multi-tenant AI chatbot platform is now ready! 
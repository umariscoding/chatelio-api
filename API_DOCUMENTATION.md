# Multi-Tenant Chatbot API Documentation

## Overview
This API provides authentication and user management for a multi-tenant chatbot platform. Companies can register, manage users, and provide chatbot services to both registered users and guest sessions.

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

## Notes for Frontend Development

1. **Token Management**: Always store tokens securely and implement automatic refresh logic
2. **Error Handling**: Implement proper error handling for all HTTP status codes
3. **Guest Sessions**: Guest sessions expire after 24 hours
4. **Progressive Enhancement**: Offer guest-to-user conversion after 2-3 interactions
5. **Company Context**: Most user operations require a valid company_id
6. **Session Validation**: Regularly check session validity, especially for long-running applications

---

## Rate Limiting & Security

- All endpoints are protected against common attacks
- JWT tokens have appropriate expiration times
- Password hashing uses bcrypt with salt rounds
- Session management prevents token replay attacks
- Input validation on all endpoints

---

This documentation covers all current authentication and user management endpoints. As you add chat functionality and other features, you can extend this documentation accordingly. 
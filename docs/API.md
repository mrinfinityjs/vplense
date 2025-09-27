# vpLense API Documentation

Complete API reference for vpLense - Verified Privacy Lense

**Version 1.0** - Production Ready

## 🔗 Base URL
```
http://localhost:5000
```

## 📋 Authentication

### Admin Authentication
Most admin endpoints require authentication. Use session-based authentication:

```bash
# Login
curl -X POST http://localhost:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password": "admin"}' \
  -c cookies.txt

# Use cookies for subsequent requests
curl -X GET http://localhost:5000/api/admin/config -b cookies.txt
```

## 🎯 Core Endpoints

### Questions

#### `GET /api/questions`
Retrieve all pending questions.

**Response:**
```json
[
  {
    "id": "uuid",
    "text": "Question text",
    "timestamp": "2024-01-01T00:00:00",
    "status": "pending",
    "ip": "127.0.0.1"
  }
]
```

#### `POST /api/questions`
Submit a new question.

**Request:**
```json
{
  "question": "What is your opinion on data privacy?"
}
```

**Response:**
```json
{
  "id": "uuid",
  "text": "What is your opinion on data privacy?",
  "timestamp": "2024-01-01T00:00:00",
  "status": "pending",
  "ip": "127.0.0.1"
}
```

#### `POST /api/questions/{id}/accept`
Accept a question (admin only).

**Response:**
```json
{
  "id": "uuid",
  "text": "Question text",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `POST /api/questions/{id}/answer`
Mark question as answered (admin only).

**Response:**
```json
{
  "success": true
}
```

#### `POST /api/questions/{id}/reject`
Reject a question (admin only).

**Response:**
```json
{
  "success": true
}
```

#### `DELETE /api/questions/{id}`
Delete a question (admin only).

**Response:**
```json
{
  "success": true
}
```

### Comments

#### `GET /api/comments`
Retrieve all pending comments.

**Response:**
```json
[
  {
    "id": "uuid",
    "text": "Comment text",
    "timestamp": "2024-01-01T00:00:00",
    "status": "pending",
    "ip": "127.0.0.1"
  }
]
```

#### `POST /api/comments`
Submit a new comment.

**Request:**
```json
{
  "comment": "Great stream!"
}
```

**Response:**
```json
{
  "id": "uuid",
  "text": "Great stream!",
  "timestamp": "2024-01-01T00:00:00",
  "status": "pending",
  "ip": "127.0.0.1"
}
```

#### `POST /api/comments/{id}/accept`
Accept a comment (admin only).

**Response:**
```json
{
  "id": "uuid",
  "text": "Comment text",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `POST /api/comments/{id}/answer`
Mark comment as accepted (admin only).

**Response:**
```json
{
  "success": true
}
```

#### `POST /api/comments/{id}/reject`
Reject a comment (admin only).

**Response:**
```json
{
  "success": true
}
```

### Topics

#### `GET /api/topics`
Retrieve all topics.

**Response:**
```json
[
  {
    "id": "uuid",
    "text": "Topic text",
    "timestamp": "2024-01-01T00:00:00"
  }
]
```

#### `POST /api/topics`
Add a new topic (admin only).

**Request:**
```json
{
  "topic": "Data Privacy"
}
```

**Response:**
```json
{
  "id": "uuid",
  "text": "Data Privacy",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `DELETE /api/topics/{id}`
Delete a topic (admin only).

**Response:**
```json
{
  "success": true
}
```

## 🎁 Giveaway Endpoints

### `GET /api/giveaways`
Retrieve all giveaways.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Privacy Protection Kit",
    "items": [
      {
        "id": "uuid",
        "name": "VPN Subscription",
        "link": "https://example.com/vpn",
        "added_at": "2024-01-01T00:00:00"
      }
    ],
    "recurring": false,
    "recurring_interval": 0,
    "remove_on_accept": true,
    "created_at": "2024-01-01T00:00:00",
    "status": "active"
  }
]
```

### `POST /api/giveaways`
Create a new giveaway (admin only).

**Request:**
```json
{
  "name": "Privacy Protection Kit",
  "delay_minutes": 0,
  "recurring": false,
  "recurring_interval": 0,
  "remove_on_accept": true
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Privacy Protection Kit",
  "items": [],
  "recurring": false,
  "recurring_interval": 0,
  "remove_on_accept": true,
  "created_at": "2024-01-01T00:00:00",
  "status": "active"
}
```

### `DELETE /api/giveaways/{id}`
Delete a giveaway (admin only).

**Response:**
```json
{
  "success": true
}
```

### `POST /api/giveaways/{id}/items`
Add item to giveaway (admin only).

**Request:**
```json
{
  "name": "VPN Subscription",
  "link": "https://example.com/vpn"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "VPN Subscription",
  "link": "https://example.com/vpn",
  "added_at": "2024-01-01T00:00:00"
}
```

### `DELETE /api/giveaways/{id}/items/{item_id}`
Delete item from giveaway (admin only).

**Response:**
```json
{
  "success": true
}
```

### `POST /api/giveaways/{id}/accept`
Accept a giveaway item (winner only).

**Response:**
```json
{
  "success": true,
  "item": {
    "id": "uuid",
    "name": "VPN Subscription",
    "link": "https://example.com/vpn"
  }
}
```

### `POST /api/giveaways/{id}/payitforward`
Pay it forward for a giveaway item (winner only).

**Response:**
```json
{
  "success": true
}
```

## 🛡️ Admin Endpoints

### Authentication

#### `POST /api/admin/login`
Admin login.

**Request:**
```json
{
  "password": "admin"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "uuid"
}
```

#### `POST /api/admin/logout`
Admin logout.

**Response:**
```json
{
  "success": true
}
```

### Configuration

#### `GET /api/admin/config`
Get system configuration (admin only).

**Response:**
```json
{
  "app_name": "vpLense",
  "admin_password": "admin",
  "rate_limit_global": "30:5",
  "rate_limit_per_ip": "3:30",
  "give_away_max_prize_per_ip": "2:64800",
  "give_away_item_timeout": "30",
  "give_away_max_payitforwards": "3"
}
```

#### `POST /api/admin/config`
Update system configuration (admin only).

**Request:**
```json
{
  "app_name": "vpLense",
  "admin_password": "new_password",
  "rate_limit_global": "30:5",
  "rate_limit_per_ip": "3:30"
}
```

**Response:**
```json
{
  "success": true
}
```

### Access Control

#### `GET /api/admin/whitelist`
Get IP whitelist (admin only).

**Response:**
```json
[
  {
    "ip": "192.168.1.100",
    "added_at": "2024-01-01T00:00:00",
    "reason": "Trusted user"
  }
]
```

#### `POST /api/admin/whitelist`
Add IP to whitelist (admin only).

**Request:**
```json
{
  "ip": "192.168.1.100",
  "reason": "Trusted user"
}
```

**Response:**
```json
{
  "success": true
}
```

#### `DELETE /api/admin/whitelist/{ip}`
Remove IP from whitelist (admin only).

**Response:**
```json
{
  "success": true
}
```

#### `GET /api/admin/blacklist`
Get IP blacklist (admin only).

**Response:**
```json
[
  {
    "ip": "192.168.1.200",
    "added_at": "2024-01-01T00:00:00",
    "reason": "Abusive behavior"
  }
]
```

#### `POST /api/admin/blacklist`
Add IP to blacklist (admin only).

**Request:**
```json
{
  "ip": "192.168.1.200",
  "reason": "Abusive behavior"
}
```

**Response:**
```json
{
  "success": true
}
```

#### `DELETE /api/admin/blacklist/{ip}`
Remove IP from blacklist (admin only).

**Response:**
```json
{
  "success": true
}
```

### System Management

#### `POST /api/admin/reset`
Reset all data (admin only).

**Response:**
```json
{
  "success": true
}
```

#### `POST /api/admin/video-source`
Change video source (admin only).

**Request:**
```json
{
  "url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
  "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response:**
```json
{
  "success": true
}
```

## 📊 Statistics

### `GET /api/statistics`
Get system statistics.

**Response:**
```json
{
  "questions_asked": 25,
  "questions_answered": 20,
  "comments_given": 15,
  "comments_accepted": 12
}
```

### `GET /api/questions_answered`
Get answered questions.

**Response:**
```json
[
  {
    "id": "uuid",
    "text": "Question text",
    "timestamp": "2024-01-01T00:00:00",
    "answered_at": "2024-01-01T00:05:00"
  }
]
```

### `GET /api/comments_answered`
Get accepted comments.

**Response:**
```json
[
  {
    "id": "uuid",
    "text": "Comment text",
    "timestamp": "2024-01-01T00:00:00",
    "accepted_at": "2024-01-01T00:05:00"
  }
]
```

## 🔌 Socket.IO Events

### Client Events

#### `connect`
Connect to the server.

#### `disconnect`
Disconnect from the server.

### Server Events

#### `new_question`
New question submitted.

```json
{
  "id": "uuid",
  "text": "Question text",
  "timestamp": "2024-01-01T00:00:00",
  "status": "pending",
  "ip": "127.0.0.1"
}
```

#### `new_comment`
New comment submitted.

```json
{
  "id": "uuid",
  "text": "Comment text",
  "timestamp": "2024-01-01T00:00:00",
  "status": "pending",
  "ip": "127.0.0.1"
}
```

#### `question_accepted`
Question accepted by admin.

```json
{
  "id": "uuid",
  "text": "Question text",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `comment_accepted`
Comment accepted by admin.

```json
{
  "id": "uuid",
  "text": "Comment text",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `giveaway_winner_selected`
Winner selected for giveaway.

```json
{
  "giveaway_id": "uuid",
  "giveaway_name": "Privacy Protection Kit",
  "item": {
    "id": "uuid",
    "name": "VPN Subscription",
    "link": "https://example.com/vpn"
  },
  "timeout": 30
}
```

#### `giveaway_item_details`
Prize details for winner.

```json
{
  "giveaway_id": "uuid",
  "giveaway_name": "Privacy Protection Kit",
  "item": {
    "id": "uuid",
    "name": "VPN Subscription",
    "link": "https://example.com/vpn"
  }
}
```

#### `admin_action_notification`
Admin action notification.

```json
{
  "action": "giveaway_accepted",
  "message": "A winner has accepted a giveaway item",
  "timestamp": "2024-01-01T00:00:00"
}
```

## 🚨 Error Responses

### Rate Limiting
```json
{
  "error": "Rate limit exceeded for this IP"
}
```

### Authentication Required
```json
{
  "error": "Not authorized"
}
```

### Not Found
```json
{
  "error": "Question not found"
}
```

### Validation Error
```json
{
  "error": "Question cannot be empty"
}
```

## 📝 Rate Limiting

The API implements multi-tier rate limiting:

- **Global Rate Limit**: System-wide request limit
- **Per-IP Rate Limit**: Individual user rate limit
- **Excessive Usage**: Detection and handling of abuse

### Rate Limit Headers
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1640995200
```

## 🔒 Security Considerations

- All admin endpoints require authentication
- Rate limiting prevents abuse
- Input validation and sanitization
- IP-based access control
- Session-based authentication
- No sensitive data in responses

## 📚 Examples

### Complete Workflow Example

```bash
# 1. Login as admin
curl -X POST http://localhost:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password": "admin"}' \
  -c cookies.txt

# 2. Create a giveaway
curl -X POST http://localhost:5000/api/giveaways \
  -H "Content-Type: application/json" \
  -d '{"name": "Privacy Kit", "delay_minutes": 0}' \
  -b cookies.txt

# 3. Add items to giveaway
curl -X POST http://localhost:5000/api/giveaways/{id}/items \
  -H "Content-Type: application/json" \
  -d '{"name": "VPN", "link": "https://example.com"}' \
  -b cookies.txt

# 4. Submit a question
curl -X POST http://localhost:5000/api/questions \
  -H "Content-Type: application/json" \
  -d '{"question": "What is data privacy?"}'

# 5. Accept the question
curl -X POST http://localhost:5000/api/questions/{id}/accept \
  -b cookies.txt
```

---

For more information, see the main README.md and FEATURES.md documentation.

**Repository**: https://github.com/mrinfinityjs/vplense

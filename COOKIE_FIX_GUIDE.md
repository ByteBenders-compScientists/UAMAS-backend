# Cookie Storage Fix Guide

## Problem
Cookies are not being stored in the frontend when the backend is hosted on Azure Ubuntu VM with Docker and Nginx.

## Root Causes
1. **JWT_COOKIE_SECURE=True** requires HTTPS but the deployment may not be using HTTPS properly
2. **SameSite=None** requires HTTPS to work correctly
3. Missing cookie header configuration in nginx
4. CORS headers not properly exposing Set-Cookie header

## Solution

### 1. Update Environment Variables

#### For HTTP Deployment (Development/Testing)
Add these to your `.env` files in **Authentication**, **backend**, and **api-gateway** directories:

```env
# Cookie settings for HTTP (no SSL)
JWT_COOKIE_SECURE=False
JWT_COOKIE_SAMESITE=Lax
```

**Note:** With `SameSite=Lax`, cookies will work for same-site requests but may not work for cross-origin POST requests.

#### For HTTPS Deployment (Production - Recommended)
Add these to your `.env` files:

```env
# Cookie settings for HTTPS (with SSL)
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None
```

**Important:** `SameSite=None` requires HTTPS. Your nginx must be configured with SSL certificates.

### 2. Configure Nginx

#### Option A: Using HTTP (Quick Fix for Testing)

1. Update your nginx configuration to proxy requests properly:

```nginx
server {
    listen 80;
    server_name your-server-ip;

    location /api/v1/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass_header Set-Cookie;
    }
}
```

2. Set environment variables:
```bash
JWT_COOKIE_SECURE=False
JWT_COOKIE_SAMESITE=Lax
```

3. Restart your Docker containers:
```bash
docker-compose down
docker-compose up -d --build
```

4. Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Option B: Using HTTPS (Recommended for Production)

1. Install SSL certificate using Certbot:
```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

2. Use the provided `nginx.conf.example` as a reference and update your nginx configuration.

3. Set environment variables:
```bash
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None
```

4. Restart services:
```bash
docker-compose down
docker-compose up -d --build
sudo systemctl reload nginx
```

### 3. Verify the Fix

#### Test Cookie Setting
1. Open browser DevTools (F12)
2. Go to Network tab
3. Make a login request to your backend
4. Check the response headers for `Set-Cookie`
5. Go to Application/Storage > Cookies
6. Verify cookies are stored

#### Test Cookie Sending
1. Make an authenticated request (e.g., `/api/v1/auth/me`)
2. Check request headers include `Cookie` header with your tokens
3. Verify the request succeeds

### 4. Common Issues and Solutions

#### Issue: Cookies still not working with HTTP
**Solution:** Make sure `JWT_COOKIE_SECURE=False` in ALL service .env files (Authentication, backend, api-gateway)

#### Issue: Cross-origin requests not working
**Solution:** Verify your frontend domain is in the CORS origins list in all `app.py` files

#### Issue: Cookies work on localhost but not on Azure VM
**Solution:** 
- If using HTTP: Set `JWT_COOKIE_SECURE=False` and `JWT_COOKIE_SAMESITE=Lax`
- If using HTTPS: Ensure SSL is properly configured in nginx

#### Issue: Getting CORS errors
**Solution:** Check that:
- `supports_credentials: True` is set in CORS configuration
- Frontend is sending `credentials: 'include'` in fetch/axios requests
- Backend CORS origins include your frontend domain

### 5. Frontend Requirements

Your frontend must also be configured correctly:

#### For fetch API:
```javascript
fetch('https://your-backend.com/api/v1/auth/login', {
  method: 'POST',
  credentials: 'include',  // IMPORTANT: This tells browser to send cookies
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ email, password })
})
```

#### For axios:
```javascript
axios.defaults.withCredentials = true;

// Or per request:
axios.post('https://your-backend.com/api/v1/auth/login', 
  { email, password },
  { withCredentials: true }
)
```

## Quick Troubleshooting Checklist

- [ ] Updated `.env` files with JWT_COOKIE_SECURE and JWT_COOKIE_SAMESITE
- [ ] Rebuilt and restarted Docker containers
- [ ] Updated nginx configuration to proxy Set-Cookie headers
- [ ] Reloaded nginx configuration
- [ ] Verified frontend sends `credentials: 'include'` or `withCredentials: true`
- [ ] Checked browser DevTools for Set-Cookie in response headers
- [ ] Checked browser DevTools for Cookie in request headers
- [ ] Verified CORS origins include your frontend domain
- [ ] If using HTTPS, verified SSL certificates are valid

## Testing Script

Run this from your Azure VM to test the configuration:

```bash
# Test login and check for Set-Cookie header
curl -i -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"yourpassword"}'

# Look for "Set-Cookie:" in the response headers
```

## Additional Resources

- [Flask-JWT-Extended Cookie Documentation](https://flask-jwt-extended.readthedocs.io/en/stable/options/#cookie-options)
- [MDN: SameSite Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)
- [Nginx Proxy Configuration](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)

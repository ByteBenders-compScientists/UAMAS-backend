# Quick Fix for Cookie Storage Issue

## The Problem
Your backend is on Azure VM with Docker and Nginx, but cookies aren't being stored in the frontend.

## The Cause
`JWT_COOKIE_SECURE=True` was hardcoded in the config, which requires HTTPS. If your nginx doesn't have SSL properly configured, cookies won't work.

## The Solution (Choose One)

### Option 1: Quick Fix for HTTP (Testing)
**Best if you don't have SSL certificates yet**

1. Add to ALL `.env` files (Authentication, backend, api-gateway):
   ```bash
   JWT_COOKIE_SECURE=False
   JWT_COOKIE_SAMESITE=Lax
   ```

2. Restart Docker containers:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. That's it! Cookies should work now.

### Option 2: Proper Fix with HTTPS (Production)
**Best for production - more secure**

1. Install SSL certificate on your Azure VM:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

2. Add to ALL `.env` files:
   ```bash
   JWT_COOKIE_SECURE=True
   JWT_COOKIE_SAMESITE=None
   ```

3. Update nginx config using `nginx.conf.example` as reference

4. Restart services:
   ```bash
   docker-compose down
   docker-compose up -d --build
   sudo systemctl reload nginx
   ```

## How to Test

1. Open browser DevTools (F12)
2. Go to Network tab
3. Login to your app
4. Check response headers - you should see `Set-Cookie`
5. Go to Application > Cookies
6. Your cookies should be there!

## Need More Help?

- **Detailed guide**: See [COOKIE_FIX_GUIDE.md](COOKIE_FIX_GUIDE.md)
- **Nginx config**: See [nginx.conf.example](nginx.conf.example)
- **Environment setup**: See `.env.example` files in each service directory

## Common Mistakes to Avoid

❌ Only updating one .env file - **Update ALL three** (Authentication, backend, api-gateway)
❌ Using `JWT_COOKIE_SECURE=True` without HTTPS - Won't work!
❌ Forgetting to restart Docker containers after changing .env
❌ Frontend not sending `credentials: 'include'` in fetch requests

## Need to Roll Back?

If something goes wrong, you can always:
```bash
git checkout main
docker-compose down
docker-compose up -d --build
```

# Production Deployment Guide

## Overview
This guide covers deploying the Knowledge Base PWA to production with:
- **Backend**: Render (FastAPI + Python)
- **Frontend**: Vercel (React + TypeScript) 
- **Database**: Supabase (PostgreSQL)

## Prerequisites
- Render account
- Vercel account  
- Supabase project
- Google Gemini API key

## 1. Database Setup (Supabase)

### Create Supabase Project
1. Go to [Supabase](https://supabase.com) and create new project
2. Note your database URL from Settings > Database
3. The URL format: `postgresql://postgres:[password]@[host]:5432/postgres`

### Database Initialization
The database tables will be automatically created on first backend startup using SQLAlchemy.

## 2. Backend Deployment (Render)

### Prepare Backend
1. Ensure `requirements.txt` includes all dependencies:
   ```
   fastapi>=0.104.0
   uvicorn[standard]>=0.24.0
   sqlalchemy>=2.0.0
   python-dotenv>=1.0.0
   google-generativeai>=0.3.0
   pydantic>=2.8.0
   python-multipart>=0.0.6
   python-jose[cryptography]>=3.3.0
   passlib[bcrypt]>=1.7.4
   email-validator>=2.0.0
   psycopg2-binary>=2.9.0
   pywebpush>=1.14.0
   apscheduler>=3.10.0
   pytz>=2023.3
   ```

### Deploy to Render
1. Connect your GitHub repository to Render
2. Create new Web Service
3. Configure environment:
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python main.py`
   - **Python Version**: 3.13

### Environment Variables
Set these in Render dashboard:
```bash
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=your_secure_jwt_secret_key
FRONTEND_ORIGINS=https://your-app.vercel.app
VAPID_PUBLIC_KEY=your_vapid_public_key
VAPID_PRIVATE_KEY=your_vapid_private_key
VAPID_SUBJECT=mailto:your-email@example.com
ENVIRONMENT=production
```

**Note**: Generate VAPID keys using:
```bash
npx web-push generate-vapid-keys
```

## 3. Frontend Deployment (Vercel)

### Prepare Frontend
1. Update `vercel.json` if needed:
   ```json
   {
     "buildCommand": "cd frontend && npm run build",
     "outputDirectory": "frontend/dist",
     "installCommand": "cd frontend && npm install",
     "framework": "vite",
     "rewrites": [
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```

### Deploy to Vercel
1. Connect your GitHub repository to Vercel
2. Configure build settings:
   - **Framework**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### Environment Variables
Set these in Vercel dashboard:
```bash
VITE_API_URL=https://your-backend.onrender.com
VITE_VAPID_PUBLIC_KEY=your_vapid_public_key
```

**Note**: Use the same VAPID public key from your backend configuration.

## 4. Post-Deployment Setup

### Verify Deployment
1. **Backend Health**: Visit `https://your-backend.onrender.com/health`
2. **Frontend**: Visit `https://your-app.vercel.app`
3. **Database**: Check Supabase dashboard for table creation

### Create First User
1. Go to your frontend signup page
2. Create your admin account
3. Verify login functionality

### Test API Integration
1. Create a test note
2. Verify AI summary generation
3. Test CRUD operations

### Test Push Notifications
1. Go to Search page → User menu → "Daily Reminders"
2. Enable notifications (browser will request permission)
3. Use "Send Test Notification" button
4. Verify notification appears on desktop/mobile
5. Check scheduler status: `GET /api/push/scheduler/status`
6. Verify daily notifications are scheduled for 10 AM IST

## 5. Production Checklist

### Security
- [ ] Strong JWT secret key set
- [ ] Database credentials secure
- [ ] CORS properly configured
- [ ] HTTPS enabled on both domains
- [ ] VAPID keys securely stored

### Performance
- [ ] Database connection pooling configured
- [ ] Frontend assets optimized
- [ ] Service worker functioning
- [ ] PWA installation working

### Push Notifications
- [ ] VAPID keys generated and configured
- [ ] Push notification permissions working
- [ ] Daily scheduler running (10 AM IST)
- [ ] Test notifications functional
- [ ] Multi-device notifications working

### Monitoring
- [ ] Render logs accessible
- [ ] Vercel deployment logs checked
- [ ] Database performance monitored
- [ ] Error tracking enabled

## 6. Environment Configuration

### Development vs Production
```bash
# Development (.env)
DATABASE_URL=  # Empty for SQLite
GEMINI_API_KEY=your_key
VITE_API_URL=http://localhost:8000

# Production
DATABASE_URL=postgresql://... # Supabase
GEMINI_API_KEY=your_key
VITE_API_URL=https://your-backend.onrender.com
FRONTEND_ORIGINS=https://your-app.vercel.app
```

## 7. Common Issues

### Backend Startup
- Ensure PostgreSQL connection string is correct
- Check Render logs for Python errors
- Verify all environment variables are set

### Frontend API Calls
- Confirm CORS configuration includes Vercel domain
- Check VITE_API_URL points to correct backend
- Verify API endpoints are accessible

### Database Connection
- Test Supabase connection locally first
- Check firewall settings
- Ensure connection pooling is configured

## 8. Maintenance

### Updates
1. Update dependencies regularly
2. Monitor for security patches
3. Test deployments in staging first
4. Keep database backups current

### Scaling
- Monitor Render resource usage
- Consider upgrading Render plan if needed
- Use Supabase connection pooling for high traffic
- Implement caching if necessary

---

**This setup provides a production-ready Knowledge Base PWA with automated CI/CD and managed infrastructure.**
# Knowledge Base PWA

A secure, multi-user note-taking Progressive Web App with AI-powered summaries, daily push notifications, and user authentication. Built with React + TypeScript frontend and FastAPI + Python backend.

## ✨ Current Features

### 🔔 Push Notifications
- **Daily notifications** at 10 AM IST with personalized note reminders
- **Round-robin note selection** - each user gets different notes each day
- **Multi-device support** - notifications work across phones, tablets, laptops
- **Web Push API** with VAPID authentication for browser notifications
- **GitHub Actions scheduling** with direct API triggering for reliability
- **User isolation** - each user gets their own notification sequence

### 🔐 User Authentication & Security
- **User registration** with email and password (no email verification required)
- **Secure login** with JWT token-based authentication (180-day expiration)
- **User isolation** - complete data separation between users
- **Logout functionality** with user dropdown menu in page headers
- **Password hashing** using pbkdf2_sha256 for security
- **Protected routes** - all pages require authentication
- **Database resilience** with connection pooling and retry logic

### 📝 Note Management  
- **Create notes** with floating action button (+)
- **View notes** in card layout with AI summary highlights
- **Individual note pages** with full content view at `/note/:id`
- **Edit notes** with content updates and optional AI summary regeneration
- **Delete notes** with confirmation modal
- **Real-time timestamps** with "just now", "5m ago", "2h ago" formatting
- **User-scoped notes** - each user sees only their own notes

### 📚 Notebooks Organization
- **Create notebooks** to organize notes by topic, project, or theme
- **Many-to-many relationships** - notes can belong to multiple notebooks
- **User-scoped notebooks** - each user manages their own notebooks
- **Notebook management** with rename, delete, and note count displays
- **Add notes to notebooks** with single-click or multi-select batch operations
- **Remove notes from notebooks** with batch selection capabilities
- **Inline editing** with Enter/Escape keyboard shortcuts

### 🔍 Search Functionality
- **Real-time search** across both note content and AI summaries
- **User-scoped search** - search only within user's own notes
- **Keyword highlighting** in search results
- **Debounced search** (300ms delay) for optimal performance
- **Case-insensitive matching** for comprehensive results

### 🧭 Navigation System
- **Bottom navigation** with three main sections:
  - **Notebooks** (left) - Organize and manage note collections
  - **Search** (center) - Find notes quickly with keyword search
  - **All Notes** (right) - View all notes in chronological order

### 🤖 AI Integration
- **Google Gemini API** integration for automatic note summarization
- **40-word optimized prompts** for mobile notification compatibility
- **Multi-model fallback**: gemini-2.5-flash → gemini-2.5-pro → gemini-2.0-flash
- **Background processing** - AI summaries generate without blocking note creation
- **Smart polling** checks for AI summary completion every 2 seconds for 20 seconds
- **Retry logic** with exponential backoff for API reliability


### 🎨 Dark Theme UI
- **Black background** (#000000) with orange accent colors (#F97316)
- **Responsive design** optimized for mobile and desktop
- **Custom Tailwind classes**: note-card, btn-primary, btn-secondary, input-field
- **Loading states** with animated spinners during AI processing
- **Floating action button** with hover effects and tooltip

### 📱 PWA Capabilities
- **Installable app** with manifest configuration
- **Service worker** for offline functionality
- **App icons** (192x192, 512x512 SVG format)
- **Standalone display** mode for native app experience

## 🏗️ Technical Architecture

### Frontend (`/frontend/`)
- **React 19.2.0** with TypeScript and Vite 7.2.2
- **React Router DOM 7.9.6** for client-side routing with bottom navigation
- **React Context API** for global state management (NotesContext)
- **Tailwind CSS 3.4.0** for styling with custom component classes
- **Manual fetch API** calls - no external HTTP libraries
- **Service worker** registration for push notifications

### Backend (`/backend/`)
- **FastAPI** with Python 3.13 and Uvicorn server
- **SQLAlchemy 2.0+** ORM with PostgreSQL (Supabase) database
- **google-generativeai 0.3+** for AI summarization
- **pywebpush** for Web Push API notifications
- **CORS enabled** for localhost:5173/5174 development and Vercel production

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Notes Table
```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    ai_summary TEXT,
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### Notebooks Table
```sql
CREATE TABLE notebooks (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### Note-Notebook Junction Table (Many-to-Many)
```sql
CREATE TABLE note_notebooks (
    note_id INTEGER,
    notebook_id INTEGER,
    PRIMARY KEY (note_id, notebook_id),
    FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
    FOREIGN KEY (notebook_id) REFERENCES notebooks (id) ON DELETE CASCADE
);
```

### Push Subscriptions Table
```sql
CREATE TABLE push_subscriptions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    endpoint VARCHAR NOT NULL UNIQUE,
    p256dh_key VARCHAR NOT NULL,
    auth_key VARCHAR NOT NULL,
    user_agent VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```


## 🚀 Setup & Development

### Prerequisites
- Python 3.13+
- Node.js 18+
- Google Gemini API Key
- VAPID Keys for push notifications
- PostgreSQL database (Supabase recommended)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create environment file
cat > .env << EOF
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:pass@host:port/dbname
VAPID_PUBLIC_KEY=your_vapid_public_key
VAPID_PRIVATE_KEY=your_vapid_private_key
VAPID_SUBJECT=mailto:support@example.com
JWT_SECRET_KEY=your_secret_key
EOF

# Run migration script (for existing installations)
python migrate_to_multiuser.py

# Start backend server
python main.py
```
**Backend runs on**: http://127.0.0.1:8000

### Frontend Setup
```bash
cd frontend
npm install

# Create environment file
echo "VITE_VAPID_PUBLIC_KEY=your_vapid_public_key" > .env

npm run dev
```
**Frontend runs on**: http://localhost:5173

### First Time Setup & Migration

For new installations, the database will be automatically created. For existing installations with data, run the migration script to preserve your notes:

```bash
cd backend
source venv/bin/activate
python migrate_to_multiuser.py
```

**Default Admin Account (after migration):**
- Email: `admin@localhost.com`
- Password: `admin123`
- All existing notes and notebooks will be assigned to this admin user

## 🔌 API Endpoints

### Authentication API
- `POST /api/auth/signup` - User registration (email, password, optional name)
- `POST /api/auth/login` - User login (returns JWT token)
- `GET /api/auth/me` - Get current user info (requires authentication)
- `POST /api/auth/logout` - User logout (clears token)

### Notes API (Protected - requires authentication)
- `GET /api/notes` - List user's notes with AI summaries
- `POST /api/notes` - Create note (triggers background AI summarization)
- `GET /api/notes/{id}` - Get individual note details
- `PUT /api/notes/{id}` - Update note content with optional summary regeneration
- `DELETE /api/notes/{id}` - Delete note permanently

### Notebooks API (Protected - requires authentication)
- `GET /api/notebooks` - List user's notebooks with note counts
- `POST /api/notebooks` - Create new notebook
- `GET /api/notebooks/{id}` - Get notebook with associated notes
- `PUT /api/notebooks/{id}` - Update notebook title
- `DELETE /api/notebooks/{id}` - Delete notebook (preserves notes)
- `POST /api/notebooks/{notebook_id}/notes/{note_id}` - Add note to notebook
- `DELETE /api/notebooks/{notebook_id}/notes/{note_id}` - Remove note from notebook

### Search API (Protected - requires authentication)
- `GET /api/search?q={query}` - Search user's notes by content and AI summaries

### Push Notifications API (Protected - requires authentication)
- `POST /api/push/subscribe` - Register device for push notifications
- `DELETE /api/push/unsubscribe` - Remove device from notifications
- `GET /api/push/subscriptions` - List user's subscribed devices
- `POST /api/push/test-notification` - Send test notification to current user
- `POST /api/push/send-daily-notifications` - Trigger daily notifications (GitHub Actions)

### Health/Status
- `GET /` - API status message
- `GET /health` - Health check endpoint
- `GET /api/wake-server` - Wake server from sleep (external services)
- `GET /api/push/scheduler/status` - Notification scheduler status


## 🎨 Styling System

### Custom CSS Classes (defined in `src/index.css`)
```css
.note-card          /* Gray card with hover effects */
.btn-primary        /* Orange buttons */
.btn-secondary      /* Gray buttons */
.input-field        /* Form inputs with orange focus */
.floating-add-button /* Fixed position + button */
```

### Color Scheme
- **Background**: Black (#000000)
- **Cards**: Gray-900 (#111827)
- **Borders**: Gray-800 (#1F2937)
- **Primary**: Orange-500 (#F97316)
- **Text**: White/Gray spectrum

## 📦 Key Dependencies

### Frontend
```json
{
  "react": "^19.2.0",
  "react-router-dom": "^7.9.6",
  "tailwindcss": "^3.4.0",
  "vite": "^7.2.2",
  "vite-plugin-pwa": "^1.1.0"
}
```

### Backend
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
google-generativeai>=0.3.0
python-dotenv>=1.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
email-validator>=2.0.0
pywebpush==1.14.0
APScheduler==3.10.4
pytz==2023.3
```

## 🔧 Development Commands

```bash
# Backend
source venv/bin/activate && python main.py

# Frontend
npm run dev

# Build & Check
npm run build
npm run lint
```

## 📊 Current Status

**✅ Fully Functional Features:**
- **Push Notifications**: Daily reminders at 10 AM IST with round-robin note selection
- **User Authentication**: JWT-based signup/login with 180-day sessions and user isolation
- **Notes Management**: Create, edit, delete, view with AI summaries
- **Notebooks Organization**: Many-to-many relationships with batch operations
- **Search System**: Real-time keyword search with highlighting
- **Bottom Navigation**: Three-tab navigation system
- **Multi-select Operations**: Batch add/remove notes from notebooks
- **PWA Functionality**: Installable with service worker and push notifications
- **Dark Theme UI**: Complete orange-accent design system
- **Multi-device Support**: Notifications work across phones, tablets, laptops

**Database**: PostgreSQL (Supabase) with users, notes, notebooks, push_subscriptions  
**Backend**: FastAPI with SQLAlchemy ORM, JWT auth, Web Push API  
**Frontend**: React 19 with TypeScript, service worker, push notifications  
**AI Integration**: Google Gemini API for note summarization  
**Scheduling**: GitHub Actions for reliable daily notification delivery  

## 🔍 Known Behavior

### Authentication Flow
- **Public routes**: `/login` and `/signup` pages (no authentication required)
- **Protected routes**: All other pages require valid JWT token
- **Token expiration**: 180-day token lifespan for persistent sessions
- **User isolation**: Complete data separation - users only see their own content
- **Logout functionality**: Available via user dropdown in page headers

### Push Notifications
- **Daily delivery**: 10 AM IST via GitHub Actions direct API trigger
- **Round-robin selection**: Each user gets different notes each day based on day of year
- **Multi-device sync**: Same note delivered to all user's subscribed devices
- **Web Push API**: Browser-native notifications with VAPID authentication
- **Subscription management**: Users can enable/disable notifications per device


### AI Processing
- **Async generation**: Summaries generate in background after note creation
- **Polling updates**: Frontend checks every 2 seconds for summary completion
- **Fallback chain**: Multiple Gemini models ensure high availability

## 🎯 Key Features Summary

### 📱 User Experience
- **Three-tab bottom navigation** for seamless organization
- **Floating action buttons** with consistent design patterns
- **Multi-select operations** with checkboxes and batch actions
- **Inline editing** with keyboard shortcuts (Enter/Escape)
- **Real-time search** with 300ms debounced input

### 🔧 Technical Highlights
- **Many-to-many database relationships** for flexible note organization
- **Background AI processing** with polling and retry logic
- **Service worker** for PWA functionality
- **Responsive design** optimized for mobile and desktop
- **Modern React patterns** with Context API and TypeScript

### 🚀 Production Ready
- **Complete CRUD operations** for notes and notebooks
- **Robust error handling** with user feedback
- **Dark theme optimization** with accessibility considerations
- **API documentation** with comprehensive endpoint coverage
- **Database schema** designed for scalability

---

**A comprehensive knowledge management PWA with AI-powered insights, daily push notifications, and flexible organization.**
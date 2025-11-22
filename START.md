# Quick Start Guide

## Setup (One Time)

1. **Run setup:**
   ```bash
   ./setup.sh
   ```

2. **Add your Google Gemini API key:**
   ```bash
   # Edit backend/.env and add:
   GEMINI_API_KEY=your_api_key_here
   ```
   Get your API key from: https://ai.google.dev/

## Start the App

**Option 1 - Start both servers:**
```bash
./start-app.sh
```

**Option 2 - Start manually:**
```bash
# Terminal 1 (Backend)
./start-backend.sh

# Terminal 2 (Frontend) 
./start-frontend.sh
```

## Access the App

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage

1. Register a new account
2. Create notes - AI summaries auto-generate
3. Organize notes in notebooks  
4. Search your knowledge base

Press `Ctrl+C` to stop servers.
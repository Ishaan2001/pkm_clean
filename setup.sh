#!/bin/bash

echo "🚀 Setting up Knowledge Base PWA..."

# Backend setup
echo "Setting up backend..."
./install-backend.sh

# Frontend setup
echo "Setting up frontend..."
cd frontend
npm install
cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Add GEMINI_API_KEY to backend/.env"
echo "2. Run: ./start-app.sh"
echo ""
echo "Manual start:"
echo "• Backend: ./start-backend.sh" 
echo "• Frontend: ./start-frontend.sh"
#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "🔍 Starting Project Verification..."

# 1. Backend Verification
echo "🐍 Verifying Backend..."
cd api
# Ensure venv (optional, assuming user has one or system python)
# pip install -r requirements.txt > /dev/null 2>&1 || echo "⚠️  Warning: Pip install failed or skipped"
export PYTHONPATH=$PYTHONPATH:$(pwd)
pytest tests/
BACKEND_STATUS=$?
cd ..

if [ $BACKEND_STATUS -ne 0 ]; then
    echo "❌ Backend Tests Failed!"
    exit 1
fi
echo "✅ Backend Verified."

# 2. Frontend Verification
echo "⚛️  Verifying Frontend..."
cd frontend/dashboard
# Ensure deps
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Frontend Dependencies..."
    npm install
fi

# Run tests
npx vitest run
FRONTEND_STATUS=$?
cd ../..

if [ $FRONTEND_STATUS -ne 0 ]; then
    echo "❌ Frontend Tests Failed!"
    exit 1
fi
echo "✅ Frontend Verified."

echo "🎉 All Systems Go! Ready for Deployment."
exit 0

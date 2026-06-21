#!/bin/bash
# Linux/Mac Quick Start Script for CodeLens

echo ""
echo "======================================"
echo " CodeLens - Python Django Setup"
echo "======================================"
echo ""

# Get the script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_EXE="${DIR}/venv/bin/python"

# Create virtual environment if it doesn't exist
if [ ! -d "${DIR}/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Install dependencies
echo "Installing dependencies..."
$PYTHON_EXE -m pip install -r backend/requirements.txt

# Change to backend directory
cd backend

# Run migrations
echo "Setting up database..."
$PYTHON_EXE manage.py migrate

# Create superuser (optional)
read -p "Create superuser account? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    $PYTHON_EXE manage.py createsuperuser
fi

# Collect static files
echo "Collecting static files..."
$PYTHON_EXE manage.py collectstatic --noinput

# Start the server
echo ""
echo "======================================"
echo " Starting Django Development Server"
echo "======================================"
echo ""
echo "Access the application at: http://localhost:8000/"
echo "Django Admin at: http://localhost:8000/admin/"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

$PYTHON_EXE manage.py runserver

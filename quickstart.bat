@echo off
REM Quick Start Script for CodeLens Django Application
REM This script sets up and runs the application on Windows

echo.
echo ======================================
echo  CodeLens - Quick Start Setup
echo ======================================
echo.

REM Define path to virtual environment python relative to script location
set PYTHON_EXE="%~dp0venv\Scripts\python.exe"

REM Create virtual environment if it doesn't exist
if not exist "%~dp0venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Install dependencies (calling python -m pip to bypass absolute path launcher bugs)
echo.
echo Installing dependencies...
%PYTHON_EXE% -m pip install -r backend\requirements.txt

REM Change to backend directory
cd backend

REM Run migrations
echo.
echo Setting up database...
%PYTHON_EXE% manage.py migrate

REM Create superuser (optional)
echo.
echo Would you like to create a superuser account for Django admin? (Y/N)
set /p create_superuser=
if /i "%create_superuser%"=="Y" (
    %PYTHON_EXE% manage.py createsuperuser
)

REM Collect static files
echo.
echo Collecting static files...
%PYTHON_EXE% manage.py collectstatic --noinput

REM Start the server
echo.
echo ======================================
echo  Starting Django Development Server
echo ======================================
echo.
echo Access the application at: http://localhost:8000/
echo Django Admin at: http://localhost:8000/admin/
echo.
echo Press Ctrl+C to stop the server
echo.

%PYTHON_EXE% manage.py runserver

pause

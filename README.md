# CodeLens - AI-Powered Python Code Analysis with Django

A full-stack Django application for analyzing Python code with AI. Features include error detection, OOP concept identification, code smell detection, and refactoring suggestions.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- SQL Server (or SQLite for testing)
- ODBC Driver 17 for SQL Server (if using SQL Server)

### Installation

1. **Create Virtual Environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Database**
   
   Edit `codelens/settings.py`:
   
   For SQL Server:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'sql_server.pyodbc',
           'NAME': 'CodeLensDB',
           'USER': 'sa',
           'PASSWORD': 'YourPassword',
           'HOST': 'localhost',
           'PORT': 1433,
           'OPTIONS': {
               'driver': 'ODBC Driver 17 for SQL Server',
           },
       }
   }
   ```

   For SQLite (testing):
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.sqlite3',
           'NAME': BASE_DIR / 'db.sqlite3',
       }
   }
   ```

4. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Collect Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

7. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

   Visit: `http://localhost:8000/`

## 📁 Project Structure

```
django_project/
├── codelens/
│   ├── settings.py              # Django configuration & database
│   ├── urls.py                  # Main URL routing
│   ├── wsgi.py                  # WSGI application
│   ├── templates/               # HTML templates
│   │   ├── HomePage.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── functionalities.html
│   │   └── history.html
│   ├── static/                  # CSS & JavaScript
│   │   ├── css/
│   │   │   ├── HomePage.css
│   │   │   ├── loginsingnup.css
│   │   │   ├── functionalities.css
│   │   │   └── history.css
│   │   └── js/
│   │       ├── main.js
│   │       ├── functionalities.js
│   │       └── history.js
│   └── analyzer/                # Django app
│       ├── models.py            # Database models
│       ├── views.py             # View logic
│       ├── urls.py              # URL routing
│       ├── admin.py             # Admin configuration
│       └── migrations/          # Database schema
├── manage.py
├── requirements.txt
├── SETUP_GUIDE.txt
└── README.md
```

## ✨ Features

### 1. User Authentication
- **Sign Up**: Create new account with email and password
- **Login**: Secure authentication
- **User Profiles**: Track analysis statistics
- **Logout**: Secure session management

### 2. Code Analysis
- **Error Detection**: Identifies syntax errors and issues
- **OOP Analysis**: Detects classes, inheritance, methods
- **Code Smells**: Identifies magic numbers, long methods
- **Refactoring**: Suggests code improvements
- **File Upload**: Upload Python files for analysis

### 3. Analysis History
- **History Tracking**: View all previous analyses
- **Search & Filter**: Find specific analyses
- **Star/Favorite**: Mark important analyses
- **Pagination**: Browse through history
- **Soft Delete**: Remove analyses from history

### 4. Database Integration
- **SQL Server**: Enterprise-grade database
- **User Data**: Secure storage of user credentials
- **Analysis Storage**: Store code and results
- **History Management**: Track analysis metadata

## 🔌 URL Routes

### Authentication
- `GET  /` - Home page
- `GET  /login/` - Login page
- `POST /login/` - Process login
- `GET  /signup/` - Signup page
- `POST /signup/` - Process signup
- `GET  /logout/` - Logout user

### Analysis
- `POST /analyze/` - Analyze code (AJAX)
- `GET  /functionalities/` - View analysis results
- `GET  /history/` - View analysis history

### API Endpoints
- `GET  /api/analysis/<id>/` - Get analysis details
- `POST /api/analysis/<id>/star/` - Star/unstar analysis
- `POST /api/history/<id>/delete/` - Delete history entry

## 🎨 Frontend Features

### Interactive Pages
1. **Home Page** - Upload/paste Python code, click "Analyze"
2. **Login/Signup** - User authentication
3. **Results Page** - Tabbed interface showing:
   - Error Detection
   - OOP Concepts
   - Code Smells & Refactoring
4. **History Page** - Searchable list of all analyses

### JavaScript Interactivity
- **Form Submission**: AJAX code submission without page reload
- **Tab Navigation**: Click tabs to switch analysis results
- **File Upload**: Support for .py and .txt files
- **Delete Confirmation**: Confirm before deleting
- **Search Functionality**: Filter history by name/tags
- **Star Toggle**: Mark important analyses

## 🔐 Security

- CSRF Protection on all forms
- SQL Injection prevention via ORM
- Password hashing with Django auth
- Session management
- User data isolation

## 🛠 Development Commands

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver

# Run tests (when added)
python manage.py test

# Open Django shell
python manage.py shell
```

## 📊 Database Models

### UserProfile
- One-to-one relationship with User
- Tracks total analyses count
- Created/updated timestamps

### CodeAnalysis
- Stores submitted code
- Analysis results (errors, OOP, smells)
- Status tracking (pending/completed/error)
- User association

### AnalysisHistory
- Links to CodeAnalysis
- Custom titles and tags
- Star/favorite marking
- Soft delete support

## 🚨 Important Notes

### SQL Server Setup
1. Install ODBC Driver: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Create database manually in SQL Server Management Studio
3. Update `settings.py` with correct credentials

### Production Deployment
- Change `SECRET_KEY` in settings.py
- Set `DEBUG = False`
- Configure `ALLOWED_HOSTS`
- Use environment variables for secrets
- Set up proper logging
- Use a production database
- Deploy with Gunicorn/uWSGI

## 🐛 Troubleshooting

**ODBC Driver Not Found**
- Install "ODBC Driver 17 for SQL Server"
- Verify driver name in settings.py

**Database Connection Failed**
- Verify SQL Server is running
- Check username/password
- Ensure database exists
- Test connection via SQL Server Management Studio

**Static Files Not Loading**
- Run: `python manage.py collectstatic`
- Check nginx/Apache configuration in production

**Login Not Working**
- Verify user exists in database
- Check password
- Clear browser cache/cookies

## 📚 Resources

- Django Documentation: https://docs.djangoproject.com/
- Python: https://python.org/
- SQL Server ODBC: https://learn.microsoft.com/en-us/sql/connect/odbc/

## 📝 License

This project is created for educational purposes.

## 👨‍💻 Support

For issues or questions:
1. Check SETUP_GUIDE.txt
2. Review Django error messages
3. Check database connection settings
4. Verify SQL Server is running

---

**Last Updated**: March 2026
**Version**: 1.0
**Python**: 3.8+
**Django**: 4.2.8

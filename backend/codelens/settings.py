"""
Django settings for codelens project.
Configuration for SQL Server Database Connection
"""

import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',

    'codelens.analyzer',
]

SITE_ID = 1


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # allauth middleware
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'codelens.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR.parent, 'frontend', 'templates')],  # fix path here
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'codelens.wsgi.application'

# ========== DATABASE ==========
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Configured for Microsoft SQL Server Database Connection (Local Development)
    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': config('DB_NAME', default='CodeLensDB'),
            'USER': config('DB_USER', default='sa'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1\\SQLEXPRESS'),
            'PORT': config('DB_PORT', default='1433', cast=int),   # 1433 for SQL Express with TCP/IP enabled
            'OPTIONS': {
                'driver': 'ODBC Driver 17 for SQL Server',
                'extra_params': 'TrustServerCertificate=yes;Connection Timeout=15',
            },
            'CONN_MAX_AGE': 0,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR.parent, 'frontend', 'static'),
]

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login redirect settings
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# ========== AUTHENTICATION BACKENDS ==========
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ========== ALLAUTH CONFIG ==========
ACCOUNT_EMAIL_VERIFICATION = 'none'       # Skip email verification
ACCOUNT_LOGIN_ON_GET = True
ACCOUNT_USERNAME_REQUIRED = False         # Don't force a username on social signup
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True

SOCIALACCOUNT_AUTO_SIGNUP = True          # Skip the extra social signup form
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_EMAIL_REQUIRED = False      # Don't block if email scope not granted

# Auto-generate username from email (e.g. buttali2004@gmail.com → buttali2004)
SOCIALACCOUNT_ADAPTER = 'codelens.analyzer.adapters.SocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID', default=''),
            'secret': config('GOOGLE_CLIENT_SECRET', default=''),
            'key': '',
        },
    },
    'github': {
        'SCOPE': ['user:email'],
        'APP': {
            'client_id': config('GITHUB_CLIENT_ID', default=''),
            'secret': config('GITHUB_CLIENT_SECRET', default=''),
            'key': '',
        },
    },
}

# ========== PREMIUM DJANGO ADMIN DESIGN (JAZZMIN CONFIG) ==========
JAZZMIN_SETTINGS = {
    "site_title": "CodeLens Portal",
    "site_header": "CodeLens",
    "site_brand": "CodeLens",
    "site_logo": "img/logo_dark.png",
    "site_icon": "img/logo_dark.png",
    "login_logo": None,
    "login_logo_dark": None,
    "custom_css": "css/admin_custom.css",
    "welcome_sign": "Welcome to the CodeLens Control Panel",
    "copyright": "CodeLens Ltd",
    "search_model": ["auth.User"],
    "show_sidebar": True,
    "navigation_expanded": True,
    "show_ui_builder": False,
    "order_with_respect_to": ["auth", "account", "socialaccount", "analyzer"],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "account.EmailAddress": "fas fa-envelope",
        "socialaccount.SocialAccount": "fas fa-share-alt",
        "socialaccount.SocialApp": "fas fa-cubes",
        "socialaccount.SocialToken": "fas fa-key",
        "analyzer.AnalysisReport": "fas fa-chart-line",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index"},
        {"name": "Main App", "url": "home", "new_window": True},
        {"model": "auth.User"},
    ],
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-indigo",
    "accent": "accent-indigo",
    "navbar": "navbar-dark navbar-indigo",
    "no_navbar_border": True,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-indigo",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

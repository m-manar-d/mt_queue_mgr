"""
Django settings for mt_queue_mgr project.
"""

from pathlib import Path
import os
import dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

dotenv_file = os.path.join(BASE_DIR, ".env")
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

SECRET_KEY = os.environ['SECRET_KEY']

FW_ADDRESS_LIST = os.environ['FW_ADDRESS_LIST']

DEBUG = False

ALLOWED_HOSTS = ['*']

# Don't leave this value!! Edit as required!!
CSRF_TRUSTED_ORIGINS = ['https://*.ramtek.net.tr']

# Application definition
INSTALLED_APPS = [
    'limiters_global.apps.RoutersConfig',
    'routers_g1.apps.RoutersConfig',
    'routers_g2.apps.RoutersConfig',
    'routers_g3.apps.RoutersConfig',
    "log_viewer",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mt_queue_mgr.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [os.path.join(BASE_DIR, "templates"), ],
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

WSGI_APPLICATION = 'mt_queue_mgr.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': os.environ['DATABASE_HOST'],
        'PORT':'3306',
        "OPTIONS": {
            "database": os.environ['DATABASE_NAME'],
            "user": os.environ['DATABASE_USER'],
            "password": os.environ['DATABASE_PASSWORD'],
            "charset": os.environ['DATABASE_CHARSET'],
            "init_command": "SET default_storage_engine=INNODB",
        },
    }
}

# Password validation

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


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ['TIME_ZONE']

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = 'static/'

# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname}: {asctime} - {module} - {funcName}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        "console": {
            "class": "logging.StreamHandler",
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
        'logfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': BASE_DIR / 'log/mt_queue_mgr.log',
            'formatter': 'verbose',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 7,
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'mt_queue_mgr': {
            'handlers': ['logfile'],
            'level': os.environ['LOG_LEVEL'],
            'propagate': True,
        },
    }
}

# django-log-viewer config:
LOG_VIEWER_FILES = ['mt_queue_mgr.log']
LOG_VIEWER_FILES_PATTERN = '*.log*'
LOG_VIEWER_FILES_DIR = 'log/'
LOG_VIEWER_PAGE_LENGTH = 50       # total log lines per-page
LOG_VIEWER_MAX_READ_LINES = 1000  # total log lines will be read
LOG_VIEWER_FILE_LIST_MAX_ITEMS_PER_PAGE = 25 # Max log files loaded in Datatable per page
LOG_VIEWER_PATTERNS = ['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL']
LOG_VIEWER_EXCLUDE_TEXT_PATTERN = None  # String regex expression to exclude the log from line
LOG_VIEWER_FILE_LIST_TITLE = "Queue Limiters Log Viewer"
LOG_VIEWER_FILE_LIST_STYLES = "/static/log_viewer/css/log-viewer-custom.css"

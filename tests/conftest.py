import django
from django.conf import settings


def pytest_configure(*args):
    # pylint: disable=unused-argument
    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
            'secondary': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    'debug': True,  # We want template errors to raise
                },
            },
        ],
        MIDDLEWARE=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.staticfiles',
            'tests',
        ),
        PASSWORD_HASHERS=('django.contrib.auth.hashers.MD5PasswordHasher',),
    )

    django.setup()

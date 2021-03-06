# coding=utf-8
from __future__ import unicode_literals

import os
import sys
import socket

from django.core.exceptions import ImproperlyConfigured


try:
    # Python 2
    from future_builtins import filter
except ImportError:
    # Python 3
    pass

from os.path import join, realpath, exists, isfile
from django.utils.translation import ugettext_lazy as _

from configurations import Configuration, values
from dotenv import load_dotenv

from .config.base import DatabasesAppsSettings, MiddlewareSettings, TemplatesSettings
from .config.logging import LoggingSettings
from .config.email import SendMailSettings
from .config.secure import SecureSettings
from .config.sentry import SentrySettings
from .config.redis import RedisSettings, RedisCacheSettings, RedisBrokerSettings, RedisChannelLayersSettings
from .config.drf import DjangorestframeworkSettings


def get_app_path(name):
    """
    Implements the default strategy for finding a module's path automagically.
    => Picks up the first path in $PATH which contains the module with given name.
    """
    path = next(filter(lambda p: isfile(join(p, name)), sys.path), None)
    if not path:
        raise ImproperlyConfigured(
            "`django-quickconfigs` couldn't find your settings module using the default strategy. "
            "Please, explicitly set `PROJECT_ROOT` in your Django settings."
        )
    return realpath(path)


class DevConfigMixin(object):
    """
    Quick-start development settings - unsuitable for production
    See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/
    """

    # Turn all debug flags on
    DEV = True
    PROD = STAGING = not DEV
    HTTPS_ONLY = False

    # Turn off debug while imported by Celery with a workaround
    # See http://stackoverflow.com/a/4806384
    if "celery" in sys.argv[0]:
        DEBUG = False

    # SendMailSettings override
    DJANGO_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST = EMAIL_HOST_USER = EMAIL_HOST_PASSWORD = None


class StagingConfigMixin(object):
    """
    Testing before going production
    eg.

    class MyDjangoSettings(StagingConfigMixin, CommonConfig):
        pass

    """

    # env reset
    STAGING = True
    PROD = DEV = not STAGING
    HTTPS_ONLY = False

    # make few vars required starting with Staging
    REDIS_URL = values.Value(environ_required=True, environ_prefix=None)
    SENTRY_DSN = values.Value(environ_required=True, environ_prefix=None)


class ProdConfigMixin(StagingConfigMixin):
    """
    Production settings,
     inherit and upgrade the staging settings for production.
    """
    PROD = HTTPS_ONLY = True
    DEBUG = DEV = STAGING = not PROD


class CommonConfig(
    # SentrySettings,
    SecureSettings, DjangorestframeworkSettings,
    SendMailSettings, RedisCacheSettings, LoggingSettings,
    TemplatesSettings, MiddlewareSettings, DatabasesAppsSettings, Configuration
):
    """
    Basic Django configuration.
    Expects env vars in 'settings/env/*.env' of current project.
    eg.

    class MyDjangoSettings(CommonConfig):
        CODENAME = 'my'
        HOSTNAME = 'localhost'
        ROOT_URLCONF = 'my.urls'
        WSGI_APPLICATION = 'my.wsgi'
        ...
    """

    # @classmethod
    # def pre_setup(cls):
    #     super(Prod, cls).pre_setup()
    #     if something.completely.different():
    #         cls.DEBUG = True

    # -----------------------------------------------------------------------------------
    # Project definition
    # Encompasses, but NOT necessarily equals this Django project; specifically,
    # the PROJECT_* may point at paths including this project's frontends (eg. Angular),
    # mobile app, etc.
    #
    # PROJECT_ROOT  : Not necessarily base dir created by django-admin.py startproject
    # SETTINGS_ROOT : The Django main app with settings.py
    # DOTENV        : Cf. https://github.com/jazzband/django-configurations/issues/165
    # -----------------------------------------------------------------------------------

    # The anchor part that enables to fetch the ENV
    HOST = socket.gethostname().split('.')[0]
    DEFAULT_CODENAME = os.getenv('DJANGO_SETTINGS_MODULE').split('.')[0]
    DEFAULT_PROJECT_ROOT = get_app_path('%s/settings.py' % DEFAULT_CODENAME)
    SETTINGS_ROOT = join(str(DEFAULT_PROJECT_ROOT), DEFAULT_CODENAME)
    # DOTENV = join(SETTINGS_ROOT, 'env/.env')

    # look for `env/.env` of main Django app for common/default settings to load,
    # then attempt to load host-specific settings from env file named after the host
    # load_dotenv(dotenv_path=join(SETTINGS_ROOT, 'env/.env'), override=False)
    load_dotenv(dotenv_path=join(SETTINGS_ROOT, 'env/.env'), override=False)
    _dotenv = join(str(SETTINGS_ROOT), 'env/%s.env' % HOST)
    if exists(_dotenv):
        # avoiding `DOTENV = _dotenv`, which is lazy;
        # instead, using python-dotenv really sets up the env NOW
        # TODO: licensing server: https://github.com/theskumar/python-dotenv#setting-config-on-remote-servers
        load_dotenv(dotenv_path=_dotenv, override=True)

    # Project definition
    CODENAME = values.Value(DEFAULT_CODENAME, environ_required=True, environ_prefix=None)
    HOSTNAME = values.Value(HOST, environ_required=True, environ_prefix=None)

    # -----------------------------------------------------------------------------------
    # Directory Configuration
    # -----------------------------------------------------------------------------------

    # Custom paths, relative to PROJECT_ROOT
    # are used beyond the scope of this Django project
    PROJECT_ROOT = values.PathValue(DEFAULT_PROJECT_ROOT, check_exists=True, environ_prefix=None)
    PROJECT_LOGS_ROOT = values.PathValue(join(str(PROJECT_ROOT), 'logs'), check_exists=True, environ_prefix=None)
    PROJECT_LIBS_DIRS = values.ListValue([join(str(PROJECT_ROOT), 'libs')], environ_prefix=None)
    PROJECT_APPS_DIRS = values.ListValue([join(str(PROJECT_ROOT), 'apps')], environ_prefix=None)
    sys.path.extend(PROJECT_LIBS_DIRS.value)

    # Django paths, relative to PROJECT_ROOT
    LOCALE_PATHS = (join(str(PROJECT_ROOT), 'locale'),)
    FIXTURE_DIRS = (join(str(PROJECT_ROOT), 'fixtures'),)
    MEDIA_ROOT = join(str(PROJECT_ROOT), 'media')
    STATIC_ROOT = values.Value(join(realpath(str(PROJECT_ROOT)), 'sitestatic'))
    STATICFILES_DIRS = values.ListValue()
    TEMPLATES_ROOT = values.ListValue([join(str(PROJECT_ROOT), 'templates')], environ_prefix=None)

    # -----------------------------------------------------------------------------------
    # Django Application definition
    # Requires host name resolution set to /etc/hosts; eg. 127.0.0.1 localhost, l1-ceduth
    # -----------------------------------------------------------------------------------
    SITE_ID = 1
    SECRET_KEY = values.SecretValue()
    ROOT_URLCONF = values.Value(environ_required=True)
    WSGI_APPLICATION = values.Value(environ_required=True)
    DEBUG = values.BooleanValue(True, environ_prefix=None)
    DJANGO_LOG_LEVEL = values.Value('INFO', environ_prefix=None)
    INTERNAL_IPS = values.ListValue(['127.0.0.1'] + socket.gethostbyname_ex(HOST)[-1])
    ADMINS = values.SingleNestedTupleValue(('Support Group @TechOutlooks', 'support@techoutlooks.com'), )
    MANAGERS = ADMINS
    ALLOWED_HOSTS = values.ListValue([h for h in [HOSTNAME.value, 'localhost', '127.0.0.1'] if h])

    # ----------------------------------------------------------------------------------
    # URLs configuration
    # ----------------------------------------------------------------------------------
    MEDIA_URL = '/media/'
    STATIC_URL = '/sitestatic/'
    ADMIN_MEDIA_PREFIX = STATIC_URL + "admin/"
    LOGIN_REDIRECT_URL = "/"
    LOGIN_URL = "/users/login/"
    LOGOUT_REDIRECT_URL = "/"

    # ----------------------------------------------------------------------------------
    # Internationalization
    # https://docs.djangoproject.com/en/1.8/topics/i18n/
    # ----------------------------------------------------------------------------------
    LANGUAGE_CODE = 'en'
    TIME_ZONE = values.Value('Africa/Conakry')
    USE_I18N = True
    USE_L10N = True
    USE_TZ = True
    LANGUAGES = (
        ('fr', _('Français')),
        ('en', _('English')),
    )

    # List of finder classes that know how to find static files in
    # various locations.
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        # 'compressor.finders.CompressorFinder',
    )


default_app_config = 'quickconfigs.apps.SmartSettingsAppConfig'


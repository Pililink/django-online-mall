"""
Django settings for dailyfresh project.

Generated by 'django-admin startproject' using Django 3.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

#通过这个设置免去应用app模块时前面加入路径apps。如 apps.user.urls
sys.path.insert(0,str(BASE_DIR / 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'x55wdcdjbmklwd_#%j0q%z+4q6(7k=)2x+-qn0f)k)oxih*j^a'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tinymce',#富文本编辑器
    'apps.cart',#购物车模块
    'apps.goods',#商品模块
    'apps.order',#订单模块
    'apps.user'#用户模块
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

ROOT_URLCONF = 'dailyfresh.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'dailyfresh.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "dailyfresh",#数据库需要手动创建。
        'USER':'root',
        'PASSWORD':'2966',
        'HOST':'10.0.0.163',
        'PORT':3306,
    }
}




# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'zh-Hans'
TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'#静态文件访问路径
STATICFILES_DIRS = [BASE_DIR / 'static']#静态文件目录


#django认证系统使用的模型类
AUTH_USER_MODEL = 'user.User'


#富文本编辑器配置
TINYMCE_DEFAULT_CONFIG = {
    'theme': 'silver',
    'width': 600,
    'height': 400,
}

#配置邮箱
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = False #是否使用TLS安全传输协议(用于在两个通信应用程序之间提供保密性和数据完整性。)
EMAIL_USE_SSL = True #是否使用SSL加密，qq企业邮箱要求使用
EMAIL_HOST = 'smtp.qq.com'
EMAIL_PORT = 465
#发送邮件的邮箱
EMAIL_HOST_USER = 'xiaoqin2966@qq.com'
#在邮箱中设置的客户端授权密码
EMAIL_HOST_PASSWORD = 'iyfqdncqugcsfiic'
#收件人看到的发件人
EMAIL_FROM = 'dajngo_test<xiaoqin2966@qq.com>'

#配置django-redis 缓存信息
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://10.0.0.163:6379/9",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# django-redis sessions配置，将session存放到缓存中
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# 配系统登录地址
LOGIN_URL = '/user/login'

# 自定义django文件存储类

DEFAULT_FILE_STORAGE = 'utils.fdfs.storage.FDFSStorage'
import os
# 设置fdfs使用的client.conf文件绝对路径
FDFS_CLIENT_CONF = r'/Volumes/public_data/src/TTsx/dailyfresh/utils/fdfs/client.conf'
print(FDFS_CLIENT_CONF)
# 设置fdfs存储服务器上nginx的IP和端口号（默认8888）
FDFS_URL = r'http://10.0.0.163:8888/'
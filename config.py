import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True #每次请求结束后都会自动提交数据库中的变动
    FLASKY_MAIL_SUBJECT_PREFIX = '[filtme]'
    FLASKY_MAIL_SENDER = 'filtme2 admin <filtme2@163.com>'
    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN') or 'coreki@163.com'
    USER_AVATAR_DIR = 'user-avatar'
    GROUP_AVATAR_DIR = 'group-avatar'
    UPLOAD_POST_IMAGE_DIR = 'post-image'

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SERVER = 'smtp.163.com'
    MAIL_PORT = 25
    MAIL_USE_TLS = True
    MAIL_DEBUG = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'filtme2'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'm1314520'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir,'data-dev.sqlite')

class TestingConfig(Config):
    TESTINT = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir,'data-test.sqlite')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir,'data.sqlite')

config = {
    'development':DevelopmentConfig,
    'testing':TestingConfig,
    'production':ProductionConfig,

    'default':DevelopmentConfig
}


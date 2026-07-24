import pymysql
pymysql.install_as_MySQLdb()

# 导入Celery应用实例
# 确保Django启动时加载Celery
from .celery import app as celery_app

__all__ = ('celery_app',)
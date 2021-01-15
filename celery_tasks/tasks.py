# 使用celery
from django.core.mail import send_mail
from django.conf import settings
from celery import Celery
import time

# 在任务处理者一端加这几句
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()

# 创建一个Celery类的实例对象
# 第一个参数可以自定义。但是一般使用导包路径做完这个的名字
# 第二个参数borker指定中间人
app = Celery('celery_tasks.tasks', broker='redis://10.10.10.10:6379/8')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    print(token)
    print(to_email)
    print(username)
    '''发送激活邮件'''
    action_url = 'http://127.0.0.1:8000/user/action/' + token
    msg = '''
            <h1>%s,欢迎您的注册,请在一天内完成激活。</h1>
            请点击下方的的按钮进行注册<br>
            <a href="%s" target="_blank">点击激活</a>
            ''' % (username, action_url)

    send_mail('注册激活','',settings.EMAIL_FROM,[to_email],html_message=msg)

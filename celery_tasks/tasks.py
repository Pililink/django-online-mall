# 使用celery
from django.core.mail import send_mail
from django.conf import settings
from celery import Celery
from django.template import loader, RequestContext

import time,os

# 在任务处理者一端加这几句
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()

#celery -A celery_tasks.tasks worker -l INFO


# 创建一个Celery类的实例对象
# 第一个参数可以自定义。但是一般使用导包路径做完这个的名字
# 第二个参数borker指定中间人
app = Celery('celery_tasks.tasks', broker='redis://10.0.0.200:6379/8')
# !!!注意在celery中使用django的模型类，需要在环境初始化之后才能导入包!!!
from apps.goods.models import *

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

@app.task
def generate_static_index_html():
    '''产生首页静态页面'''
    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners


    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}

    # 使用模板
    # 1.加载模板文件,返回模板对象
    temp = loader.get_template('celery_static/static_index.html')
    # 2.模板渲染
    static_index_html = temp.render(context)

    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)
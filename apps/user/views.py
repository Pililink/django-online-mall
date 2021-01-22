from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.views.generic import View
from apps.user.models import User,Adderss
from apps.goods.models import GoodsSKU

# 导入django内置用户认证模块
from django.contrib.auth import authenticate, login, logout

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from dailyfresh.settings import SECRET_KEY
import re

from celery_tasks.tasks import send_register_active_email

#登录状态判断Mixin
from utils.mixin import LoginRequiredMixin

from django_redis import get_redis_connection

# Create your views here.

'''
django3 的验证系统官方文档
https://docs.djangoproject.com/zh-hans/3.1/topics/auth/default/
'''

# /user/register
class RegisterView(View):
    '''注册功能的类视图'''

    def get(self, request):
        '''显示页面'''
        return render(request, 'register.html')

    def post(self, request):
        '''进行注册处理'''
        '''注册处理方法'''
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 数据校验
        if allow != 'on':
            # 没有选接受协议
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        if not all([username, password, email]):  # 使用all方法，给all方法中传递一个可迭代对象，如果都为真时返回 真
            # 数据不完整时
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            # 邮箱不合法
            return render(request, 'register.html', {'errmsg': '邮箱不合法，格式不正确'})
        # 校验用户是否已存在
        try:
            User.objects.get(username=username)
            user = True  # 表示已存在
        except User.DoesNotExist as err:
            # 抛错时表示用户名不存在
            user = False  # 表示不存在
        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 进行业务处理（进行用户注册）
        user = User.objects.create_user(username=username, password=password, email=email)
        user.is_active = 0  # 注册完成后默认不激活
        user.save()

        # 发送激活邮件，包含激活连接:http://127.0.0.1:8000/user/action/
        ## 激活连接中需要包含用户的信息，并且需要进行加密


        serializer = Serializer(SECRET_KEY, 3600)  # 一小时后失效
        dumps_user_token = {'confirm': user.id}
        dumps_user_token = serializer.dumps(dumps_user_token)
        dumps_user_token = str(dumps_user_token, encoding='utf-8')
        # 通过异步方式发送邮件
        send_register_active_email.delay(username = user.username,to_email = user.email , token=dumps_user_token)

        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))


# /user/active/123123123
class ActiveView(View):
    '''用户激活'''

    def get(self, request, token):
        '''进行用户激活'''
        # 解密
        serializer = Serializer(SECRET_KEY, 3600)  # 一小时后失效
        try:
            loads_user_token = serializer.loads(token)  # 进行解密
            # 获取解密过后的信息
            user_id = loads_user_token['confirm']

            # 通过用户id 读取数据库中的用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            # 返回应答
            # return HttpResponse('%s,恭喜您激活成功'%user.username)
            # 返回等登陆界面
            return redirect(reverse('user:login'))

        except SignatureExpired as error:
            # 激活链接无效
            return HttpResponse("激活链接无效")

# /user/login
class LoginView(View):
    '''登陆'''

    def get(self, request):
        '''显示登陆界面'''
        #判断是否记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ""
            checked = ""
        return render(request, 'login.html',{'username':username,'checked':checked})
    def post(self,request):
        '''登录校验'''

        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        # 校验身份
        if not all([username, password]):
            return render(request,'login.html',{'errmsg':'数据不完整'})

        #user = User.objects.get(username=username,password=password)
        ## 通过django内置用户认证方法进行认证
        user = authenticate(username=username,password=password)
        print(user)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 已激活用户
                # 记录用户的登录状态:使用django内置的登录方法，会将登录的信息保存到session中
                login(request,user)

                #获取登录页面中地址后面的next内容，默认值设为系统主页
                next_url = request.GET.get('next',reverse('goods:index'))
                # 创建一个HttpResponseRedirect对象，方便之后添加cookie信息
                response = redirect(next_url)


                # 判断 是否记住 用户名
                remember = request.POST.get('remember')
                if remember =='on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')
                # 获取所需要跳转到地址信息
                # 返回应答
                return response
            else:
                # 未激活用户
                return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})

# /user/logout
class LogoutView(View):
    def get(self,request):
        '''退出用户'''
        #清楚用户的session信息
        logout(request)
        return redirect(reverse("goods:index"))


#/user
class UserInfoView(LoginRequiredMixin,View):
    '''用户信息-信息页'''
    def get(self,request):

        # 如果用户没有登录 request.user 是AnonymousUser类的一个实例,is_authenticated返回False
        # 如果用户登录 request.user 是User类的一个实例,is_authenticated返回True
        # request.user.is_authenticated()
        # 在django中除了自己设定的模板变量之外，django还会把request.user也传给模板文件（名字为user）



        # 获取用户的个人信息
        # 获取对应的user对象
        user = request.user
        address = Adderss.objects.get_default_address(user=user)

        # 获取用户的历史浏览记录
        # 从redis数据库中获取浏览记录
        con = get_redis_connection('default')
        history_key = 'history_%d'%user.id
        sku_ids = con.lrange(history_key,0,4)#取前五个
        # 获取前五个浏览记录中的商品信息
        # 遍历查询，以便保持对应的位置
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下问
        context= {
            'page':"user",
            'address':address,
            "goods_li":goods_li
        }

        return render(request,'user/user_center_info.html',context)

#/user/order
class UserOrderView(LoginRequiredMixin,View):
    '''用户信息-订单页'''
    def get(self,request):

        # 获取用户的订单信息

        return render(request,'user/user_center_order.html',{'page':"order"})

#/user/address
class UserAddressView(LoginRequiredMixin,View):
    '''用户信息-地址页'''
    def get(self,request):
        # 获取对应的user对象
        user = request.user
        # 获取用户的默认受收获地址
        address = Adderss.objects.get_default_address(user=user)

        return render(request,'user/user_center_site.html',{'page':"address",'address':address})

    def post(self,request):
        '''地址添加'''
        #接受数据
        receiver = request.POST.get('reveiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        #校验数据
        if not all([receiver,addr,phone]):
            return render(request,'user/user_center_site.html',{'page':"address",'errmsg':'数据不完整'})
        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$',phone):
            return render(request, 'user/user_center_site.html', {'page': "address", 'errmsg': '手机号格式错误'})

        #添加地址
        #如果用户已存在默认收获地址则添加的收货地址设为默认，否则新添加的收货地址不设为默认地址

        #获取对应的user对象
        user = request.user
        address = Adderss.objects.get_default_address(user=user)

        if address:
            is_default = False
        else:
            is_default = True

        # 创建地址
        Adderss.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default
                               )

        #返回应答，刷新地址页面
        return redirect(reverse('user:address'))

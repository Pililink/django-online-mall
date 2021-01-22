
from django.urls import path
from apps.user.views import *
#内置的登录状态判断 装饰器
from django.contrib.auth.decorators import login_required
urlpatterns = [
    path('register/',RegisterView.as_view(),name='register'), #指向 用户注册 类视图处理方法
    path('login/',LoginView.as_view(),name='login'), #指向 用户登陆 类视图处理方法
    path('action/<str:token>',ActiveView.as_view(),name='active'), #指向 用户激活 类视图处理方法

    path('logout',LogoutView.as_view(),name='logout'),# 退出系统
    #path('address/',login_required(UserAddressView.as_view()),name='address'),# 用户中心地址页
    #path('order/',login_required(UserOrderView.as_view()),name='order'),# 用户中心订单页
    #path('',login_required(UserInfoView.as_view()),name='user')# 用户中心信息页

    path('address/',UserAddressView.as_view(),name='address'),# 用户中心地址页
    path('order/',UserOrderView.as_view(),name='order'),# 用户中心订单页
    path('',UserInfoView.as_view(),name='user')# 用户中心信息页
]

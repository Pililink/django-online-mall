from django.urls import path
from apps.order.views import *
urlpatterns = [
    path(r'place',OrderPlaceView.as_view(),name='place'), #提交订单页面
    path(r'commit',OrderCommiteView.as_view(),name='commit'), #订单创建
    path(r'pay',OrderPayView.as_view(),name='pay'), #订单支付
    path(r'chack',CheckPayView.as_view(),name='chack'), #订单支付状态查询
    path(r'comment/<int:id>',ConnentView.as_view(),name='comment'), #订单评论
]

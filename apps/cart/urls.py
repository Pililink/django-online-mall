from .views import *
from django.urls import path

urlpatterns = [
    path(r'add/',CartAddView.as_view(),name='add'),#购物车添加
    path(r'update/',CartUpdateView.as_view(),name='update'),#购物车记录更新
    path(r'delete/',CartDeleteView.as_view(),name='delete'),#购物车记录删除
    path(r'',CartInfoView.as_view(),name='info'),#购物车详情页
]

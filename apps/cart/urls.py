from .views import *
from django.urls import path

urlpatterns = [
    path(r'add/',CartAddView.as_view(),name='add'),#购物车天机
]

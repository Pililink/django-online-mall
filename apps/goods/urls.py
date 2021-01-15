
from django.urls import path
from apps.goods import views
urlpatterns = [
    path(r'index/',views.index,name = 'index'),
    path(r'',views.index,name = 'index'),


]


from django.urls import path
from apps.goods import views
urlpatterns = [
    path(r'index/',views.IndexView.as_view(),name = 'index'),
    path(r'detail/<int:sku_id>/',views.DateilView.as_view(),name='detail'),
    path(r'list/<int:type_id>/<int:page>/',views.ListView.as_view(),name='list')

]

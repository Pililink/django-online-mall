
from django.urls import path
from apps.goods import views
urlpatterns = [
    path(r'index/',views.IndexView.as_view(),name = 'index'),

]


from django.urls import path
from apps.order.views import *
urlpatterns = [
    path(r'place',OrderPlaceView.as_view(),name='place'),
    path(r'commit',OrderCommiteView.as_view(),name='commit')
]

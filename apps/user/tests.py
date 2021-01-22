from django.test import TestCase
from apps.user.models import *
# Create your tests here.
user = User.objects.all()[0]
Adderss.objects.create(user=user,
                       receiver="asdasdasdasd",
                       addr="address",
                       zip_code="123123",
                       phone="phone",
                       is_default=True
                       )
from django.contrib import admin
from .models import *
# Register your models here.
class BaseAdmin(admin.ModelAdmin):
    pass
@admin.register(User)
class GoodsTypeAdmin(BaseAdmin):
    pass
@admin.register(Address)
class GoodsTypeAdmin(BaseAdmin):
    pass
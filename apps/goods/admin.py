from django.contrib import admin
from celery_tasks.tasks import generate_static_index_html
from .models import *
# Register your models here.

#重写模型管理方法，使得在对数据库操作时执行指定命令
#doc: https://docs.djangoproject.com/zh-hans/3.1/ref/contrib/admin/
class BaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''重写save方法，加上保存后要执行的语句'''
        super().save_model(request, obj, form, change)
        # 发出任务让celety worker重写生成首页静态
        generate_static_index_html.delay()

    def delete_model(self,request,obj):
        '''重写delete方法，加上删除表中数据后的语句'''
        super().delete_model(request,obj)
        # 发出任务让celety worker重写生成首页静态
        generate_static_index_html.delay()






admin.site.register(GoodsType)
admin.site.register(GoodsSKU)
admin.site.register(Goods)
admin.site.register(GoodsImage)

admin.site.register(IndexGoodsBanner)
admin.site.register(IndexTypeGoodsBanner)
admin.site.register(IndexPromotionBanner,BaseAdmin)
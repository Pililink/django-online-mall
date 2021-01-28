from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
# Create your views here.

#/cart/add
class CartAddView(View):
    '''购物车添加视图'''
    def post(self,request):
        '''
        前端使用ajax的方式访问
        '''
        user = request.user
        if not user.is_authenticated:
            #用户未登录
            return JsonResponse({'res':1,'error':'请登录'})
        #接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        #数据校验
        if not all([sku_id,count]):
            return JsonResponse({'res':2,'error':'数据不完整'})
        # 校验添加商品的数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'error': '商品数目出错'})
        #校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id = sku_id)
        except Exception as a:
            return JsonResponse({'res': 4, 'error': '商品不存在'})
        #添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        cart_count = conn.hget(cart_key,sku.id)#没有记录时返回none
        if cart_count:
            #累加数目
            count += int(cart_count)

        #校验库存
        if count >sku.stock:
            return JsonResponse({'res': 5, 'error': '商品库存不足'})

        #设置redis中的记录。没有的话新增数据，有的话则修改。
        conn.hset(cart_key,sku_id,count)
        #计算商品条目数
        total_count = conn.hlen(cart_key)
        #返回页面
        return JsonResponse({'res': 0, 'message': '添加成功','total_count':total_count})
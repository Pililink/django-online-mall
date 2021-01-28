from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
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


#/cart
class CartInfoView(LoginRequiredMixin,View):
   '''购物车页面显示'''
   def get(self,request):
       '''显示购物车页面'''
       #获取登录的用户
       user = request.user
       #获取购物车内容
       conn = get_redis_connection('default')
       cart_key = 'cart_%d'%user.id
       cart_dict = conn.hgetall(cart_key)#{'商品id'：数量}

       #遍历商品的字典，获取商品的信息
       skus=[] #记录购物车中的所有商品信息
       total_count=0 # 记录总数目
       total_price=0 # 记录总价格
       for sku_id,count in cart_dict.items():
           #通过id找到商品信息
           sku = GoodsSKU.objects.get(id = sku_id)
           #计算商品的小计
           amount = sku.price * int(count)
           #动态给sku添加属性amount来记录小计的值
           sku.amount = amount
           #动态给sku添加属性count，来记录购买的数量
           sku.count=int(count)
           skus.append(sku)
           total_price += amount
           total_count += int(count)

       #组织上下文
       context = {
           'total_count':total_count,
           'total_price':total_price,
           'skus':skus
       }
       return render(request,'cart/cart.html',context)


#更新购物车信息
#采用ajax post方式,接收商品id和数量
#/cart/update
class CartUpdateView(View):
    '''购物车记录更新'''
    def post(self,request):
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 1, 'error': '请登录'})
        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 2, 'error': '数据不完整'})
        # 校验添加商品的数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'error': '商品数目出错'})
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception as a:
            return JsonResponse({'res': 4, 'error': '商品不存在'})

        # 添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 校验库存
        if count > sku.stock:
            return JsonResponse({'res': 5, 'error': '商品库存不足'})
        cart_count = conn.hset(cart_key, sku.id,count)  # 没有记录时返回none

        # 设置redis中的记录。没有的话新增数据，有的话则修改。
        conn.hset(cart_key, sku_id, count)

        # 计算用户购物车中商品的总件数
        vals = conn.hvals(cart_key)
        total = 0
        for value in vals:
            total += int(value)
        print(total)
        # 返回页面
        return JsonResponse({'res': 0, 'message': '更新成功','total':total})

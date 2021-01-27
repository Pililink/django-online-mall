from django.shortcuts import render,redirect
from django.urls import reverse
from django.views.generic import View
from apps.goods.models import *
from apps.order.models import OrderGoods
from django_redis import get_redis_connection
from django.core.cache import cache
from django.core.paginator import Paginator
# Create your views here.

# /index
class IndexView(View):
    '''首页'''
    def get(self, request):
        '''显示首页'''
        # 配置页面缓存
        # https://docs.djangoproject.com/zh-hans/3.1/topics/cache/#%E5%BA%95%E5%B1%82%E7%BC%93%E5%AD%98API

        # 读取缓存
        context = cache.get('index_page_data')
        if context is None:
            # 缓存中没有数据
            # 获取商品的种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            for type in types: # GoodsType
                # 获取type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners
            context = {'types': types,
                       'goods_banners': goods_banners,
                       'promotion_banners': promotion_banners
                       }
            # 添加缓存
            cache.set('index_page_data',context,3600)
        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            # 读取 用户购物车数量
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文

        context.update(cart_count=cart_count)

        # 使用模板
        return render(request, 'index.html', context)


# /detail/<int>
class DateilView(View):
    '''商品详情页'''
    def get(self,request,sku_id):
        '''显示详情页'''
        try:
            sku = GoodsSKU.objects.get(id = sku_id)
        except GoodsSKU.DoesNotExist:
            #商品不存在
            return redirect(reverse('goods:index'))
        # 获取商品的种类信息
        types = GoodsType.objects.all()
        # 获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment = '')
        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type = sku.type).order_by('-create_time')[:2]
        # 获取同一sku其他规格的商品
        sane_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku.id)
        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            # 添加浏览记录
            conn = get_redis_connection('default')
            history_key = "history_%d"%user.id
            # 移除已存在的商品id
            conn.lrem(history_key,0,sku_id)
            # 将商品id插入到列表的左边
            conn.lpush(history_key,sku_id)
            # 只保存最新的五条最近浏览
            conn.ltrim(history_key,0,4)


        # 组织模板上下文
        context = {
            'sku':sku,
            'types':types,
            'sku_orders':sku_orders,
            'new_skus':new_skus,
            'cat_count':cart_count,
            'sane_spu_skus':sane_spu_skus
        }
        return render(request,'goods/detail.html',context)


# /list/种类id/页码?sort=排序方式
# 种类id 页码 排序方式
class ListView(View):
    '''列表页面'''
    def get(self,request,type_id,page):
        '''显示列表页'''
        #获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            #不存在
            return redirect(reverse('goods:index'))

        #获取商品的分类信息
        types = GoodsType.objects.all()

        #获取排序方式
        #sort=default,默认按照添加时间
        #sort=price,按照商品价格排序
        #sort=hot,按照销量排序
        sort = request.GET.get('sort')
        #获取分类商品的信息
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-update_time')

        #对数据进行分页
        #https://docs.djangoproject.com/zh-hans/3.1/topics/pagination/
        paginater = Paginator(skus,1)
        # 获取第paginater的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1
        # 判断是否超出范围
        if page > paginater.num_pages:
            page=1
        if page < 1 :
            page = 1

        #获取指定页的内容
        skus_page = paginater.page(page)
        # 控制页面上最多显示五个页码
        #1 总页数小于五页，页码显示所有页码
        #2 当前页是前三页，显示1-5页
        #3 当前页是后三页，显示后五页
        #4 其他，显示当前页的前两页和后两页
        num_pages = paginater.num_pages
        if num_pages<5:
            pages = range(1,num_pages+1)
        elif page <=3:
            pages = range(1,6)
        elif num_pages-page<=2:#后三页
            pages = range(num_pages-4,num_pages+1)
        else:
            pages = range(page-2,page+3)



        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]
        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        #组织上下文
        print(skus)
        context = {
            'type':type,
            'types':types,
            'skus_page':skus_page,
            'new_skus':new_skus,
            'cart_count':cart_count,
            'sort':sort,
            'pages':pages
        }

        return render(request,'goods/list.html',context)
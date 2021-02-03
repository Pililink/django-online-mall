from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from apps.user.models import Address
from apps.order.models import OrderInfo,OrderGoods
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
from datetime import datetime
from django.db import transaction
# Create your views here.
#显示订单
#/order/place
class OrderPlaceView(LoginRequiredMixin,View):
    def post(self,request):
        '''提交订单页面'''
        #获取登录的用户信息
        user = request.user
        #获取参数
        sku_ids = request.POST.getlist('sku_ids')
        #校验数据
        if not sku_ids:
            #数据为空跳转购物车页面
            return redirect(reverse('cart:info'))
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id


        #遍历sku_ids，获取用户购买商品的信息
        skus=[]

        total_count=0 #保存总件数
        total_price=0 #保存总价格
        for sku_id in sku_ids:
            #根据商品的id获取商品信息
            sku = GoodsSKU.objects.get(id = sku_id)
            #获取用户所要购买的数量
            count = conn.hget(cart_key,sku_id)
            #计算商品小计
            amount = sku.price*int(count)
            #动态给sku增加属性count，保存购买数量.amount保存商品小计
            sku.count = int(count)
            sku.amount = amount
            skus.append(sku)
            total_count += int(count)
            total_price += amount
        #运费.因独立一个app操作运费
        transit_price = 10
        #实付款
        total_pay = total_price+transit_price
        #收货地址
        address = Address.objects.filter(user=user)

        sku_ids=','.join(sku_ids)
        #定义上下文
        context= {
            'skus':skus,
            'total_count':total_count,
            'total_price':total_price,
            'transit_price':transit_price,
            'total_pay':total_pay,
            'address':address,
            'sku_ids':sku_ids
        }
        return render(request,'order/place_order.html',context)

#创建订单
#/order/commit
#接收地址（addr_id）、支付方式(pey_method)、后买商品id字符串(sku_ids)
#django模型类事务文档：https://docs.djangoproject.com/zh-hans/3.0/topics/db/transactions/

class OrderCommiteView1(View):
    @transaction.atomic
    def post(self,request):
        '''订单创建'''
        #判断用户是否登录
        user=request.user
        if not user.is_authenticated:
            #用户未登录
            return JsonResponse({'res': 1, "error": '用户未登录'})

        #接收数据
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        print(addr_id,pay_method,sku_ids)
        #校验参数
        if not all([addr_id,pay_method,sku_ids]):
            return JsonResponse({'res': 2, "error": '参数错误'})
        #校验支付方式
        if pay_method not in OrderInfo.PAY_METHOD.keys():
            return JsonResponse({'res': 3, "error": '支付方式错误'})
        #校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 4, "error": '地址有误'})
        #todo：创建订单（核心业务）

        #组织参数
        #订单id:年分秒+用户id：2021020213205601
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        #运费
        transit_price = 10
        #总数目和总金额
        total_count = 0
        total_price = 0

        #设置事务保存点
        save_id = transaction.savepoint()
        try:
            # 创建订单信息表中添加内容
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price
            )
            #创建订单商品表
            sku_ids = sku_ids.split(',')
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            for sku_id in sku_ids:
                #获取商品信息
                try:
                    #select_for_update()相当于给这个查询加了个锁。悲观锁
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except:
                    #商品不存在
                    transaction.savepoint_rollback(save_id)#回滚保存点
                    return JsonResponse({'res': 5, "error": '商品信息错误'})
                #从redis中获取用户购买商品的数量
                count = conn.hget(cart_key,sku_id)
                #判断库存
                if int(count)> sku.stock:
                    transaction.savepoint_rollback(save_id)#回滚保存点
                    return JsonResponse({'res': 6, "error": '商品库存不足'})
                # 创建一个订单商品表
                OrderGoods.objects.create(
                    order=order,
                    sku = sku,
                    count=count,
                    price=sku.price
                )
                # 更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                # 累加订单商品的总数和总价
                amount = sku.price*int(count)
                total_count += int(count)
                total_price += amount

            #更新订单信息表中的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price

            order.save()
        except Exception as e:
            print(e)
            transaction.savepoint_rollback(save_id)  # 回滚保存点
            return JsonResponse({'res': 7, "error": "下单失败"})
        #提交事务
        transaction.savepoint_commit(save_id)
        #更新购物车中的信息
        conn.hdel(cart_key,*sku_ids)

        #返回应答
        return JsonResponse({'res': 0, "msg": '创建成功'})


class OrderCommiteView(View):
    @transaction.atomic
    def post(self, request):
        '''订单创建'''
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 1, "error": '用户未登录'})

        # 接收数据
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        print(addr_id, pay_method, sku_ids)
        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 2, "error": '参数错误'})
        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHOD.keys():
            return JsonResponse({'res': 3, "error": '支付方式错误'})
        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 4, "error": '地址有误'})
        # todo：创建订单（核心业务）

        # 组织参数
        # 订单id:年分秒+用户id：2021020213205601
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        # 运费
        transit_price = 10
        # 总数目和总金额
        total_count = 0
        total_price = 0

        # 设置事务保存点
        save_id = transaction.savepoint()
        try:
            # 创建订单信息表中添加内容
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price
            )
            # 创建订单商品表
            sku_ids = sku_ids.split(',')
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            for sku_id in sku_ids:
                for i in range(3):
                    # 获取商品信息
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except:
                        # 商品不存在
                        transaction.savepoint_rollback(save_id)  # 回滚保存点
                        return JsonResponse({'res': 5, "error": '商品信息错误'})
                    # 从redis中获取用户购买商品的数量
                    count = conn.hget(cart_key, sku_id)
                    # 判断库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)  # 回滚保存点
                        return JsonResponse({'res': 6, "error": '商品库存不足'})
                    # 更新商品的库存和销量
                    # 乐观锁,查询时不加锁，但是在更新数据时判断一下要修改的值是否和之前一样。
                    # update df_goods_sku set stock=0,sales=1 where id=17 and stock=1;
                    # 更新库存为零的时候判断一下之前是否为1
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)
                    print('user:%d times:%d stock:%d'%(user.id,i,sku.stock))
                    # import time
                    # time.sleep(10)
                    # update df_goods_sku set stock=new_stock,sales=new_sales
                    # where id=sku_id and stock=orgin_stock
                    # 返回受影响的行数,此处只会返回一个信息。结果不是0则是1
                    res = GoodsSKU.objects.filter(id=sku_id,stock=orgin_stock).update(stock=new_stock,
                                                                                sales=new_sales)
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(save_id)  # 回滚保存点
                            return JsonResponse({'res': 7, "error": '下单失败。'})
                        continue
                    # 创建一个订单商品表
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )
                    # 累加订单商品的总数和总价
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount
                    break

            # 更新订单信息表中的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price

            order.save()
        except Exception as e:
            print(e)
            transaction.savepoint_rollback(save_id)  # 回滚保存点
            return JsonResponse({'res': 8, "error": "下单失败"})
        # 提交事务
        transaction.savepoint_commit(save_id)
        # 更新购物车中的信息
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 0, "msg": '创建成功'})
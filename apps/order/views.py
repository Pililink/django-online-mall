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

from alipay import AliPay, DCAliPay, ISVAliPay
from alipay.utils import AliPayConfig

from django.conf import settings
import os,time

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
                   # print('user:%d times:%d stock:%d'%(user.id,i,sku.stock))
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


#订单支付
#/order/pay
class OrderPayView(View):

    def post(self,request):
        '''订单支付'''
        #判断登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':1,'error':'用户未登录'})
        #接收参数
        order_id = request.POST.get('order_id')
        #校验参数
        if not order_id:
            return JsonResponse({'res': 2, 'error': '订单无效'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 3, 'error': '订单无效'})
        #业务处理，调用支付接口
        # 配置地址
        app_private_path = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        alipay_public_path = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')
        app_private_key_string = open(app_private_path).read()
        alipay_public_key_string = open(alipay_public_path).read()

        alipay = AliPay(
            appid="2021000117608619",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True,  # 默认False
            verbose = False,  # 输出调试数据
            config = AliPayConfig(timeout=15)  # 可选, 请求超时时间
        )

        # 如果你是 Python 3的用户，使用默认的字符串即可
        subject = "天天生鲜："+order_id

        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject=subject,
            return_url="https://example.com",
            notify_url="https://example.com/notify"  # 可选, 不填则使用默认notify url
        )


        #返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 0, 'pay_url': pay_url})


#查询订单支付状态
#/order/check
class CheckPayView(View):
    '''查看订单支付的结果'''
    def post(self, request):
        '''查询支付结果'''
        # 判断登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 1, 'error': '用户未登录'})
        # 接收参数
        order_id = request.POST.get('order_id')
        # 校验参数
        if not order_id:
            return JsonResponse({'res': 2, 'error': '订单无效'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 3, 'error': '订单无效'})
        # 业务处理，调用支付接口
        # 配置地址
        app_private_path = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        alipay_public_path = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')
        app_private_key_string = open(app_private_path).read()
        alipay_public_key_string = open(alipay_public_path).read()

        alipay = AliPay(
            appid="2021000117608619",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True,  # 默认False
            verbose=False,  # 输出调试数据
            config=AliPayConfig(timeout=15)  # 可选, 请求超时时间
        )

        # 调用支付宝的交易查询接口
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # response = {
            #         "trade_no": "2017032121001004070200176844", # 支付宝交易号
            #         "code": "10000", # 接口调用是否成功
            #         "invoice_amount": "20.00",
            #         "open_id": "20880072506750308812798160715407",
            #         "fund_bill_list": [
            #             {
            #                 "amount": "20.00",
            #                 "fund_channel": "ALIPAYACCOUNT"
            #             }
            #         ],
            #         "buyer_logon_id": "csq***@sandbox.com",
            #         "send_pay_date": "2017-03-21 13:29:17",
            #         "receipt_amount": "20.00",
            #         "out_trade_no": "out_trade_no15",
            #         "buyer_pay_amount": "20.00",
            #         "buyer_user_id": "2088102169481075",
            #         "msg": "Success",
            #         "point_amount": "0.00",
            #         "trade_status": "TRADE_SUCCESS", # 支付结果
            #         "total_amount": "20.00"
            # }

            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()
                # 返回结果
                return JsonResponse({'res': 0, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                # 业务处理失败，可能一会就会成功
                import time
                time.sleep(5)
                continue
            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


#订单评论
class ConnentView(View):
    def get(self,request,id):
        user = request.user
        #校验数据
        if not id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id =id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))
        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count*order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order/order_comment.html", {"order": order})


    def post(self, request, id):
        """处理评论内容"""
        user = request.user
        # 校验数据
        if not id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i) # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '') # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5 # 已完成
        order.save()

        return redirect(reverse("user:order", kwargs={"page": 1}))






















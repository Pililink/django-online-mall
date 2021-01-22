from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel
# Create your models here.

class User(AbstractUser,BaseModel):
    '''用户模型类'''

    class Meta:
        db_table = "df_user"
        verbose_name = "用户"
        verbose_name_plural  = verbose_name


class AddressManager(models.Manager):
    '''地址模型管理类'''
    # 改变原有的查询的结果集
    def all(self):
        '''获取所有没有被删除的地址信息'''
        address = self.filter(is_delete=False)
        return address
    # 封装新的方法,用于操作模型类对应的数据包

    def get_default_address(self,user):
        # self.model 获取self所在的模型类
        '''获取用户的默认收获地址'''
        try:
            address = self.get(user=user,is_default=True)
            # 加密手机号
            address.phone = address.phone.replace(address.phone[3:7], '****')
        except self.model.DoesNotExist:
            # 没有默认地址
            address = None
        return address

class Adderss(BaseModel):
    '''地址模型类'''
    user = models.ForeignKey('User',verbose_name='所属账户', on_delete=models.DO_NOTHING)
    receiver = models.CharField(max_length=20,verbose_name="收件人")
    addr = models.CharField(max_length=256,verbose_name='收件地址')
    zip_code = models.CharField(max_length=6,null=True,verbose_name='邮政编码')
    phone = models.CharField(max_length=11,verbose_name='联系电话')
    is_default = models.BooleanField(default=False,verbose_name='是否默认')
    # 自定义模型管理器对象
    objects = AddressManager()
    class Meta:
        db_table = "df_address"
        verbose_name = '地址'
        verbose_name_plural = verbose_name





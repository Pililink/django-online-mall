'''
自定义存储类
文件存放到fast DFS中
相关文档
https://docs.djangoproject.com/zh-hans/3.1/ref/files/storage/
https://docs.djangoproject.com/zh-hans/3.1/howto/custom-file-storage/
https://docs.djangoproject.com/zh-hans/3.1/ref/files/file/
'''
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from fdfs_client.client import Fdfs_client, get_tracker_conf

@deconstructible
class FDFSStorage(Storage):
    '''
    fast 文件存储
    '''
    def __init__(self, client_conf=None, base_url=None):
        """初始化"""
        if not client_conf:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if not base_url:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(name, mode='rb'):
        '''文件打开'''
        pass

    def _save(self,name, content):
        '''
        保存文件时使用
        :param name: 上传文件的文件名
        :param content: 上传文件的File对象
        :return:Fast DFS中保存的id信息
        '''

        #创建一个 Fdfs_client 对象

        trackers = get_tracker_conf(self.client_conf)
        client = Fdfs_client(trackers)

        #上传文件到fdfs系统中
        ret = client.upload_by_buffer(content.read())
        '''
        dict {
                    'Group name'      : group_name,
                    'Remote file_id'  : remote_file_id,
                    'Status'          : 'Upload successed.',
                    'Local file name' : '',
                    'Uploaded size'   : upload_size,
                    'Storage IP'      : storage_ip
                }
        '''
        if ret.get('Status') !='Upload successed.':
            # 上传失败
            raise Exception('上次文件到Fast DFS失败')
        # 获取返回的文件id
        filename = ret.get('Remote file_id')
        return filename.decode()

    def exists(self,name):
        """
        在save()函数之前执行，Django判断文件名是否可用
        返回True如果给定的名称引用的文件在存储系统中已经存在，或者False如果名称是适用于一个新的文件。
        本项目文件并非存放在django中，即返回一定为Fals
        """
        return False
    def url(self, name):
        '''返回完整的url地址'''
        return self.base_url+name
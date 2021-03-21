# 运行环境
```
amqp==5.0.5
asgiref==3.3.1
billiard==3.6.3.0
celery==5.0.5
click==7.1.2
click-didyoumean==0.0.3
click-plugins==1.1.1
click-repl==0.1.6
Django==3.1.7
django-haystack==3.0
django-redis==4.12.1
django-tinymce==3.2.0
itsdangerous==1.1.0
jieba==0.42.1
Jinja2==2.10
kombu==5.0.2
MarkupSafe==1.1.1
nginx==0.0.1
Pillow==8.1.0
prompt-toolkit==3.0.16
py3Fdfs==2.2.0
PyMySQL==1.0.2
pytz==2021.1
redis==3.5.3
six==1.15.0
sqlparse==0.4.1
vine==5.0.0
wcwidth==0.2.5
Whoosh==2.7.4
```
>注意全文检索需要修改文件 https://www.cnblogs.com/chang/archive/2013/01/10/2855321.html
# 用到的服务
## celery
需要另外一台服务器跑项目中的celery

1.安装
```
pip install -U Celery
```
2.启动方法
```
celery -A celery_tasks.tasks worker -l INFO
```
> 服务器运行时需要将tasks.py文件上方的语句取消注释

## redis
安装好之后修改`settings.py`中redis的配置信息，以及`celery_task/stasks.py`中的redis的IP地址。
## mysql
版本5.7，安装之后使用修改`settings.py`中数据库的信息。使用django命令初始化数据库。
## fastdfs
### 使用docker安装

1.安装fdfs的tracker，不需要修改
```
docker run -d --network=host --name tracker -v /var/fdfs/tracker:/var/fdfs delron/fastdfs tracker
```
2.安装fdfs的storage，修改ip地址。
```
docker run -d --network=host --name storage -e TRACKER_SERVER=你服务器自己的ip:22122 -v /var/fdfs/storage:/var/fdfs -e GROUP_NAME=group1 delron/fastdfs storage
```
3.进入tracker容器修改配置。
```
# 进入容器
docker exec -it tracker bash
# 修改client.conf文件
vi /etc/fdfs/client.conf
tracker_server=你自己的ip:22122
```
3.修改项目的配置信息

`settings.py`中的fdfs_url的地址

`utils/dafs/client.conf`中的tracker_server地址
>引用：https://www.cnblogs.com/yangzhuxian/p/13879035.html

# nginx配置
## 运行端（实际运行django服务器的服务器）
配置信息
```
worker_processes  1;
events {
    worker_connections  1024;
}
http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;
    upstream django {
        server 127.0.0.1:8080;
        server 127.0.0.1:8081;
    }
    server {
        listen       80;
        server_name  localhost;

        location / {
            # 包含uwsgi的请求参数
            include uwsgi_params;
            # 转交请求给uwsgi
            #uwsgi_pass 127.0.0.1:8080;
            # 转交请求给upstream实现负载均衡
            uwsgi_pass django;
        }
        location /static/{
            # 指定静态文件存放的目录
            alias /Volumes/public_data/src/TTsx/dailyfresh/static/;
        }
        location = / {
            # 精确匹配 / 
            # 传递请求给静态文件上的nginx(服务端地址)
            proxy_pass http://10.10.10.10;
        }
        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }
    include servers/*;
}
```
## 服务端（运行网站所需服务器的服务器）
服务器fdfs是使用docker运行，docker中已有nginx无需修改。

配置信息
```
worker_processes auto;
pid /run/nginx.pid;

events {
	worker_connections 768;
}

http {
	include /etc/nginx/mime.types;
        default_type application/octet-stream;
        error_log /var/log/nginx/error.log;
	server {
                listen  80;
                server_name     localhost;
                location /static {
                        alias /home/ttsx/static/;
                }
                location / {
                        root /home/ttsx/static/;
                        index index.html index.htm;
                }
        }
}
```
# uwsgi
启动： uwsgi --ini 配置文件路径

停止： uwsgi --stop uwsgi.pid路径

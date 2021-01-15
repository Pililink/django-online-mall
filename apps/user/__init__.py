import pymysql
pymysql.version_info = (1, 4, 13, "final", 0)#通过这个命令指定pymysql的版本
pymysql.install_as_MySQLdb()  # 使用pymysql代替mysqldb连接数据库
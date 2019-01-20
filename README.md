Install
=====
* 下载源码


        git clone https://github.com/xuyunj/opsadmin.git


* 安装依赖库


        cd ansible-ui
        pip install -r requirements.txt


* 初始化数据库

        python manage.py syncdb


* 启动websocket


        python manage.py runwebsocket 0.0.0.0:9000


* 启动simpletask


        python manage.py simpletask


* 配置ansible


        cp ansible-conf/ansible.cfg ~/.ansible.cfg


Run
=====
* (manage.py)目录运行


        python manage.py runserver ip:8000


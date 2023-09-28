#!/usr/bin/env python3
# from flask import Flask
import json
import sys
import os
import platform
#import websockets.exceptions
#from websockets.server import serve
from flask import Flask, request, make_response, abort
from flask_socketio import SocketIO, emit
#from flask_cors import *
import asyncio
import hashlib
import time
import psutil
#from gevent import pywsgi
#from geventwebsocket.handler import WebSocketHandler

VERSION = "1.0.0"
connect_num = 0
sys_type = ""
config = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app, cors_allowed_origins='*')

name_space = '/ws'

def info():
    global sys_type,VERSION
    memory = psutil.virtual_memory()
    return {
        "system": {
            "arch": platform.machine(),
            "platform": sys.platform,
            "system": sys_type,
            "used_memory": memory.used,
            "total_memory": memory.total
        },
        "version": VERSION
    }

def ws_return(status:int=200,msg:str="OK",data=None):
    return json.dumps({
        "status": status,
        "msg": msg,
        "data": data
    })

@app.errorhandler(404)
def e_404(e):
    return """<html>
<head><title>404 Not Found</title></head>
<body>
<center><h1>404 Not Found</h1></center>
<hr><center>Powered by TzGamePanel</center>
</body>
</html>"""

@app.route("/")
def daemon_is_ok():
    return "TzGamePanel Daemon is OK. Time: "+str(int(time.time()))

@app.route("/get_info", methods=["GET"])
def get_info():
    token = request.args.get("token")
    if not token:
        return json.dumps({'status': 403,'msg': "Permission denied"}), 403
    if not token == config['token']:
        return json.dumps({'status': 403,'msg': "Pernission denied"}), 403
    else:
        return json.dumps({'status': 200,'msg': "OK",'data':info()}), 200

@socketio.on("connect", namespace=name_space)
def websocket_connect(ws):
    print("websocket建立连接")

@socketio.on("my_event", namespace=name_space)
def websocket_msg(msg):
    print(msg)
    emit('test',msg)

def main():
    global sys_type,config
    print("_____     ____                      ____                  _\n|_   _|___/ ___| __ _ _ __ ___   ___|  _ \\ __ _ _ __   ___| |\n  | ||_  / |  _ / _` | '_ ` _ \\ / _ \\ |_) / _` | '_ \\ / _ \\ |\n  | | / /| |_| | (_| | | | | | |  __/  __/ (_| | | | |  __/ |\n  |_|/___|\\____|\\__,_|_| |_| |_|\\___|_|   \\__,_|_| |_|\\___|_|")
    print("___\n|   \\ __ _ ___ _ __  ___ _ _\n| |) / _` / -_) '  \\/ _ \\ ' \\\n|___/\\__,_\\___|_|_|_\\___/_||_|")
    if not os.path.exists("data"):
        os.mkdir("data")
    if not os.path.exists("data/configs"):
        os.mkdir("data/configs")
    if not os.path.exists("data/InstanceConfig"):
        os.mkdir("data/InstanceConfig")
    if not os.path.exists("data/InstanceData"):
        os.mkdir("data/InstanceData")
    token = None
    if not os.path.exists("data/configs/config.json"):
        with open("data/configs/config.json","w") as f:
            token = hashlib.md5(string=str(str(time.time())+"TzGamePanel key").encode("utf-8")).hexdigest()
            f.write(json.dumps({
                'host': '0.0.0.0',
                'port': 8002,
                'token':token
            },indent=4))
    with open("data/configs/config.json","r") as f:
        config = f.read()
    try:
        config = json.loads(config)
    except json.decoder.JSONDecodeError as err:
        print(f"在加载配置文件时发生了错误：JSONDecodeError: {err}")
        print("请尝试删除配置文件data/configs/config.json，然后再启动")
        sys.exit(1)
    if token != None:
        print("第一次启动，已生成token: "+token)
    if sys.platform.startswith("linux"):
        sys_type = "Linux"
    elif sys.platform.startswith("win"):
        sys_type = "Windows"
    else:
        print("不支持你的操作系统！")
        print(f"sys.platform = {platform}")
        sys.exit(1)
    print("此设备的平台："+sys.platform)
    print("此设备的操作系统："+sys_type)
    print("TzGamePanel开源免费，基于GPLv3，项目地址：https://gitee.com/tzdtwsj/TzGamePanel-Daemon")
    print(f"TzGamePanel监听在地址{config['host']}，端口{config['port']}")
    print("此进程的PID是"+str(os.getpid()))
    print("退出请按下Ctrl + C")
    socketio.run(app,host=config['host'],port=config['port'])

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("正在退出")
        sys.exit(0)

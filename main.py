#!/usr/bin/env python3
# from flask import Flask
import json
import sys
import os
import platform
from flask import Flask, request, make_response, abort
from flask_socketio import SocketIO, emit
import hashlib
import time
import glob
from subprocess import Popen, PIPE
import psutil

VERSION = "1.0.0"
sys_type = ""
config = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app, cors_allowed_origins='*')

name_space = '/ws'

started_instances = []

os.chdir(os.path.dirname(__file__)) # 强制更改目录到项目所在目录
from func import *
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

def get_instances_list():
    files = glob.glob(os.path.join(os.path.dirname(__file__),"data","InstanceConfig","*.json"))
    instances = []
    for i in files:
        with open(i) as f:
            try:
                inst = json.loads(f.read(9999999))
                instances.append(inst)
            except json.decoder.JSONDecodeError:
                continue
    return instances

def create_instance(name:str,start_cmd:str,stop_cmd:str="stop",instance_dir=None):
    instance_id = hashlib.md5(string=str(str(time.time())+"TzGamePanel Instance ID").encode("utf-8")).hexdigest()
    if instance_dir == None:
        instance_dir = os.path.abspath("data/InstanceData/"+instance_id)
        os.mkdir(instance_dir)
    else:
        if not os.path.isdir(instance_dir):
            return {
                'status': False,
                'msg': "实例目录不存在"
            }
    instance_config_template = {
        "name": name,
        "id": instance_id,
        "configs": {
            "start_cmd": start_cmd,
            "stop_cmd": stop_cmd,
            "create_time": int(time.time())
        }
    }
    with open(os.path.abspath("data/InstanceConfig/"+instance_id+".json"),"w") as f:
        f.write(json.dumps(instance_config_template))
    with open(os.path.abspath("data/InstanceLog/"+instance_id+".log"),"w") as f:
        f.write("欢迎使用TzGamePanel\n此实例已成功创建\n")
    return {
        'status': True,
        'msg': "OK",
        'instance_id': instance_id
    }

def start_instance(instance_id:str):
    status = False
    config = {}
    for i in get_instances_list():
        if i['id'] == instance_id:
            status = True
            config = i['config']
            break
    if status:
        cmd = load_cmd_str(config['start_cmd'])
        if cmd == False:
            return {
                'status': False,
                'msg': "启动命令解析失败"
            }
        start_inst = start_instance(cmd)
    else:
        return {
            'status': False,
            'msg': "没有此实例"
        }

def ws_return(status:int=200,msg:str="OK",data=None):
    return json.dumps({
        "status": status,
        "msg": msg,
        "data": data
    })

@app.errorhandler(400)
def e_400(e):
    return json.dumps({
        'status': 400,
        'msg': 'Please check if the data you sent to the server is correct.'
    })

@app.errorhandler(404)
def e_404(e):
    return json.dumps({
        'status': 404,
        'msg': 'Not Found'
    })

@app.errorhandler(405)
def e_405(e):
    return json.dumps({
        'status': 405,
        'msg': 'Method Not Allowed'
    })

@app.errorhandler(415)
def e_415(e):
    return json.dumps({
        'status': 415,
        'msg': 'Did not attempt to load JSON data because the request Content-Type was not \"application/json\".'
    })

@app.errorhandler(500)
def e_500(e):
    return json.dumps({
        'status': 500,
        'msg': 'TzGamePanel Daemon has some error. Please check Daemon\'s log.'
    },indent=4)

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

@app.route("/get_instances", methods=['GET'])
def get_instances():
    token = request.args.get("token")
    if not token:
        return json.dumps({'status': 403,'msg': "Permission denied"}), 403
    if not token == config['token']:
        return json.dumps({'status': 403,'msg': "Pernission denied"}), 403
    else:
        return json.dumps({'status': 200,'msg': 'OK','data':get_instances_list()}), 200

@app.route("/create_instance",methods=['POST'])
def c_instance():
    token = request.args.get("token")
    if not token:
        return json.dumps({'status': 403,'msg': "Permission denied"}), 403
    if not token == config['token']:
        return json.dumps({'status': 403,'msg': "Pernission denied"}), 403
    else:
        data = request.get_json()
        if not data:
            return json.dumps({'status': 400,'msg': "Empty JSON data"}), 400
        if data.get("name")==None or data.get("start_cmd")==None:
            return json.dumps({'status': 400,'msg': "Missing parameter"}), 400
        if data.get("stop_cmd") == None:
            stop_cmd = "stop"
        else:
            stop_cmd = data.get("stop_cmd")
        instance_dir = data.get("instance_dir")
        result = create_instance(name=data.get("name"),start_cmd=data.get("start_cmd"),stop_cmd=stop_cmd,instance_dir=instance_dir)
        if not result['status']:
            return json.dumps({'status': 400,'msg': "实例目录不存在"}), 400
        else:
            return json.dumps({'status': 200,'msg': "OK",'instance_id':result['instance_id']}), 200


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
    if not os.path.exists("data/InstanceLog"):
        os.mkdir("data/InstanceLog")
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
    print("VERSION: "+str(VERSION))
    print("此设备的平台："+sys.platform)
    print("此设备的操作系统："+sys_type)
    print("TzGamePanel开源免费，遵循GPLv3开源许可证，项目地址：https://gitee.com/tzdtwsj/TzGamePanel-Daemon")
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

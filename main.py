#!/usr/bin/env python3
# from flask import Flask
import json
import sys
import os
import platform
from flask import Flask, request, make_response, abort
from flask_socketio import SocketIO, emit, join_room
import hashlib
import time
import glob
from subprocess import Popen, PIPE
import psutil
import threading

VERSION = "1.0.0"
sys_type = ""
config = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app, cors_allowed_origins='*')

name_space = '/ws'

instances = []

tmp_terminal_token = []
Thread_check_tmp_terminal_token = None

os.chdir(os.path.dirname(__file__)) # 强制更改目录到项目所在目录
from func import *

def ret(status:int,msg:str,data=None):
    return json.dumps({'status':status,'msg':msg,'data':data,'time':int(time.time())}), status

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
    global instances
    files = glob.glob(os.path.join(os.path.dirname(__file__),"data","InstanceConfig","*.json"))
    instances2 = []
    for i in files:
        with open(i) as f:
            try:
                inst = json.loads(f.read(9999999))
                instances2.append(inst)
            except json.decoder.JSONDecodeError:
                continue
    i = 0
    while i<len(instances2):
        for j in instances:
            if j.instance_id == instances2[i]['id']:
                instances2[i]['status'] = j.status
                continue
        i += 1
    return instances2

def get_instance(instance_id):
    for i in get_instances_list():
        if i['id'] == instance_id:
            return i
    return False

def create_instance(name:str,start_cmd:str,stop_cmd:str="stop",instance_dir=None):
    instance_id = hashlib.md5(string=str(str(time.time())+"TzGamePanel Instance ID").encode("utf-8")).hexdigest()
    if instance_dir == None:
        instance_dir = os.path.abspath("data/InstanceData/"+instance_id)
        os.mkdir(instance_dir)
    else:
        if not os.path.isdir(instance_dir):
            return {
                'status': False,
                'msg': "指定的实例目录不存在"
            }
    if load_cmd_str(start_cmd) == False:
        return {
            'status': False,
            'msg': "启动命令解析失败"
        }
    instance_config_template = {
        "name": name,
        "id": instance_id,
        "configs": {
            "start_cmd": start_cmd,
            "stop_cmd": stop_cmd,
            "work_directory": instance_dir
        },
        "create_time": int(time.time())
    }
    with open(os.path.abspath("data/InstanceConfig/"+instance_id+".json"),"w") as f:
        f.write(json.dumps(instance_config_template))
    with open(os.path.abspath("data/InstanceLog/"+instance_id+".log"),"w") as f:
        f.write("[TzGamePanel] 实例已成功创建\nPowered by TzGamePanel\n")
    global instances
    instances.append(instance(cmd=load_cmd_str(start_cmd),cwd=instance_dir,instance_id=instance_id))
    return {
        'status': True,
        'msg': "OK",
        'instance_id': instance_id
    }

def start_instance(instance_id:str):
    global instances
    status = False
    inst = None
    for i in instances:
        if i.instance_id == instance_id:
            status = True
            inst = i
            break
    if status:
        result = inst.start()
        if result == True:
            return {
                'status': True,
                'msg': "OK"
            }
        elif result == False:
            return {
                'status': False,
                'msg': "实例正在运行中，无需再启动"
            }
        else:
            return {
                'status': False,
                'msy': "实例启动失败，请检查实例配置是否正确"
            }
    else:
        return {
            'status': False,
            'msg': "没有此实例"
        }

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
        return ret(403,"Permission denied")
    if not token == config['token']:
        return ret(403,"Permission denied")
    else:
        return ret(200,"OK",info())

@app.route("/get_instances", methods=['GET'])
def get_instances():
    token = request.args.get("token")
    if not token:
        return ret(403,"Permission denied")
    if not token == config['token']:
        return ret(403,"Permission denied")
    else:
        return ret(200,"OK",get_instances_list())

@app.route("/create_instance",methods=['POST'])
def web_create_instance():
    token = request.args.get("token")
    if not token:
        return ret(403,"Permission denied")
    if not token == config['token']:
        return ret(403,"Permission denied")
    else:
        data = request.get_json()
        if not data:
            return ret(400,"Empty JSON data")
        if data.get("name")==None or data.get("start_cmd")==None:
            return ret(400,"Missing parameter")
        if data.get("stop_cmd") == None:
            stop_cmd = "stop"
        else:
            stop_cmd = data.get("stop_cmd")
        instance_dir = data.get("instance_dir")
        result = create_instance(name=data.get("name"),start_cmd=data.get("start_cmd"),stop_cmd=stop_cmd,instance_dir=instance_dir)
        if not result['status']:
            return ret(400,"实例目录不存在")
        else:
            return ret(200,"OK",result['instance_id'])

@app.route("/start_instance")
def web_start_instance():
    token = request.args.get("token")
    if not token:
        return ret(403,"Permission denied")
    if not token == config['token']:
        return ret(403,"Permission denied")
    instance_id = request.args.get("instance_id")
    if not instance_id:
        return ret(400,"Missing parameter")
    status = False
    for i in get_instances_list():
        if i['id'] == instance_id:
            status = True
            break
    if status:
        result = start_instance(instance_id)
        if result['status']:
            return ret(200,"OK")
        else:
            return ret(500,result['msg'])
    else:
        return ret(404,"实例不存在")

@app.route("/stop_instance")
def web_stop_instance():
    global instances
    token = request.args.get("token")
    if not token:
        return ret(403,"Permission denied")
    if not token == config['token']:
        return ret(403,"Permission denied")
    instance_id = request.args.get("instance_id")
    if not instance_id:
        return ret(400,"Missing parameter")
    status = False
    inst = None
    for i in instances:
        if i.instance_id == instance_id:
            inst = i
            status = True
            break
    if status:
        i.stop(get_instance(i.instance_id)['configs']['stop_cmd'])
        return ret(200,"OK")
    else:
        return ret(404,"实例不存在")

@app.route("/send_cmd_to_instance",methods=["POST"])
def web_send_cmd_to_instance():
    global instances
    token = request.args.get("token")
    if not token:
        return ret(403,"Permission denied")
    if not token == config['token']:
        return ret(403,"Permission denied")
    instance_id = request.args.get("instance_id")
    data = request.get_json()
    if not instance_id or not data.get("command"):
        return ret(400,"Missing parameter")
    if type(data.get("command")) != str:
        return ret(400,"\"command\" must is str")
    status = False
    inst = None
    for i in instances:
        if i.instance_id == instance_id:
            inst = i
            status = True
            break
    if status:
        result = i.exec_cmd(data.get("command"),log_to_terminal=data.get("log_to_terminal",True))
        if result:
            return ret(200,"OK")
        else:
            return ret(500,"实例未启动，无法执行命令")
    else:
        return ret(404,"实例不存在")

@app.route("/get_tmp_terminal_connect_token",methods=["POST"])
def gttct():
    global tmp_terminal_token,Thread_check_tmp_terminal_token
    if Thread_check_tmp_terminal_token == None:
        def cttt():
            global tmp_terminal_token
            tmp_terminal_token2 = []
            while True:
                for i in tmp_terminal_token:
                    if i['endtime'] >= int(time.time()):
                        tmp_terminal_token2.append(i)
                tmp_terminal_token = tmp_terminal_token2
                tmp_terminal_token2 = []
                time.sleep(1)
        Thread_check_tmp_terminal_token = threading.Thread(target=cttt)
        Thread_check_tmp_terminal_token.daemon = True
        Thread_check_tmp_terminal_token.start()
    token = request.args.get("token")
    if not token:
        return ret(403,"Permission denied")
    if not token == config['token']:
        return ret(403,"Permission denied")
    data = request.get_json()
    if not data:
        return ret(400,"Empty JSON data")
    if data.get("instance_id")==None:
        return ret(400,"Missing parameter")
    if get_instance(data.get("instance_id")) == False:
        return ret(400,"实例不存在")
    for i in tmp_terminal_token:
        if i['instance_id'] == data.get("instance_id"):
            return ret(200,"OK",{'token':i['token'],'instance_id':data.get("instance_id")})
    token = hashlib.sha256(string=str(str(time.time())+"TzGamePanel Terminal Key").encode("utf-8")).hexdigest()
    tmp_terminal_token.append({'instance_id':data.get("instance_id"),'token':token,'endtime':int(time.time())+86400})
    return ret( 200, "OK", {'token':token,'instance_id':data.get("instance_id")} )


@socketio.on("connect", namespace=name_space)
def websocket_connect(ws):
    print("websocket建立连接")

@socketio.on("disconnect", namespace=name_space)
def websocket_disconnect():
    print("webscoket断开连接")

@socketio.on("terminal", namespace=name_space)
def websocket_terminal(msg):
    global tmp_terminal_token
    if type(msg) != dict:
        emit("result",[False,-1,"Must is type 'dict'(or javascript object)."])
        return
    token = msg.get("token")
    if token == None:
        emit("result",[False,-1,"The parameter \"token\" was not found or it was \"null\"."])
        return
    status = False
    instance_id = None
    for i in tmp_terminal_token:
        if i['token'] == msg.get("token"):
            status = True
            instance_id = i['instance_id']
            break
    if status:
        emit("result",[True,0,"OK. Please listen event \"terminal\"."])
    else:
        emit("result",[False,-1,"Permission denied."])
        return
    join_room("instance_"+instance_id,namespace="/ws")

def main():
    global sys_type,config,instances
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
            token = hashlib.md5(string=str(str(time.time())+"TzGamePanel Key").encode("utf-8")).hexdigest()
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
        log(f"在加载配置文件时发生了错误：JSONDecodeError: {err}",loglevel="FATAL")
        log("请尝试删除配置文件data/configs/config.json，然后再启动",loglevel="FATAL")
        sys.exit(1)
    if token != None:
        log("第一次启动，已生成token: "+token)
    if sys.platform.startswith("linux"):
        sys_type = "Linux"
    elif sys.platform.startswith("win"):
        sys_type = "Windows"
    else:
        log("不支持你的操作系统！",loglevel="ERROR")
        log(f"sys.platform = {platform}",loglevel="ERROR")
        sys.exit(1)
    log("守护进程版本: "+str(VERSION))
    log("此设备的平台："+sys.platform)
    log("此设备的操作系统："+sys_type)
    log("TzGamePanel开源免费，遵循GPLv3开源许可证，项目地址：https://gitee.com/tzdtwsj/TzGamePanel-Daemon")
    log("加载实例中")
    for i in get_instances_list():
        instances.append(instance(cmd=load_cmd_str(i['configs']['start_cmd']),cwd=i['configs']['work_directory'],instance_id=i['id']))
    log("加载实例完成")
    log(f"TzGamePanel监听在地址{config['host']}，端口{config['port']}")
    log("此进程的PID是"+str(os.getpid()))
    log("退出请按下Ctrl + C")
    socketio.run(app,host=config['host'],port=config['port'])

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log("正在退出")
        for i in instances:
            i.kill()
        sys.exit(0)

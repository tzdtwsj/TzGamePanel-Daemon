#!/usr/bin/env python3
from flask import Flask
import json
import sys
import os
import platform
app = Flask(__name__)

@app.route("/")
def root():
    return 'TzGamePanel Daemon is OK.'

@app.get("/info")
def info():
    global sys_type
    info = {
        "status": 200,
        "msg": "OK",
        "data": {
            "system": {
                "arch": platform.machine(),
                "platform": sys.platform,
                "system": sys_type
            }
        }
    }
    return json.dumps(info)

if __name__ == '__main__':
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
    if not os.path.exists("data/configs/config.json"):
        with open("data/configs/config.json","w") as f:
            f.write(json.dumps({
                'host': '0.0.0.0',
                'port': 8002
            },indent=4))
    with open("data/configs/config.json","r") as f:
        config = f.read()
    try:
        config = json.loads(config)
    except json.decoder.JSONDecodeError as err:
        print(f"在加载配置文件时发生了错误：JSONDecodeError: {err}")
        print("请尝试删除配置文件data/configs/config.json，然后再启动")
        sys.exit(1)
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
    app.run(host=config['host'],port=config['port'])

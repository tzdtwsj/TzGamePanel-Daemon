#!/usr/bin/env python3
# from flask import Flask
import json
import sys
import os
import platform
import websockets.exceptions
from websockets.server import serve
import asyncio
import hashlib
import time
import psutil

VERSION = "1.0.0"
connect_num = 0
sys_type = ""
config = {}

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

async def ws_main(ws):
    global connect_num,config
    connect_num += 1
    auth = False
    print(f"有客户端建立连接，当前连接数：{connect_num}")
    try:
        async for message in ws:
            if auth == False:
                if message == config['token']:
                    auth = True
                    await ws.send("OK")
                    continue
                else:
                    await ws.send("Fail")
                    break
            try:
                data = json.loads(message)
            except json.decoder.JSONDecodeError:
                await ws.send(json.dumps({
                    "status": 500,
                    "msg": "无法解析JSON",
                    "data": None
                }))
                break
            if data.get("action") == None:
                await ws.send(ws_return(400,"缺少参数action"))
                break
            elif data.get("action") == "get_info":
                await ws.send(ws_return(data=info()))
            elif data.get("action") == "close_connection":
                break
            else:
                await ws.send(ws_return(400,"无效的action"))
    except websockets.exceptions.ConnectionClosedError:
        connect_num -= 1
        print(f"有客户端断开连接，当前连接数：{connect_num}")
        return
    connect_num -= 1
    print(f"有客户端断开连接，当前连接数：{connect_num}")

async def main():
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
    async with serve(ws_main,config['host'],config['port']):
        print(f"TzGamePanel监听在地址{config['host']}，端口{config['port']}")
        print("此进程的PID是"+str(os.getpid()))
        print("退出请按下Ctrl + C")
        await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("正在退出")
        sys.exit(0)

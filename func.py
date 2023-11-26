from subprocess import Popen, PIPE
import os
import threading
import time
import datetime
from __main__ import emit, app
def load_cmd_str(cmd:str):
    char_arr = list(cmd.strip())
    tmp_cmd_arr = [""]
    num = 0
    i = 0
    z = 0
    while i < len(char_arr):
        if char_arr[i] == " " and char_arr[i-1] == " ":
            i = i + 1
            continue
        if char_arr[i] == "\"" and ( i==0 or z%2 == 0 ):
            z1 = 0
            while i < len(char_arr):
                if i+1 == len(char_arr):
                    return False
                if char_arr[i] == "\\":
                    z1 += 1
                else:
                    z1 = 0
                if char_arr[i+1] == "\"" and z1%2 == 0:
                    break
                elif i+1 != len(char_arr):
                    tmp_cmd_arr[num] += char_arr[i+1]
                i = i + 1
            i = i + 1
        elif char_arr[i] == " ":
            num = num + 1
            tmp_cmd_arr.append("")
        else:
            tmp_cmd_arr[num] += char_arr[i]
        if char_arr[i] == "\\":
            z += 1
        else:
            z = 0
        i = i + 1
    return tmp_cmd_arr

def log(text:str,loglevel:str="INFO"):
    if loglevel == "INFO":
        loglevel2 = "\x1b[36mINFO\x1b[0m"
    elif loglevel == "WARN":
        loglevel2 = "\x1b[33mWARN\x1b[0m"
    elif loglevel == "ERROR":
        loglevel2 = "\x1b[31mERROR\x1b[0m"
    elif loglevel == "FATAL":
        loglevel2 = "\x1b[31mFATAL\x1b[0m"
    elif loglevel == "DEBUG":
        loglevel2 = "\x1b[34mDEBUG\x1b[0m"
    else:
        raise ValueError("无效的loglevel: "+loglevel)
    print("\x1b[0m[\x1b[32m"+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\x1b[0m \x1b[33mTzGamePanel\x1b[0m "+loglevel2+"] "+text)

class instance:
    cmd = None
    cwd = None
    proc = None #进程类
    stdin = None #管道
    stdout = None #管道
    stdout2 = []
    instance_id = None #实例id
    Thread_read_proc_text_to_file = None
    closed = False
    status = 0 #关于status的解释：0-已关闭，1-运行中，2-关闭中

    def __init__(self,cmd:list,cwd:str,instance_id:str):
        if self.closed:
            raise Exception("此对象已被关闭")
        if type(cmd) != list:
            raise TypeError(f"cmd should be list, not {type(cmd)}")
        self.stdin = os.pipe()#os.pipe返回的是元组，元组的返回的第一个fd是读，第二个fd是写
        self.stdout = os.pipe()
        #self.stderr = os.pipe()
        self.cmd = cmd
        self.cwd = cwd
        self.instance_id = instance_id
        def read_proc_text_to_file(file,fd,self):
            while True:
                try:
                    text = os.read(fd,256000)
                except Exception as e:
                    return
                with open(file,"ab") as f:
                    f.write(text)
                self.stdout2.append(text)
                try:
                    with app.app_context():
                        emit('terminal', text, to="instance_"+instance_id, namespace="/ws", broadcast=True)
                except Exception as e:
                    print(str(e))
            
        self.Thread_read_proc_text_to_file = threading.Thread(
            target = read_proc_text_to_file,
            kwargs = {
                'file': os.path.abspath("data/InstanceLog/"+self.instance_id+".log"),
                'fd': self.stdout[0],
                'self': self
            }
        )
        self.Thread_read_proc_text_to_file.setDaemon(True)
        self.Thread_read_proc_text_to_file.start()

    def start(self):
        if self.closed:
            raise Exception("此对象已被关闭")
        if self.proc != None:
            if self.proc.poll() == None:
                return False
        try:
            if os.path.isdir(self.cmd[0]):
                raise Exception(f"{self.cmd[0]}: 是一个目录")
            self.proc = Popen(
                args = self.cmd,#命令参数
                shell = False,#是否由shell带动此进程
                stdin = self.stdin[0],#标准输入
                stdout = self.stdout[1],#标准输出
                stderr = self.stdout[1],#标准错误输出
                cwd = self.cwd
            )
        except Exception as e:
            os.write(self.stdout[1],("[TzGamePanel] 实例启动失败，请检查启动命令\n    启动命令：\n").encode("utf-8"))
            os.write(self.stdout[1],("  ").encode("utf-8"))
            for i in self.cmd:
                os.write(self.stdout[1],(i+" ").encode("utf-8"))
            os.write(self.stdout[1],("\n").encode("utf-8"))
            os.write(self.stdout[1],("  启动时捕获到的异常："+str(e)+"\n").encode("utf-8"))
            return e
        self.status = 1
        def ciir(self):
            while True:
                time.sleep(1)
                if not self.is_running():
                    self.status = 0
                    os.write(self.stdout[1],("[TzGamePanel] 实例已关闭"+"\n").encode("utf-8"))
                    return
        threading.Thread(target=ciir,kwargs={'self':self}).start()
        os.write(self.stdout[1],("[TzGamePanel] 实例已启动"+"\n").encode("utf-8"))
        return True

    def is_running(self):
        if self.closed:
            raise Exception("此对象已被关闭")
        if self.proc == None:
            return False
        if self.proc.poll() == None:
            return True
        else:
            return False

    def get_return_code(self):
        if self.closed: 
            raise Exception("此对象已被关闭")
        if self.proc.poll() == None:
            return False
        return self.proc.poll()

    def stop(self,stop_cmd:str="stop"):
        if self.closed: 
            raise Exception("此对象已被关闭")
        if not self.is_running():
            return False
        if self.status == 2:
            return True
        self.status = 2
        def csis(self,ct):
            while time.time()<ct+300:
                if not self.is_running():
                    return
            os.write(self.stdout[1], ("[TzGamePanel] 检测到实例关闭实例时长过长，已自动恢复到运行中状态\n").encode("utf-8"))
            self.status = 1
        threading.Thread(target=csis,kwargs={'self':self,'ct':time.time()}).start()
        os.write(self.stdout[1], ("[TzGamePanel] 已发送停止命令："+stop_cmd+"，如果停止命令不正确将会无法正常停止\n").encode("utf-8"))
        os.write(self.stdin[1],(stop_cmd+"\n").encode("utf-8"))
        return True

    def kill(self):
        if self.closed: 
            raise Exception("此对象已被关闭")
        if not self.is_running():
            return False
        self.proc.kill()
        return True

    def exec_cmd(self,cmd:str,log_to_terminal:bool=True):
        if self.closed: 
            raise Exception("此对象已被关闭")
        if self.proc == None or self.proc.poll() != None:
            return False
        os.write(self.stdin[1],cmd.encode("utf-8"))
        os.write(self.stdin[1],b"\n")
        if log_to_terminal == True:
            os.write(self.stdout[1],("[TzGamePanel] 用户执行了命令："+cmd+"\n").encode("utf-8"))
        return True

    def clear_log(self):
        with open(os.path.abspath("data/InstanceLog/"+self.instance_id+".log"),"w") as f:
            f.write("")
        self.stdout2 = []

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.proc != None and self.proc.poll() == None:
            self.proc.kill()
        for i in [self.stdin[0],self.stdin[1],self.stdout[0],self.stdout[1]]:
            os.close(i)

if __name__ == "__main__":
    print("不要直接执行此文件！你需要执行TzGamePanel的main.py进行使用")

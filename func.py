from subprocess import Popen, PIPE
import os
import threading
import time
import datetime
import sys
from __main__ import emit, app
import __main__
import traceback
import psutil
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

def log(text:str,loglevel:str="INFO",color=None):
    if color == None:
        color = __main__.config.get("colorlog",False)
    if color:
        info = "\x1b[36m"
        warn = "\x1b[33m"
        error = "\x1b[31m"
        fatal = "\x1b[31m"
        debug = "\x1b[34m"
        clear = "\x1b[0m"
        _time = "\x1b[32m"
    else:
        info = warn = error = fatal = debug = clear = _time = ""
    if loglevel == "INFO":
        loglevel2 = info+"INFO"+clear
    elif loglevel == "WARN":
        loglevel2 = warn+"WARN"+clear
    elif loglevel == "ERROR":
        loglevel2 = error+"ERROR"+clear
    elif loglevel == "FATAL":
        loglevel2 = fatal+"FATAL"+clear
    elif loglevel == "DEBUG":
        loglevel2 = debug+"DEBUG"+clear
    else:
        raise ValueError("无效的loglevel: "+loglevel)
    print(clear+"["+_time+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+clear+" "+warn+"TzGamePanel "+clear+loglevel2+"] "+text)

def load_dir(directory):
    dir2 = directory.split("/")
    dir3 = ""
    for i in dir2:
        if i == "":
            continue
        dir3 += "/"+i
    if dir3 == "":
        return "/"
    else:
        return dir3

class instance:
    cmd = None
    cwd = None
    proc = None #进程类
    stdin = None #管道
    stdout = None #管道
    stdout2 = None
    instance_id = None #实例id
    Thread_read_proc_text_to_file = None
    closed = False
    status = 0 #关于status的解释：0-已关闭，1-运行中，2-关闭中

    thread_lock = threading.Lock()

    def __init__(self,cmd:list,cwd:str,instance_id:str):
        if self.closed:
            raise Exception("此对象已被关闭")
        if type(cmd) != list:
            raise TypeError(f"cmd should be list, not {type(cmd).__name__}")
        self.stdin = os.pipe()#os.pipe返回的是元组，元组的返回的第一个fd是读，第二个fd是写
        self.stdout = os.pipe()
        #self.stderr = os.pipe()
        self.cmd = cmd
        self.cwd = cwd
        self.instance_id = instance_id
        self.stdout2 = []
        self.__clean_log_file(os.path.abspath("data/InstanceLog/"+self.instance_id+".log"))
        if os.path.exists(os.path.abspath("data/InstanceLog/"+self.instance_id+".log")):
                with open(os.path.abspath("data/InstanceLog/"+self.instance_id+".log"),"rb") as f:
                    if os.path.getsize(os.path.abspath("data/InstanceLog/"+self.instance_id+".log")) > 1024**2:
                        f.seek(-1*(1024**2),2)
                    self.stdout2.append(f.read(1024**2))
        def read_proc_text_to_file(file,fd,self):
            while True:
                try:
                    text = os.read(fd,256000)
                except Exception as e:
                    return
                self.thread_lock.acquire()
                with open(file,"ab") as f:
                    f.write(text)
                self.stdout2 = self.stdout2[:500]
                self.stdout2.append(text)
                self.thread_lock.release()
                text = text.replace(b'\n',b'\r\n')
                try:
                    with app.app_context():
                        emit('terminal', text, to="instance_"+self.instance_id, namespace="/ws", broadcast=True)
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
        self.__clean_log_file(os.path.abspath("data/InstanceLog/"+self.instance_id+".log"))
        try:
            if os.path.isdir(self.cmd[0]):
                raise Exception(f"{self.cmd[0]}: 是一个目录")
            self.proc = Popen(
                args = self.cmd,         # 命令参数
                shell = False,           # 是否由shell带动此进程
                stdin = self.stdin[0],   # 标准输入
                stdout = self.stdout[1], # 标准输出
                stderr = self.stdout[1], # 标准错误输出
                cwd = self.cwd
            )
        except Exception as e:
            os.write(self.stdout[1],("[TzGamePanel] 实例启动失败，请检查启动命令\n    启动命令：\n").encode("utf-8"))
            os.write(self.stdout[1],("  ").encode("utf-8"))
            for i in self.cmd:
                os.write(self.stdout[1],(i+" ").encode("utf-8"))
            os.write(self.stdout[1],("\n").encode("utf-8"))
            os.write(self.stdout[1],("  启动时捕获到的异常："+str(e)+"\n").encode("utf-8"))
            traceback.print_exc()
            return e
        self.status = 1
        def ciir(self):
            while True:
                time.sleep(1)
                if not self.is_running():
                    self.status = 0
                    log("实例 "+__main__.get_instance(self.instance_id).get("name")+"["+self.instance_id+"] 已关闭")
                    os.write(self.stdout[1],("[TzGamePanel] 实例已关闭"+"\n").encode("utf-8"))
                    with app.app_context():
                        emit('instance-status', 0, to="instance_"+self.instance_id, namespace="/ws", broadcast=True)
                    return
        threading.Thread(target=ciir,kwargs={'self':self}).start()
        os.write(self.stdout[1],("[TzGamePanel] 实例已启动"+"\n").encode("utf-8"))
        with app.app_context():
            emit('instance-status', 1, to="instance_"+self.instance_id, namespace="/ws", broadcast=True)
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

    def stop(self,stop_cmd:str="stop",log_to_terminal:bool=True):
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
            with app.app_context():
                emit('instance-status', 1, to="instance_"+self.instance_id, namespace="/ws", broadcast=True)
        threading.Thread(target=csis,kwargs={'self':self,'ct':time.time()}).start()
        if log_to_terminal:
            os.write(self.stdout[1], ("[TzGamePanel] 已发送停止命令："+stop_cmd+"，如果停止命令不正确将会无法正常停止\n").encode("utf-8"))
        os.write(self.stdin[1],(stop_cmd+"\n").encode("utf-8"))
        with app.app_context():
            emit('instance-status', 2, to="instance_"+self.instance_id, namespace="/ws", broadcast=True)
        return True

    def kill(self):
        if self.closed: 
            raise Exception("此对象已被关闭")
        if not self.is_running():
            return False
        proc = psutil.Process(self.proc.pid)
        try:
            proc_children = proc.children(recursive=True)
            for i in proc_children:
                os.kill(i.pid,9)
        except Exception as e:
            traceback.print_exc()
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

    def send_string(self,string:str):#与exec_cmd不同的是，这个结尾没有换行符
        if self.closed:
            raise Exception("此对象已被关闭")
        if self.proc == None or self.proc.poll() != None:
            return False
        os.write(self.stdin[1],string.encode("utf-8"))
        return True

    def clear_log(self):
        self.thread_lock.acquire()
        with open(os.path.abspath("data/InstanceLog/"+self.instance_id+".log"),"w") as f:
            f.write("")
        self.stdout2 = []
        self.thread_lock.release()

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.proc != None and self.proc.poll() == None:
            self.proc.kill()
        for i in [self.stdin[0],self.stdin[1],self.stdout[0],self.stdout[1]]:
            os.close(i)

    def listdir(self,directory:str="/"):
        try:
            files = os.listdir(os.path.abspath(self.cwd+"/"+directory))
        except Exception:
            return False
        files2 = []
        for i in files:
            mode = oct(os.stat(os.path.abspath(self.cwd+"/"+directory+"/"+i)).st_mode & 0o777)[2:]
            if os.path.isdir(os.path.abspath(self.cwd+"/"+directory+"/"+i)):
                files2.append({'name':i,'type':"d","mode":mode,"size":None})
            else:
                files2.append({'name':i,'type':"f","mode":mode,"size":os.path.getsize(os.path.abspath(self.cwd+"/"+directory+"/"+i))})
        return files2

    def get_last_log(self,line:int=50):
        string = ""
        self.thread_lock.acquire()
        for i in self.stdout2[0-line:]:
            string += i.decode("utf-8")
        self.thread_lock.release()
        return string

    def __clean_log_file(self,file):
        if not os.path.exists(os.path.abspath("data/InstanceLog/"+self.instance_id+".log")):
            return
        self.thread_lock.acquire()
        text = ""
        if os.path.getsize(os.path.abspath("data/InstanceLog/"+self.instance_id+".log")) > 1024**2:
            with open(file,"rb") as f:
                f.seek(-1*(1024**2),2)
                text = f.read(1024**2) # 1MiB
            with open(file,"wb") as f:
                f.write(text)
        self.thread_lock.release()

if __name__ == "__main__":
    print("不要直接执行此文件！你需要执行TzGamePanel的main.py进行使用")

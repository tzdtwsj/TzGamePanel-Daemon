from subprocess import Popen, PIPE
import os
import threading
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

class start_instance:
    proc = None #进程类

    status = None #进程返回的返回值

    stdin = None #管道

    stdout = None #管道

    stdout2 = None #class将会使用此管道

    instance_id = None #实例id

    start_success = None #是否启动进程成功

    error_msg = "" #如果start_success == False，那么这个变量会有内容

    #stderr = None#为了方便，stderr与stdout合并

    Thread_read_proc_text_to_file = None

    Thread_check_proc_is_running = None

    def __init__(self,cmd:list,cwd:str,instance_id:str):
        self.stdin = os.pipe()#os.pipe返回的是元组，元组的返回的第一个fd是读，第二个fd是写
        self.stdout = os.pipe()
        self.stdout2 = os.pipe()
        #self.stderr = os.pipe()
        self.instance_id = instance_id
        try:
            self.proc = Popen(
                args = cmd,#命令参数
                shell = False,#是否由shell带动此进程
                stdin = self.stdin[0],#标准输入
                stdout = self.stdout[1],#标准输出
                stderr = self.stdout[1],#标准错误输出
                cwd = cwd
            )
        except Exception as e:
            self.start_success = False
            self.error_msg = e.__str__() + " 在class " + str(type(e)) + " 中"
        else:
            self.start_success = True
            def read_proc_text_to_file(file,fd,fd2,self):
                while True:
                    try:
                        text = os.read(fd,256000)
                        with open(file,"ab") as f:
                            f.write(text)
                        os.write(fd2,text)
                    except Exception:
                        break
                
                def check_proc_is_running(self):
                    while True:
                        if self.proc.poll() != None:
                            self.status = self.proc.poll()
                            os.close(self.stdin[0])
                            os.close(self.stdin[1])
                            os.close(self.stdout[0])
                            os.close(self.stdout[1])
                            return
            self.Thread_read_proc_text_to_file = threading.Thread(
                target = read_proc_text_to_file,
                kwargs = {
                    'file': os.path.abspath("data/InstanceLog/"+self.instance_id+".log"),
                    'fd': self.stdout[0],
                    'fd2': self.stdout2[1],
                    'self': self
                }
            )
            self.Thread_check_proc_is_running = threading.Thread(
                target = check_proc_is_running,
                kwargs = {
                    'self': self
                }
            )
            self.Thread_read_proc_text_to_file.setDaemon(True)
            self.Thread_check_proc_is_running.setDaemon(True)
            self.Thread_read_proc_text_to_file.start()
            self.Thread_check_proc_is_running.start()

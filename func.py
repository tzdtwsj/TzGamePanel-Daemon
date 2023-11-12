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
    proc = None
    status = None
    stdin = None
    stdout = None
    #stderr = None#为了方便，stderr与stdout合并
    def __init__(self,cmd:list):
        self.stdin = os.pipe()#os.pipe返回的是元组，元组的返回的第一个fd是读，第二个fd是写
        self.stdout = os.pipe()
        #self.stderr = os.pipe()
        self.proc = Popen(
            cmd,
            shell = False,
            stdin = self.stdin[0],
            stdout = self.stdout[1],
            stderr = self.stderr[1]
        )

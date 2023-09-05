import time,sqlite3,difflib,ctypes,hjson
import os.path
import win32api,win32gui,win32con
from PIL import ImageGrab,ImageDraw
from io import BytesIO
from PPOCR_api import GetOcrApi
from functools import cmp_to_key

print("================================")
print("源代码: https://github.com/paulzzh/ASMOCR")
print("演示视频: https://www.bilibili.com/video/BV1tm4y1T7Dr")
print("不得用于商业用途 严禁倒卖")
print("================================")
print("请先启动dmm客户端再运行脚本")
print("之后进入小游戏会自动点击")
print("================================")

if os.path.exists("config.json"):
    obj=hjson.load(open("config.json",encoding="utf8"))
    title = obj["title"]
    sub = (obj["sub"]["x"],obj["sub"]["y"])
    retry = (obj["retry"]["x"],obj["retry"]["y"])
    question = (obj["question"]["left"],obj["question"]["top"],obj["question"]["right"],obj["question"]["bottom"])
    topleft = (obj["topleft"]["left"],obj["topleft"]["top"],obj["topleft"]["right"],obj["topleft"]["bottom"])
    topright = (obj["topright"]["left"],obj["topright"]["top"],obj["topright"]["right"],obj["topright"]["bottom"])
    bottomleft = (obj["bottomleft"]["left"],obj["bottomleft"]["top"],obj["bottomleft"]["right"],obj["bottomleft"]["bottom"])
    bottomright = (obj["bottomright"]["left"],obj["bottomright"]["top"],obj["bottomright"]["right"],obj["bottomright"]["bottom"])
else:
    print("WARN: 配置文件不存在 将使用默认DMM端通用配置")
    title = "PrincessConnectReDive"
    
    sub = (1156, 584)
    retry = (950, 655)
    
    question = (32,167,32+678,167+163)
    
    topleft = (32,425,32+320,425+100)
    topright = (395,425,395+320,425+100)
    bottomleft = (32,575,32+320,575+100)
    bottomright = (395,575,395+320,575+100)

b1 = ((topleft[0]+topleft[2])//2, (topleft[1]+topleft[3])//2)
b2 = ((topright[0]+topright[2])//2, (topright[1]+topright[3])//2)
b3 = ((bottomleft[0]+bottomleft[2])//2, (bottomleft[1]+bottomleft[3])//2)
b4 = ((bottomright[0]+bottomright[2])//2, (bottomright[1]+bottomright[3])//2)
bs = [b1,b2,b3,b4]

yes = (b1[0], (b1[1]+b3[1])//2)
no = (b2[0], (b2[1]+b4[1])//2)

print("窗口标题",title)
print("提交按钮",sub)
print("再来按钮",retry)
print("题目区域",question)
print("左上按钮",topleft,b1)
print("右上按钮",topright,b2)
print("左下按钮",bottomleft,b3)
print("右下按钮",bottomright,b4)
print("正确",yes)
print("错误",no)

class Window():
    def __init__(self,hwnd):
        if not hwnd:
            return
        self.hwnd = hwnd
        frame = self.screenshot()
        print("分辨率",frame.size)
        print("基准坐标",(self.xbase,self.ybase))
        draw = ImageDraw.Draw(frame)
        draw.rectangle(question,outline=(255, 0, 0))
        draw.text((question[0],question[1]), "question","red")
        draw.rectangle(topleft,outline=(255, 0, 0))
        draw.text((b1[0],b1[1]), "topleft","red")
        draw.rectangle(topright,outline=(255, 0, 0))
        draw.text((b2[0],b2[1]), "topright","red")
        draw.rectangle(bottomleft,outline=(255, 0, 0))
        draw.text((b3[0],b3[1]), "bottomleft","red")
        draw.rectangle(bottomright,outline=(255, 0, 0))
        draw.text((b4[0],b4[1]), "bottomright","red")
        
        draw.text((yes[0],yes[1]), "yes","red")
        draw.text((no[0],no[1]), "no","red")
        draw.text((sub[0],sub[1]), "sub","red")
        draw.text((retry[0],retry[1]), "retry","red")
        
        frame.save(title+".png", "PNG")
        
    def screenshot(self):
        win32gui.SetForegroundWindow(hwnd)
        x1, y1, x2, y2 = win32gui.GetClientRect(self.hwnd)
        self.width = x2-x1
        self.height = y2-y1

        wx1, wy1, wx2, wy2 = win32gui.GetWindowRect(self.hwnd)
        bx = wx1
        by = wy1
        # normalize to origin
        wx1, wx2 = wx1-wx1, wx2-wx1
        wy1, wy2 = wy1-wy1, wy2-wy1
        # compute border width and title height
        bw = int((wx2-x2)/2.)
        th = wy2-y2-bw
        # calc offset x and y taking into account border and titlebar, screen coordiates of client rect
        sx = bw
        sy = th
        
        self.xbase = bx + sx
        self.ybase = by + sy
        
        left, top = self.xbase, self.ybase
        right, bottom = left + self.width, top + self.height
        
        frame = ImageGrab.grab(bbox=(left, top, right, bottom))
        return frame
    
    def click(self,pos):
        win32gui.SetForegroundWindow(hwnd)
        x=self.xbase+pos[0]
        y=self.ybase+pos[1]
        win32api.SetCursorPos([x,y])
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y)
        win32api.SetCursorPos([x,y])
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y)
        time.sleep(0.5)

class OCR():
    def __init__(self,argument = {'config_path': "models/config_japan.txt"}):
        self.ocr = GetOcrApi(r".\PaddleOCR-json\PaddleOCR-json.exe", argument)
    
    def cmp(t1, t2): #从上到下 从左到右
        if t1[1]<t2[1]:
            return -1
        elif t1[1]>t2[1]:
            return 1
        elif t1[0]<t2[0]:
            return -1
        elif t1[0]>t2[0]:
            return 1
        return 0
    
    def boxesi(boxes):
        temp=[]
        for i in range(len(boxes)):
            box=boxes[i]
            point=box[0]
            x,y=point
            temp.append([x,y,i])
        return temp
    
    def onelineocr(self,frame):
        buffered = BytesIO()
        frame.save(buffered, format="PNG")
        result = self.ocr.runBytes(buffered.getvalue())
        if not result["code"] == 100:
            return ""
        txts = [line["text"] for line in result["data"]]
        boxes = [line["box"] for line in result["data"]]
        
        sorted_points = sorted(OCR.boxesi(boxes), key=cmp_to_key(OCR.cmp))
        texts=""
        for pointi in sorted_points:
            _,_,i=pointi
            texts+=txts[i]
        return texts

#https://github.com/ra1nty/DXcam/issues/30#issuecomment-1250197004
def set_dpi_awareness():
    awareness = ctypes.c_int()
    errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(
        0, ctypes.byref(awareness))
    errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    success = ctypes.windll.user32.SetProcessDPIAware()

def get_windows_bytitle(title_text):
    def _window_callback(hwnd, all_windows):
        all_windows.append((hwnd, win32gui.GetWindowText(hwnd)))
    windows = []
    win32gui.EnumWindows(_window_callback, windows)
    return [(hwnd,title) for hwnd, title in windows if title_text in title]

set_dpi_awareness()

wins=get_windows_bytitle(title)
print("窗口句柄",wins)
print("默认第一个 如匹配不正确请修改配置文件")
hwnd = wins[0][0]
win32gui.SetForegroundWindow(hwnd)
time.sleep(1)
W=Window(hwnd)
O=OCR()


#读小游戏数据
def query_jp_db(query, args=(), one=False):
    #https://stackoverflow.com/questions/3286525/return-sql-table-as-json-in-python
    conn = sqlite3.connect('redive_jp.db')
    cur = conn.cursor()
    cur.execute(query, args)
    r = [dict((cur.description[i][0], value) \
               for i, value in enumerate(row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return (r[0] if r else None) if one else r

asm_data = query_jp_db("select * from asm_data")
asm_true_or_false_data = query_jp_db("select * from asm_true_or_false_data")
asm_4_choice_data = query_jp_db("select * from asm_4_choice_data")
asm_many_answers_data = query_jp_db("select * from asm_many_answers_data")

asm_true_or_false_data_dict = {x["asm_id"]:x for x in asm_true_or_false_data}
asm_4_choice_data_dict = {x["asm_id"]:x for x in asm_4_choice_data}
asm_many_answers_data_dict = {x["asm_id"]:x for x in asm_many_answers_data}


#找到最近似的题目
ques=None
def diff_asm(obj):
    try:
        return difflib.SequenceMatcher(None, obj["detail"], ques).quick_ratio()
    except:
        return 0.0

def diff_ab(a,b):
    return difflib.SequenceMatcher(None, a, b).quick_ratio()


asm_id=None
wait=0
while True:
    frame = W.screenshot()
    
    quesimg = frame.crop(question) #剪裁到只有题目
    
    ques=O.onelineocr(quesimg)
    data = max(asm_data, key=diff_asm, default='')
    score = diff_asm(data)
    if asm_id == data["asm_id"] or score<0.7: #重复或匹配度低
        if wait>=3: #可能结算后了
            W.click(retry)
            wait=0
        time.sleep(2)
        wait+=1
        continue
    
    wait=0
    img1 = frame.crop(topleft) #左上
    img2 = frame.crop(topright) #右上
    img3 = frame.crop(bottomleft) #左下
    img4 = frame.crop(bottomright) #右下
    ansimgs = [img1,img2,img3,img4]
    
    print("================================")
    print("OCR:",ques)
    print("QUE:","{:.2%}".format(score),data["detail"])
    
    time.sleep(0.5) #似乎识别太快了 点太快会点不动
    
    asm_id=data["asm_id"]
    if asm_id<2000000: #判断
        ans = asm_true_or_false_data_dict[asm_id]
        print("ANS:",ans["correct_answer"]==1)
        if ans["correct_answer"]==1:
            W.click(yes)
        else:
            W.click(no)
        
    elif asm_id<3000000: #单选
        ans = asm_4_choice_data_dict[asm_id]
        ans_str=ans["choice_"+str(ans["correct_answer"])]
        print("ANS:",ans_str)
        
        score = 0.0
        best = 0
        ans_ocr = []
        for i in range(4):
            an = O.onelineocr(ansimgs[i])
            ans_ocr.append(an)
            if an == ans_str:
                score = 1.0
                best = i
                break
            if diff_ab(an,ans_str) > score:
                score = diff_ab(an,ans_str)
                best = i
        
        print("OCR:","{:.2%}".format(score),ans_ocr[best])
        W.click(bs[best])
        
    else: #多选
        ans = asm_many_answers_data_dict[asm_id]
        ans_strs = []
        for i in ["1","2","3","4"]:
            if ans["is_correct_"+i]==1:
                ans_strs.append(ans["choice_"+i])
                print("ANS:",ans["choice_"+i])
        
        ans_ocr = []
        for i in range(4):
            an = O.onelineocr(ansimgs[i])
            ans_ocr.append(an)
        scores = []
        bests = []
        for ans_str in ans_strs:
            score = 0.0
            best = 0
            for i in range(4):
                if diff_ab(ans_ocr[i],ans_str) > score:
                    score = diff_ab(ans_ocr[i],ans_str)
                    best = i
            scores.append(score)
            bests.append(best)
        
        for i in range(len(scores)):
            print("OCR:","{:.2%}".format(scores[i]),ans_ocr[bests[i]])
        for i in range(len(scores)):
            W.click(bs[bests[i]])
        
    #print(ans)
    print("================================")
    
    W.click(sub)

import time,sqlite3,difflib,cv2
import win32api,win32gui,win32ui,win32con
import numpy as np
from PPOCR_api import GetOcrApi
from functools import cmp_to_key

print("================================")
print("源代码: https://github.com/paulzzh/ASMOCR")
print("不得用于商业用途 严禁倒卖")
print("================================")
print("请先启动dmm客户端再运行脚本")
print("之后进入小游戏会自动点击")
print("================================")

hwnd = win32gui.FindWindow(None, "PrincessConnectReDive")
win32gui.SetForegroundWindow(hwnd)
left, top, right, bottom = win32gui.GetClientRect(hwnd)
xbase, ybase, _, _ = win32gui.GetWindowRect(hwnd)
width = right - left
height = bottom - top
print(width,height) #DMM端分辨率应该固定是1280x720吧
WDC = win32gui.GetDC(hwnd)
DC = win32ui.CreateDCFromHandle(WDC)
CDC = DC.CreateCompatibleDC()
BMP = win32ui.CreateBitmap()
BMP.CreateCompatibleBitmap(DC, width, height)
CDC.SelectObject(BMP)

yes = (32+170, 550)
no = (32+510, 550)
sub = (1156, 584)
retry = (950, 655)

b1 = (32+170, 475)
b2 = (32+510, 475)
b3 = (32+170, 625)
b4 = (32+510, 625)
bs = [b1,b2,b3,b4]

argument = {'config_path': "models/config_japan.txt"}
ocr = GetOcrApi(r".\PaddleOCR-json\PaddleOCR-json.exe", argument)

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

def click(pos):
    x=xbase+pos[0]
    y=ybase+pos[1]+50
    win32api.SetCursorPos([x,y])
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y)
    win32api.SetCursorPos([x,y])
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y)
    time.sleep(0.5)

def onelineocr(frame):
    result = ocr.runBytes(cv2.imencode('.png', frame)[1].tobytes())
    if not result["code"] == 100:
        return ""
    txts = [line["text"] for line in result["data"]]
    boxes = [line["box"] for line in result["data"]]
    
    sorted_points = sorted(boxesi(boxes), key=cmp_to_key(cmp))
    texts=""
    for pointi in sorted_points:
        _,_,i=pointi
        texts+=txts[i]
    return texts

frameg_old=None
im_show=None
asm_id=None
wait=0
while True:
    CDC.BitBlt((left,top),(width,height),DC,(0,0),win32con.SRCCOPY)
    bitmap=BMP.GetBitmapBits(True)
    frame = np.frombuffer(bitmap, dtype=np.uint8)
    frame.shape = (height, width, 4)
    frame = frame[:,:,:3] #删除alpha通道
    
    quesimg = frame[167:167+163, 32:32+678] #剪裁到只有题目
    
    frameg=cv2.cvtColor(quesimg, cv2.COLOR_BGR2GRAY)
    if frameg_old is not None:
        #判断前后屏相似 如果变化不大那么不进行OCR(太慢了)
        #(score, diff) = compare_ssim(frameg_old, frameg, full=True)
        diff = cv2.absdiff(frameg_old, frameg)
        diff = diff.astype(np.uint8)
        frameg_old=frameg
        if np.count_nonzero(diff)<1000:
            if wait>=3: #可能结算后了
                click(retry)
                wait=0
            time.sleep(2)
            wait+=1
            continue
    wait=0
    frameg_old=frameg
    
    ques=onelineocr(quesimg)
    data = max(asm_data, key=diff_asm, default='')
    score = diff_asm(data)
    if asm_id == data["asm_id"] or score<0.7: #重复或匹配度低
        continue
    
    img1 = frame[425:425+100, 32:32+320] #左上
    img2 = frame[425:425+100, 395:395+320] #右上
    img3 = frame[575:575+100, 32:32+320] #左下
    img4 = frame[575:575+100, 395:395+320] #右下
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
            click(yes)
        else:
            click(no)
        
    elif asm_id<3000000: #单选
        ans = asm_4_choice_data_dict[asm_id]
        ans_str=ans["choice_"+str(ans["correct_answer"])]
        print("ANS:",ans_str)
        
        score = 0.0
        best = 0
        ans_ocr = []
        for i in range(4):
            an = onelineocr(ansimgs[i])
            ans_ocr.append(an)
            if an == ans_str:
                score = 1.0
                best = i
                break
            if diff_ab(an,ans_str) > score:
                score = diff_ab(an,ans_str)
                best = i
        
        print("OCR:","{:.2%}".format(score),ans_ocr[best])
        click(bs[best])
        
    else: #多选
        ans = asm_many_answers_data_dict[asm_id]
        ans_strs = []
        for i in ["1","2","3","4"]:
            if ans["is_correct_"+i]==1:
                ans_strs.append(ans["choice_"+i])
                print("ANS:",ans["choice_"+i])
        
        ans_ocr = []
        for i in range(4):
            an = onelineocr(ansimgs[i])
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
            click(bs[bests[i]])
        
    #print(ans)
    print("================================")
    
    click(sub)

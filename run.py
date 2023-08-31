#https://github.com/paulzzh/ASMOCR
import sqlite3,difflib,cv2
import numpy as np
from adbutils import adb
from paddleocr import PaddleOCR, draw_ocr
from skimage.metrics import structural_similarity as compare_ssim
from functools import cmp_to_key

d = adb.device() #手机开USB调试模式 插数据线连接 手机上要点一下同意
ocr = PaddleOCR(lang="japan")

#设备不同 自行填写 看pos.png
#截个图 拿画图打开 然后选中题目黑色区域 左下角就是要填的参数
x=320
y=220
w=1020
h=280
#下面的不要动了

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

frameg_old=None
im_show=None

while True:
    image = d.screenshot() #截图
    frame = cv2.cvtColor(np.array(image, dtype=np.uint8), cv2.COLOR_RGB2BGR)
    frame = frame[y:y+h, x:x+w] #剪裁到只有题目
    
    frameg=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if frameg_old is not None:
        #判断前后屏相似 如果变化不大那么不进行OCR(太慢了)
        (score, diff) = compare_ssim(frameg_old, frameg, full=True)
        frameg_old=frameg
        #print(score)
        if score>0.98:
            cv2.imshow("w",im_show)
            cv2.waitKey(1)
            continue
    frameg_old=frameg
    
    result = ocr.ocr(frame)
    txts = [detection[1][0] for line in result for detection in line]
    boxes = [detection[0] for line in result for detection in line]
    
    
    sorted_points = sorted(boxesi(boxes), key=cmp_to_key(cmp))
    ques=""
    for pointi in sorted_points:
        _,_,i=pointi
        ques+=txts[i]
    
    #ques = max(txts, key=len, default='')
    print("================================")
    print("OCR:",ques)
    data = max(asm_data, key=diff_asm, default='')
    print("QUE:","{:.2%}".format(diff_asm(data)),data["detail"])
    
    asm_id=data["asm_id"]
    if asm_id<2000000: #判断
        ans = asm_true_or_false_data_dict[asm_id]
        print("ANS:",ans["correct_answer"]==1)
        
    elif asm_id<3000000: #单选
        ans = asm_4_choice_data_dict[asm_id]
        print("ANS:",ans["choice_"+str(ans["correct_answer"])])
        
    else: #多选
        ans = asm_many_answers_data_dict[asm_id]
        for i in ["1","2","3","4"]:
            if ans["is_correct_"+i]==1:
                print("ANS:",ans["choice_"+i])
    #print(ans)
    print("================================")
    
    scores = [detection[1][1] for line in result for detection in line]
    im_show = draw_ocr(frame, boxes, txts, scores)
    cv2.imshow("w",im_show)
    cv2.waitKey(1)

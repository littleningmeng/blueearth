#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
    blueearth.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    blueearth.py从日本的地球同步卫星向日葵8号(Himawari 8 (ひまわり8号)获取高清地球图像，设置为桌面壁纸
    
    关于向日葵8号卫星
    维基百科: https://zh.wikipedia.org/wiki/%E5%90%91%E6%97%A5%E8%91%B58%E8%99%9F
    由H-IIA202火箭在日本时间2014年10月7日14时16分00秒于种子岛宇宙中心发射升空。其后14时43分57秒卫星与火箭成功分离，
    同月16日19时00分确认其进入静止轨道（东经104.7度, 笔者目测大致在澳大利亚中部上空）
    
    制造厂商	三菱电机
    卫星平台	DS2000
    姿态控制	3轴姿态控制
    寿命	    卫星：15年
                观察仪器：8年
    卫星重量	发射时：3.5吨
                进入轨道后：1.3吨
    观察传感器	AHI (Advanced Himawari Imager) 16频段  宇宙环境观察 (SEDA)
    观察频度	全球观察：10分钟/1次
                日本附近：2.5分钟/1次
    静止经纬度	赤道, 东经140.7度附近
    图像传送	使用商用通信卫星传送
    
    CODE BY APACHE(2017/2/27，为了小柠檬的NASA航天梦)
"""

import os
import sys
import time
import json
import qrcode
import threadpool
from cStringIO import StringIO
from urllib import urlopen
from Tkinter import Tk, Label, Button
from PIL import Image, ImageTk

magic_file_name = u"可爱的小柠檬.txt"
daughter_birthday = "20170104"
save_img_file = "earth.jpg"
proportion = 1.78            # width / heith
zoom_level = 4               # image zoom level of himawari8 , curent supported: 1, 2, 4, 8, ..., 20(MAX)
if(len(sys.argv) > 1) and sys.argv[1].startswith("--level"):
    try:
        zoom_level = int(sys.argv[1].split("=")[1])
        print "Using zoom level: %d" % zoom_level
    except:
        pass
            
png_unit_size = 550          # per earth fragment size is 550x550
y_offset = png_unit_size / 2 # y offset when we splice the fragments
png_height = png_unit_size * zoom_level + 2 * y_offset
png_width = int(png_height * proportion)
x_offset = (png_width - png_unit_size * zoom_level) / 2
latest_json_url = "http://himawari8-dl.nict.go.jp/himawari8/img/D531106/latest.json"
earth_templ_url = "http://himawari8.nict.go.jp/img/D531106/{}d/550/{}/{}_{}_{}.png"

pool = threadpool.ThreadPool(64)

tip_at_start = u"""BLUEEARTH STARTED
---------------------------------------------------
  satellite:\thimawari8(ひまわり8号)
launch time:\t2014/10/7
  longitude:\t140.7
   latitude:\t0
     height:\t35,800 KM
---------------------------------------------------
Project by Apache
For my lovely daughter's space exploration dream!

"""
    
########################################################################
proxy_conf = "proxy.txt"
proxy_addr = ""
try:
    proxy_addr = open(proxy_conf, "r").read().strip()       # no check, please set right proxy address
    print "Using proxy: %s" % proxy_addr
except:
    pass
########################################################################

def set_wallpaper(img_path):
    platform = sys.platform
    if platform.startswith("win"):
        import ctypes
        SPI_SETDESKWALLPAPER = 20 
        ctypes.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, img_path, 3)
    else:
        # todo
        pass

def dont_show_qrcode():
    return os.path.exists(magic_file_name) or (len(sys.argv) > 1 and sys.argv[1] == "--%s" % daughter_birthday)
    
def paste_qrcode(target, qrcode_buff):
    if dont_show_qrcode():
       # NO QRCODE WILL BE PASTED
       return
       
    img = Image.open(StringIO(qrcode_buff))
    tw, th = target.size
    qw, qh = img.size
    target.paste(img, (tw - qw, (th - qh) / 2, tw, (th - qh) / 2 + qh))
    
def pop_qrcode_window(qrcode_buff):
    if dont_show_qrcode():
        return 
        
    def on_button_clicked():
        try:
            open(magic_file_name, "w").write("""Hi, guy
If you like this app, a little donation will make it better!
Re-run the app to remove QR-code on your wallpaper""" )
        except:
            pass
            
        finally:
            sys.exit(1)
            
    tk = Tk()
    tk.wm_attributes('-topmost', 1)
    tk.title(u"您的捐助可以让BLUEEARTH做的更好！")
    img2 = Image.open(StringIO(qrcode_buff))
    tk_img = ImageTk.PhotoImage(img2)
    label = Label(tk, image=tk_img)
    label.pack()
    button = Button(tk, text="Don't show this anymore", command=on_button_clicked, bg="green")
    button.pack()
    tk.mainloop()


def safe_urlopen(url):
    try:
        if proxy_addr.startswith("http"):
            res = urlopen(url, proxies={"http": proxy_addr})
        else:
            res = urlopen(url)
        
        return res
        
    except Exception as e:
        print """ERROR:\nNetwork unreachable!
If you have http proxy, please write it to proxy.txt
Thes proxy address format looks like http://xxx.com:8080"""
        raw_input("anykey to quit")
        sys.exit(1)
        
def download_task(url):
    res = safe_urlopen(url)
    open(os.path.basename(url), "wb").write(res.read())
    print "success         %s" % os.path.basename(url)

def update_pilimage_list(datalist, fpath):
    fp = open(fpath, "rb")
    datalist.append((Image.open(fp), fp, fpath))
    
def stitching(urls, zoomlv=zoom_level):
    datalist, index = [], 0
    for url in urls:
        fpath = os.path.basename(url)
        try:
            update_pilimage_list(datalist, fpath)
        except IOError as e:
            print "image file %s error!\ntrying to re-download" % fpath
            try:
                res = safe_urlopen(url)
                open(fpath, "wb").write(res.read())
                update_pilimage_list(datalist, fpath)
                print "repaired:)"
            except Exception as e:
                print "unable to re-download!", e
                return
            
    target = Image.new('RGB', (png_width, png_height))
    x, y = 0, 0
    for i in xrange(len(urls)):
        col = i / zoomlv
        target.paste(datalist[i][0], (x + x_offset + col * png_unit_size,
                               y + y_offset,
                               x + x_offset + png_unit_size + col * png_unit_size,
                               y + png_unit_size + y_offset))
        y += png_unit_size
        if (i + 1) % zoomlv == 0:
            y = 0
        
        datalist[i][1].close()
        try:
            os.remove(datalist[i][2])
        except Exception as e:
            print e


    try:
        paste_qrcode(target, qrcode.qrcode_resource_data)
        target.save(save_img_file, quality=100)
    except Exception as e:
        print e
        print "fail to save image file!! please check your permission"
        sys.exit(1)

    
def get_fragments_by_date(date, time, zoomlv=zoom_level):
    urls = []
    for i in xrange(zoomlv):
        for j in xrange(zoomlv):
            urls.append(earth_templ_url.format(zoomlv, date, time, i, j))
    
    reqs = threadpool.makeRequests(download_task, urls, None)
    [pool.putRequest(req) for req in reqs]
    pool.wait()
    
    return urls
    
def get_latest_fragments(zoomlv=zoom_level):
    res = safe_urlopen(latest_json_url)
    jsonstr = res.read()  # like this: {"date":"2017-02-27 01:20:00","file":"PI_H08_20170227_0120_TRC_FLDK_R10_PGPFD.png"}   
    try:
        datadict = json.loads(jsonstr)
    except Exception as e:
        print "ERROR:\nbad response, maybe you are behind of firewall.\nplease test you network and retry."
        raw_input("anykey to quit")
        sys.exit(1)
        
    datestr = datadict.get("date", "")
    if datestr == "":
        print "bad date string"
        sys.exit(1)
        
    date, time = datestr.split(" ")#"2017-02-27 22:20:00".split(" ")#
    date, time = date.replace("-", "/"), time.replace(":", "")
    return get_fragments_by_date(date, time, zoomlv)
    
def print_tip_at_start():
    t = 0.01
    i = 0
    for ch in tip_at_start:
        if i == 251:
            t = 0.05
        sys.stdout.write(ch), time.sleep(t)
        i += 1
        
def main():
    if sys.platform.startswith("win"):
        os.system("color 0A && title %s" % os.path.basename(sys.argv[0]))

    print_tip_at_start()
    urls = get_latest_fragments(zoom_level)
    stitching(urls)
    set_wallpaper(save_img_file)
    print "Finished, enjoy!!"
    pop_qrcode_window(qrcode.qrcode_resource_data)
    
if __name__ == "__main__":
    main()
    
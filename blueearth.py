#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import gevent
import requests
from gevent import monkey
from PIL import Image
from logger import create_logger


monkey.patch_socket()

log = create_logger(__name__, "history.log")
save_img_file = "earth.png"
proportion = 1            # width / heith
zoom_level = 4            # image zoom level of himawari8 , curent supported: 1, 2, 4, 8, ..., 20(MAX)
if(len(sys.argv) > 1) and sys.argv[1].startswith("--level"):
    try:
        zoom_level = int(sys.argv[1].split("=")[1])
        log.debug("Using zoom level: %d" % zoom_level)
    except ValueError as e:
        pass
            
png_unit_size = 550                   # per earth fragment size is 550x550
y_offset = int(png_unit_size / 2.0)   # y offset when we splice the fragments
png_height = png_unit_size * zoom_level + 2 * y_offset
png_width = int(png_height * proportion)
x_offset = int((png_width - png_unit_size * zoom_level) / 2.0)
latest_json_url = "https://himawari8.nict.go.jp/img/D531106/latest.json"
earth_templ_url = "https://himawari8.nict.go.jp/img/D531106/{}d/550/{}/{}_{}_{}.png"
proxy_conf = "proxy.txt"
proxy_addr = ""
tip_at_start = u"""
  satellite:\thimawari8(ひまわり8号)
launch time:\t2014/10/7
  longitude:\t140.7
   latitude:\t0
     height:\t35,800 KM
---------------------------------------------------
especially for my lovely daughter's space exploration dream!

"""

if os.path.exists(proxy_conf):
    try:
        with open(proxy_conf, "r") as f:
            proxy_addr = f.read().strip()
            log.debug("Using proxy: %s" % proxy_addr)
    except IOError as e1:
        log.error("fail to load proxy")


def safe_urlopen(url):
    try:
        return requests.get(url, proxies={"http": proxy_addr}) if proxy_addr.startswith("http") else requests.get(url)
    except requests.exceptions.ConnectionError as e1:
        log.error("""Network unreachable! Exp: %s
If you have http proxy, please write it to proxy.txt
proxy example: http://xxx.com:8080""" % e1)
        sys.exit(1)


def download_task(url):
    res = safe_urlopen(url)
    with open(os.path.basename(url), "wb") as fp:
        fp.write(res.content)
    log.info("success    %s" % os.path.basename(url))


def update_pilimage_list(datalist, fpath):
    fp = open(fpath, "rb")
    datalist.append((Image.open(fp), fp, fpath))


def stitching(urls, zoomlv=zoom_level):
    datalist, index = [], 0
    for url in urls:
        fpath = os.path.basename(url)
        try:
            update_pilimage_list(datalist, fpath)
        except IOError as e1:
            log.error("image file %s error! Exp: %s, trying to re-download" % (e1, fpath))
            res = safe_urlopen(url)
            with open(fpath, "wb") as fp:
                fp.write(res.content)
            update_pilimage_list(datalist, fpath)
            log.debug("repaired:)")
            
    target = Image.new('RGB', (int(png_width), int(png_height)))
    x, y = 0, 0
    for i in range(len(urls)):
        col = int(i / zoomlv)
        target.paste(datalist[i][0], (int(x + x_offset + col * png_unit_size), int(y + y_offset),
                                      int(x + x_offset + png_unit_size + col * png_unit_size),
                                      int(y + png_unit_size + y_offset)))
        y += png_unit_size
        if (i + 1) % zoomlv == 0:
            y = 0
        
        datalist[i][1].close()
        try:
            os.remove(datalist[i][2])
        except Exception as e:
            log.debug("fali to remove tmp files. Exp: %s" % repr(e))

    target.save(save_img_file, quality=100)

    
def get_fragments_by_date(date, time, zoomlv=zoom_level):
    urls = []
    for i in range(zoomlv):
        for j in range(zoomlv):
            urls.append(earth_templ_url.format(zoomlv, date, time, i, j))

    threads = [gevent.spawn(download_task, url) for url in urls]
    gevent.joinall(threads)
    return urls


def get_latest_fragments(zoomlv=zoom_level):
    res = safe_urlopen(latest_json_url)
    if res.status_code != 200:
        log.error(f"{res}")
    # json data format: {"date":"2017-02-27 01:20:00","file":"PI_H08_20170227_0120_TRC_FLDK_R10_PGPFD.png"}
    json_data = res.json()
    date_str = json_data.get("date", "")
    if date_str == "":
        log.error("bad date string")
        sys.exit(1)
    date, t = date_str.split(" ")
    date, t = date.replace("-", "/"), t.replace(":", "")
    return get_fragments_by_date(date, t, zoomlv)


def main():
    print(tip_at_start)
    urls = get_latest_fragments(zoom_level)
    stitching(urls)
    log.info("done")


if __name__ == "__main__":
    main()

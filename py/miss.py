# -*- coding: utf-8 -*-
import json
import re
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        self.host = config.get('site', 'https://missav.ws').rstrip('/')
        self.base_path = "/dm194/cn"
        
        # 配置无头浏览器模式（不弹出窗口）
        self.co = ChromiumOptions()
        self.co.set_argument('--no-sandbox')
        self.co.set_argument('--headless')  # 如果调试可以注释掉这行看浏览器操作
        self.co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

    def get_html_with_browser(self, url):
        """核心：使用浏览器内核过盾并获取 HTML"""
        page = ChromiumPage(self.co)
        try:
            page.get(url)
            # 等待关键元素加载，这会自动处理 5 秒盾
            if page.wait.ele_displayed('.thumbnail', timeout=10):
                return page.html
            return page.html
        finally:
            page.quit()

    def homeContent(self, filter):
        url = f"{self.host}{self.base_path}/new"
        html = self.get_html_with_browser(url)
        doc = pq(html)
        
        classes = [
            {"type_id": "new", "type_name": "最近更新"},
            {"type_id": "chinese-subtitle", "type_name": "中文字幕"},
            {"type_id": "uncensored-leak", "type_name": "无码流出"},
            {"type_id": "genres/uncensored", "type_name": "无码影片"}
        ]
        
        return {
            'class': classes,
            'list': self.parse_list(doc),
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}{self.base_path}/{tid}?page={pg}"
        html = self.get_html_with_browser(url)
        doc = pq(html)
        return {
            'list': self.parse_list(doc),
            'page': int(pg)
        }

    def parse_list(self, doc):
        videos = []
        items = doc('.thumbnail').items()
        for item in items:
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            a_tag = item('a').last()
            href = a_tag.attr('href') or ""
            vod_id = href.rstrip('/').split('/')[-1]
            
            if vod_id:
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": (a_tag.attr('title') or item('h2').text() or "影片").strip(),
                    "vod_pic": img if img.startswith('http') else "https:" + img if img.startswith('//') else "",
                    "vod_remarks": item('.duration').text() or ""
                })
        return videos

    def detailContent(self, ids):
        mid = ids[0]
        url = f"{self.host}/{mid}"
        # 详情页也需要过盾
        page = ChromiumPage(self.co)
        page.get(url)
        html = page.html
        doc = pq(html)
        
        # 提取 m3u8
        m3u8 = ""
        match = re.search(r"source\s*=\s*'(https?://[^']+?\.m3u8[^']*)'", html)
        if match:
            m3u8 = match.group(1)
        
        page.quit()

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text().strip(),
            "vod_pic": doc('video').attr('poster') or "",
            "vod_play_from": "MissAV",
            "vod_play_url": f"播放链接${m3u8 if m3u8 else '嗅探$' + url}"
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0 if "m3u8" in id else 1,
            "url": id.split('$')[-1],
            "header": "" # 浏览器模式下 header 往往已在 Cookie 中集成
        }

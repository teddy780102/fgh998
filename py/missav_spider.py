"""
==================================================
@Spider Name : MissAV
@Author      : 飞鱼
@Version     : 1.0.1
@Description : TVBox/CatVod MissAV Spider Plugin
==================================================
"""

import json
import sys
import re
import base64
from urllib.parse import urljoin, quote, unquote
from pyquery import PyQuery as pq

# 兼容 Spider 基础类导入
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    author = "飞鱼"
    version = "1.0.1"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://missav02.xyz/'
    }
    
    # 轮询域名列表（优先使用用户指定的 missav02.xyz）
    domains = [
        'https://missav02.xyz',
        'https://missav.app'
    ]

    def getDependence(self):
        return ['pyquery']

    def getName(self):
        return "MissAV (by 飞鱼)"

    def init(self, extend=""):
        print(f"[{self.getName()}] 插件加载成功 | 作者: {self.author} | 版本: {self.version}")

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def action(self, action):
        pass

    # 核心轮询请求工具：支持多域名故障转移
    def _fetch_with_fallback(self, path):
        for domain in self.domains:
            full_url = urljoin(domain, path)
            try:
                rsp = self.fetch(full_url, headers=self.headers)
                if rsp and rsp.status_code == 200 and 'Just a moment...' not in rsp.text:
                    return rsp.text, domain
            except Exception:
                continue
        return None, self.domains[0]

    # 通用视频列表卡片解析器逻辑
    def _parse_cards(self, doc, base_domain):
        videos = []
        items = doc('div.grid > div, div.thumbnail, div.item, .relative.group')
        if len(items) == 0:
            items = doc('a[href*="/videos/"], a[href*="/voddetail/"]')
            
        for item in items.items():
            a_tag = item if item.is_('a') else item('a').eq(0)
            img_tag = item('img').eq(0)
            
            href = a_tag.attr('href')
            if not href:
                continue
                
            vod_id = href.replace(base_domain, "")
            
            vod_name = img_tag.attr('alt') or item('.title').text() or item('h3').text() or "未知影片"
            vod_pic = img_tag.attr('data-src') or img_tag.attr('src') or ""
            if vod_pic and not vod_pic.startswith('http'):
                vod_pic = urljoin(base_domain, vod_pic)
                
            vod_remarks = item('.duration').text() or item('.date').text() or ""

            videos.append({
                "vod_id": vod_id,
                "vod_name": vod_name.strip(),
                "vod_pic": vod_pic,
                "vod_remarks": vod_remarks.strip()
            })
        return videos

    # 1. 首页推荐数据 & 分类菜单
    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_name": "国产", "type_id": "20"},
            {"type_name": "日本有码", "type_id": "21"},
            {"type_name": "日本无码", "type_id": "22"},
            {"type_name": "中文字幕", "type_id": "28"},
            {"type_name": "欧美", "type_id": "23"},
            {"type_name": "动漫", "type_id": "24"},
            {"type_name": "伦理", "type_id": "25"}
        ]
        result['class'] = classes

        filters = {
            "20": [{"key": "cateId", "name": "分类", "value": [{"v": "20", "n": "全部"}, {"v": "26", "n": "国产精品"}, {"v": "27", "n": "国产剧情"}, {"v": "29", "n": "国产自拍"}, {"v": "35", "n": "国产主播"}, {"v": "85", "n": "国模私拍"}, {"v": "91", "n": "网红明星"}, {"v": "105", "n": "国产SM"}, {"v": "107", "n": "台湾辣妹"}, {"v": "108", "n": "香港正妹"}]}],
            "21": [{"key": "cateId", "name": "分类", "value": [{"v": "21", "n": "全部"}, {"v": "31", "n": "人妻"}, {"v": "44", "n": "素人"}, {"v": "46", "n": "口爆颜射"}, {"v": "47", "n": "萝莉少女"}, {"v": "48", "n": "美乳巨乳"}, {"v": "52", "n": "制服诱惑"}, {"v": "57", "n": "调教"}, {"v": "58", "n": "出轨"}, {"v": "101", "n": "有码精品"}]}],
            "22": [{"key": "cateId", "name": "分类", "value": [{"v": "22", "n": "全部"}, {"v": "102", "n": "无码精品"}]}],
            "23": [{"key": "cateId", "name": "分类", "value": [{"v": "23", "n": "全部"}, {"v": "104", "n": "欧美精品"}]}],
            "24": [{"key": "cateId", "name": "分类", "value": [{"v": "24", "n": "全部"}, {"v": "103", "n": "动漫精品"}]}],
            "25": [{"key": "cateId", "name": "分类", "value": [{"v": "25", "n": "全部"}, {"v": "39", "n": "综合三级"}]}],
            "28": [{"key": "cateId", "name": "分类", "value": [{"v": "28", "n": "全部"}, {"v": "51", "n": "日本中字"}]}]
        }
        if filter:
            result['filters'] = filters

        try:
            html, base_domain = self._fetch_with_fallback("/label/new/")
            if html:
                doc = pq(html)
                result['list'] = self._parse_cards(doc, base_domain)
            else:
                result['list'] = []
        except Exception:
            result['list'] = []

        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    # 2. 分类列表数据处理
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        page = int(pg)
        target_cate_id = extend.get('cateId', tid) if extend else tid
        
        path = f"/vodtype/{target_cate_id}-{page}/" if target_cate_id.isdigit() else f"/genres/{target_cate_id}?page={page}"
        
        try:
            html, base_domain = self._fetch_with_fallback(path)
            if html:
                doc = pq(html)
                result['list'] = self._parse_cards(doc, base_domain)
                result['page'] = page
                result['pagecount'] = page + 1
                result['limit'] = 20
                result['total'] = 9999
            else:
                result['list'] = []
        except Exception:
            result['list'] = []

        return result

    # 3. 详情页解析
    def detailContent(self, array):
        vod_id = array[0]
        result = {}
        
        try:
            html, base_domain = self._fetch_with_fallback(vod_id)
            if not html:
                return {"list": []}
                
            doc = pq(html)
            
            title = doc('h1').text() or doc('.title').text() or "未获取到名称"
            pic = doc('video').attr('poster') or doc('img.cover').attr('src') or ""
            if pic and not pic.startswith('http'):
                pic = urljoin(base_domain, pic)
                
            type_name = doc('.category, .genre').text() or ""
            actor = doc('.actors, .actor').text() or "内详"
            remark = doc('.release-date, .date').text() or ""
            desc = doc('.description, .summary').text() or "暂无简介。"
            
            vod = {
                "vod_id": vod_id,
                "vod_name": title.strip(),
                "vod_pic": pic,
                "type_name": type_name.strip(),
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": remark.strip(),
                "vod_actor": actor.strip(),
                "vod_director": "内详",
                "vod_content": desc.strip()
            }
            
            vod["vod_play_from"] = "MissAV"
            vod["vod_play_url"] = f"立即播放${vod_id}"
            
            result['list'] = [vod]
        except Exception as e:
            result['list'] = []

        return result

    # 4. 搜索功能
    def searchContent(self, key, quick, pg="1"):
        result = {}
        encoded_key = quote(key)
        path = f"/search/{encoded_key}?page={pg}"
        
        try:
            html, base_domain = self._fetch_with_fallback(path)
            if html:
                doc = pq(html)
                result['list'] = self._parse_cards(doc, base_domain)
            else:
                result['list'] = []
        except Exception:
            result['list'] = []
            
        return result

    # 5. 播放地址解析
    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            html, base_domain = self._fetch_with_fallback(id)
            if not html:
                return {"parse": 0, "url": ""}
                
            m3u8_match = re.search(r"window\.source_url\s*=\s*['"]([^'"]+\.m3u8[^'"]*)['"]", html)
            if not m3u8_match:
                m3u8_match = re.search(r"url['"]\s*:\s*['"]([^'"]+\.m3u8[^'"]*)['"]", html)
            if not m3u8_match:
                m3u8_match = re.search(r"['"](https?://[^'"]+\.m3u8[^'"]*)['"]", html)
                
            if m3u8_match:
                video_url = m3u8_match.group(1)
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = video_url
                result["header"] = json.dumps(self.headers)
            else:
                full_url = urljoin(base_domain, id)
                result["parse"] = 1
                result["url"] = full_url
                result["header"] = json.dumps(self.headers)
        except Exception:
            result = {"parse": 0, "url": ""}
            
        return result
"""
==================================================
@Spider Name : MissAV
@Author      : 飞鱼
@Version     : 1.0.3
@Description : TVBox/CatVod MissAV 最新改版高兼容插件
==================================================
"""

import json
import sys
import re
from urllib.parse import urljoin, quote

# 兼容 Spider 基础类导入
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    author = "飞鱼"
    version = "1.0.3"

    # 使用高仿真主流浏览器请求头，提供 Referer 绕过底层反爬规则
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://missav02.xyz'
    }
    
    # 轮询域名列表：优先请求你本地测试秒开的最新节点
    domains = [
        'https://missav02.xyz',
        'https://missav.app',
        'https://missav.ai'
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

    # 核心轮询请求工具，支持多域名故障转移
    def _fetch_with_fallback(self, path):
        for domain in self.domains:
            full_url = urljoin(domain, path)
            try:
                rsp = self.fetch(full_url, headers=self.headers)
                if rsp and rsp.status_code == 200 and 'Just a moment...' not in rsp.text:
                    return rsp.text, domain
            except Exception:
                continue
        return None, self.domains

    # 通用视频列表卡片解析器逻辑
    def _parse_cards(self, doc, base_domain):
        videos = []
        
        # 精准匹配包含视频卡片的核心元素节点（包括最新版的响应式 grid 盒子）
        items = doc('div.grid > div, div.thumbnail, .relative.group, a[href*="/videos/"]')
        
        for item in items.items():
            # 确保定位到正确的 a 标签
            a_tag = item if item.is_('a') else item('a[href*="/videos/"]').eq(0)
            if not a_tag:
                a_tag = item('a').eq(0)
                
            href = a_tag.attr('href')
            if not href:
                continue
                
            # 过滤并提取标准化 vod_id
            vod_id = href.replace(base_domain, "")
            if not vod_id.startswith('/'):
                vod_id = '/' + vod_id
            
            img_tag = item('img').eq(0)
            
            # 【重要】修复不显示内容的核心：必须优先提取 data-src 懒加载海报属性
            vod_pic = img_tag.attr('data-src') or img_tag.attr('src') or ""
            if vod_pic and not vod_pic.startswith('http'):
                vod_pic = urljoin(base_domain, vod_pic)
                
            # 提取标题，多重节点机制防留空
            vod_name = img_tag.attr('alt') or item('h3').text() or item('.title').text() or "未知影片"
            
            # 提取影片时长或上架日期作为角标备注
            vod_remarks = ""
            duration_node = item('.duration') or item('span.absolute')
            if duration_node:
                vod_remarks = duration_node.text()
            
            # 只把有效视频加入列表，跳过干扰分类链接
            if '/videos/' in vod_id:
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name.strip(),
                    "vod_pic": vod_pic,
                    "vod_remarks": v_remarks if 'v_remarks' in locals() else vod_remarks.strip()
                })
                
        # 兜底提取逻辑：捕捉顶层可能遗漏的大图推荐位
        if len(videos) == 0:
            for a_sub in doc('a[href*="/videos/"]').items():
                sub_href = a_sub.attr('href')
                sub_img = a_sub('img').eq(0)
                if sub_href and sub_img:
                    v_id = sub_href.replace(base_domain, "")
                    v_name = sub_img.attr('alt') or "推荐影片"
                    v_pic = sub_img.attr('data-src') or sub_img.attr('src') or ""
                    if v_pic and not v_pic.startswith('http'):
                        v_pic = urljoin(base_domain, v_pic)
                    videos.append({
                        "vod_id": v_id if v_id.startswith('/') else '/' + v_id,
                        "vod_name": v_name.strip(),
                        "vod_pic": v_pic,
                        "vod_remarks": "推荐"
                    })
                    
        # 内存级终极去重，防止网格节点重复渲染
        seen = set()
        unique_videos = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique_videos.append(v)
                
        return unique_videos

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
            # 最新更新页面包含最全的视频瀑布流列表
            html, base_domain = self._fetch_with_fallback("/label/new/")
            if html:
                from pyquery import PyQuery as pq
                doc = pq(html)
                result['list'] = self._parse_cards(doc, base_domain)
            else:
                result['list'] = []
        except Exception:
            result['list'] = []

        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    # 2. 分类页面列表数据处理
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        page = int(pg)
        target_cate_id = extend.get('cateId', tid) if extend else tid
        
        # 兼容老版整型 ID 路由及新版混合字母路由
        path = f"/vodtype/{target_cate_id}-{page}/" if target_cate_id.isdigit() else f"/genres/{target_cate_id}?page={page}"
        
        try:
            html, base_domain = self._fetch_with_fallback(path)
            if html:
                from pyquery import PyQuery as pq
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
        vod_id = array if isinstance(array, list) else array
        result = {}
        
        try:
            html, base_domain = self._fetch_with_fallback(vod_id)
            if not html:
                return {"list": []}
                
            from pyquery import PyQuery as pq
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
            
            vod["vod_play_from"] = "MissAV_Line"
            vod["vod_play_url"] = f"立即播放${vod_id}"
            
            result['list'] = [vod]
        except Exception:
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
                from pyquery import PyQuery as pq
                doc = pq(html)
                result['list'] = self._parse_cards(doc, base_domain)

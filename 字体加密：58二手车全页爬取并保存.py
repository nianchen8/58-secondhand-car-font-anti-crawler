import os
import re
import base64
import time
import random
import requests
from lxml import etree
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
import easyocr
import numpy as np
from openpyxl import Workbook


class SecondHandCar:
    def __init__(self):
        self.session = requests.Session()
        self.text = ''
        self.html = ''
        self.mapping = {}
        self.reader = easyocr.Reader(['en'], gpu=False)
        self.decrypted = []
        self.total_pages = 1
        self.query_suffix = ''          # 存储从分页器提取的查询参数

        # 从您提供的 curl 中提取的 Cookies
        cookies_str = (
            'f=n; commontopbar_new_city_info=414%7C%E9%95%BF%E6%B2%99%7Ccs; '
            'commontopbar_ipcity=wh%7C%E6%AD%A6%E6%B1%89%7C0; userid360_xml=F2C30B03BBEDD62C07692E26AD3F2834; '
            'time_create=1777697643257; fzq_h=4ff8188125c45e15bfcae18c0a2551c4_1775057939990_8963f8eb072b488bac5f836cf380afb5_47905484756815153562959247610675686328; '
            'id58=uWi+aWnNPBNCD5X0BQmAAg==; 58home=hg; city=hg; 58tj_uuid=1032b838-2c96-47b5-8c51-384dc1c2801d; '
            'als=0; sessionid=39b299af-fcaf-4a11-bd77-57658f17863b; 58ua=58pc; wmda_uuid=2b0a5583df92b87cbd3678b600678470; '
            'wmda_new_uuid=1; wmda_visited_projects=%3B1732038237441; xxzlclientid=e4c73769-f504-44dc-a284-1775105643892; '
            'f=n; xxzlxxid=pfmxu9V5HIZqNGqlYSBJkx0OiIWY5Gt/bhBbYS23Q/xTd+cmqqdIxuBgrahR+WBlECSz; new_uv=4; '
            'utm_source=; spm=; new_session=0; init_refer=; '
            'wmda_session_id_1732038237441=1775120774949-00ef0cbf-e3ae-465f-b7b7-bfc092491f61; '
            'fzq_js_usdt_infolist_car=e58c01cebd55d869dcf7cd18e22b28c4_1775121693483_6; wmda_report_times=5; '
            'xxzlbbid=pfmbROfC4crZ9Scdl68vx3ua4gb0JIDGcTOP8jj3kgEEm1kTOSTpwDYkDFXeC942LvRzqdwLAShq76HD0GjWlJVAd46HA0BTduidynQPuuenu30LLpkS8VK4d+VUqijABj2ox1uMOwYxNzc1MTIxNjk0NTk0MTA1_1'
        )
        self.cookies = {}
        for item in cookies_str.split('; '):
            if '=' in item:
                key, value = item.split('=', 1)
                self.cookies[key] = value

        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
            'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        self.session.headers.update(self.headers)

    def get_html(self, url, referer=None, retry=3):
        for attempt in range(retry):
            try:
                req_headers = self.headers.copy()
                if referer:
                    req_headers['Referer'] = referer
                response = self.session.get(url, cookies=self.cookies, headers=req_headers, timeout=10)
                print(f"[DEBUG] 请求 {url} 状态码: {response.status_code}, 内容长度: {len(response.text)}")
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response.text
                else:
                    print(f"状态码异常: {response.status_code}, 重试 {attempt+1}/{retry}")
                    time.sleep(2)
            except Exception as e:
                print(f"请求异常: {e}, 重试 {attempt+1}/{retry}")
                time.sleep(2)
        raise Exception(f"无法获取 {url}，已重试 {retry} 次")

    def get_page_num(self):
        match = re.search(r'____usedCar\.totalPage\s*=\s*"(\d+)"', self.text)
        if match:
            total = int(match.group(1))
            print(f"从JavaScript变量获取到总页数: {total}")
            return total
        page_numbers = self.html.xpath(
            '//div[@class="pager"]//a/span/text() | //div[@class="pager"]/strong/span/text()'
        )
        if page_numbers:
            try:
                max_page = max([int(num) for num in page_numbers if num.isdigit()])
                print(f"从分页器获取到总页数: {max_page}")
                return max_page
            except:
                pass
        print("无法获取总页数，默认1页")
        return 1

    def extract_query_params(self):
        """从第一页的分页器中提取查询参数（用于后续页）"""
        # 查找第二页的链接
        second_page_link = self.html.xpath('//div[@class="pager"]/a[1]/@href')
        if second_page_link:
            href = second_page_link[0]
            # 提取 '?' 后面的部分
            if '?' in href:
                query = href.split('?', 1)[1]
                # 去除可能包含的页码参数（如 pn2，但查询字符串中一般没有页码）
                self.query_suffix = '?' + query
                print(f"提取到查询参数: {self.query_suffix}")
                return
        # 如果没找到，使用第一页 URL 中的查询参数（如果有）
        if '?' in self.current_first_url:
            self.query_suffix = '?' + self.current_first_url.split('?', 1)[1]
        else:
            # 默认添加 needHpCityTest=true
            self.query_suffix = '?needHpCityTest=true'

    def get_data(self):
        cards = self.html.xpath('//div[@class="info--wrap"]/ancestor::li[1]')
        print(f"[DEBUG] 本页通过XPath找到 {len(cards)} 个卡片")
        if len(cards) == 0:
            cards = self.html.xpath('//li[contains(@class,"car_list")]')
            print(f"[DEBUG] 备用XPath找到 {len(cards)} 个卡片")

        particulars = []
        for card in cards:
            title = card.xpath('.//span[@class="info_link"]/text()')
            title = title[0].strip() if title else ''
            label = card.xpath('.//div[@class="tags h-clearfix"]/span/text()')
            label = [l.strip() for l in label]
            params_list = card.xpath('.//div[@class="info_params"]/text()')
            params = ' '.join([p.strip() for p in params_list]) if params_list else ''
            price = card.xpath('.//div[@class="info--price"]/b/text()')
            price = price[0].strip() if price else ''
            particulars.append({
                'title': title,
                'label': label,
                'params': params,
                'price': price,
            })
        if particulars:
            print(f"[DEBUG] 本页成功解析 {len(particulars)} 条数据，示例价格: {particulars[0]['price']}")
        return particulars

    def get_font(self):
        p = re.compile(r"url\(['\"]?data:application/font-ttf;charset=utf-8;base64,([^'\"\)]+)", re.DOTALL)
        data = p.findall(self.text)
        if not data:
            raise Exception("未找到字体 Base64 数据")
        with open('font.ttf', 'wb') as f:
            f.write(base64.b64decode(data[0]))

    def build_map(self):
        font = TTFont('./font.ttf')
        cmap = font.getBestCmap()
        try:
            pil_font = ImageFont.truetype('./font.ttf', 100)
        except:
            pil_font = ImageFont.load_default()
        self.mapping.clear()
        for code_point in cmap.keys():
            img = Image.new('RGB', (300, 300), "white")
            draw = ImageDraw.Draw(img)
            draw.text((30, 30), chr(code_point), font=pil_font, fill="black")
            result = self.reader.readtext(np.array(img), detail=0)
            if result and result[0]:
                recognized = result[0][0]
                if recognized in '0123456789.万':
                    self.mapping[chr(code_point)] = recognized
        print(f"当前页字体映射表(仅数字相关): {self.mapping}")

    def decrypt(self, text):
        if not text:
            return ''
        result = []
        for ch in text:
            if ch in self.mapping:
                result.append(self.mapping[ch])
            else:
                result.append(ch)
        return ''.join(result)

    def clear_cache(self):
        if os.path.exists('./font.ttf'):
            os.remove('./font.ttf')

    def save_to_excel(self, filename="58二手车_全量.xlsx"):
        wb = Workbook()
        ws = wb.active
        ws.title = "二手车信息"
        headers = ["标题", "标签", "上牌年份/里程", "价格(万元)"]
        ws.append(headers)
        for item in self.decrypted:
            label_str = ", ".join(item['label']) if item['label'] else ""
            row = [item['title'], label_str, item['params'], item['price']]
            ws.append(row)
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 15
        wb.save(filename)
        print(f"数据已保存到 {filename}，共 {len(self.decrypted)} 条记录。")

    def run(self, test_mode=True, max_test_pages=5):
        first_url = 'https://cs.58.com/ershouche/'
        self.current_first_url = first_url
        print("正在获取第一页，以确定总页数...")
        self.text = self.get_html(first_url)
        self.html = etree.HTML(self.text)
        self.total_pages = self.get_page_num()
        print(f"检测到总页数：{self.total_pages}")

        # 从第一页中提取查询参数（用于后续页）
        self.extract_query_params()

        if test_mode:
            max_pages = min(self.total_pages, max_test_pages)
            print(f"测试模式：仅爬取前 {max_pages} 页")
        else:
            max_pages = self.total_pages

        all_data = []
        for page in range(1, max_pages + 1):
            print(f"\n========== 正在爬取第 {page} 页 ==========")
            if page == 1:
                url = first_url
                referer = None
            else:
                # 使用提取的查询参数构造 URL
                url = f'https://cs.58.com/ershouche/pn{page}/{self.query_suffix}'
                referer = first_url
            try:
                self.text = self.get_html(url, referer=referer)
                self.html = etree.HTML(self.text)

                try:
                    self.get_font()
                    self.build_map()
                    self.clear_cache()
                except Exception as e:
                    print(f"字体处理失败: {e}，可能本页无加密价格，继续...")

                page_data = self.get_data()
                for item in page_data:
                    decrypted_item = {
                        'title': item['title'],
                        'label': item['label'],
                        'params': item['params'],
                        'price': self.decrypt(item['price'])
                    }
                    all_data.append(decrypted_item)

                print(f"第 {page} 页爬取完成，当前累计 {len(all_data)} 条数据。")
                delay = random.uniform(3, 6)
                print(f"等待 {delay:.2f} 秒...")
                time.sleep(delay)
            except Exception as e:
                print(f"第 {page} 页爬取失败: {e}")
                continue

        self.decrypted = all_data
        self.save_to_excel()


if __name__ == '__main__':
    scraper = SecondHandCar()
    # 测试模式只爬前5页，确认无误后改为 test_mode=False 全量爬取
    # scraper.run(test_mode=True, max_test_pages=5)
    # 全量爬取所有页
    scraper.run(test_mode=False)
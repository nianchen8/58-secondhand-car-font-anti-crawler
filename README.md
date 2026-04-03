# 58-secondhand-car-font-anti-crawler
解决58同城二手车字体反爬的Python爬虫，自动解密价格并导出Excel
# 58同城二手车字体反爬数据采集

解决58同城二手车字体反爬的Python爬虫，自动解密价格并导出Excel。

## 功能特点

- 自动解析总页数，支持全站爬取
- 破解字体反爬（woff/ttf动态字体）
- 使用OCR（easyocr）识别加密字符，建立映射
- 自动清理临时字体文件
- 导出结构化Excel报表

## 技术栈

- Python 3.x
- requests / lxml
- fontTools / Pillow / easyocr
- openpyxl

## 使用方法

1. 安装依赖：
   ```bash
   pip install requests lxml fontTools easyocr Pillow numpy openpyxl

  
  运行脚本：

python 字体加密：58二手车全页爬取并保存.py

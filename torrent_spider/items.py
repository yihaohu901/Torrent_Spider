# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TorrentItem(scrapy.Item):
    """定义Torrent数据项目结构"""
    # 种子名称
    name = scrapy.Field()
    # 种子链接地址
    torrent_url = scrapy.Field()
    # 磁力链接
    magnet_url = scrapy.Field()
    # 文件大小
    size = scrapy.Field()
    # 种子数
    seeders = scrapy.Field()
    # 下载数
    leechers = scrapy.Field()
    # 上传时间
    upload_time = scrapy.Field()
    # 分类
    category = scrapy.Field()
    # 视频长度/时长
    duration = scrapy.Field()
    # 描述
    description = scrapy.Field()
    # 来源网站
    source_url = scrapy.Field()
    # 爬取时间
    crawl_time = scrapy.Field()
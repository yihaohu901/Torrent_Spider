# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json
import csv
import sqlite3
import os
from datetime import datetime
from itemadapter import ItemAdapter


class TorrentSpiderPipeline:
    """基础数据处理管道"""
    
    def process_item(self, item, spider):
        if item is None:
            return None
        adapter = ItemAdapter(item)
        
        # 数据清理和验证
        if adapter.get('name'):
            adapter['name'] = adapter['name'].strip()
        
        # 确保必要字段存在
        if not adapter.get('name'):
            adapter['name'] = 'Unknown'
        
        if not adapter.get('crawl_time'):
            adapter['crawl_time'] = datetime.now().isoformat()
        
        return item


class JsonWriterPipeline:
    """JSON文件输出管道"""
    
    def open_spider(self, spider):
        # 从spider设置中获取文件名，如果没有则使用默认值
        filename = getattr(spider, 'json_file', 'torrents.json')
        # 确保输出目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.file = open(filename, 'w', encoding='utf-8')
        self.file.write('[\r\n')
        self.first_item = True
        self.items = []
    
    def close_spider(self, spider):
        self.file.write('\r\n]')
        self.file.close()
    
    def process_item(self, item, spider):
        if item is None:
            return None
        if not self.first_item:
            self.file.write(',\r\n')
        else:
            self.first_item = False
        
        line = json.dumps(ItemAdapter(item).asdict(), ensure_ascii=False, indent=2)
        self.file.write(line)
        return item


class CsvWriterPipeline:
    """CSV文件输出管道"""
    
    def open_spider(self, spider):
        # 从spider设置中获取文件名，如果没有则使用默认值
        filename = getattr(spider, 'csv_file', 'torrents.csv')
        # 确保输出目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.file = open(filename, 'w', newline='', encoding='utf-8')
        self.fieldnames = [
            'name', 'torrent_url', 'magnet_url', 'size', 'seeders', 
            'leechers', 'upload_time', 'category', 'duration', 'description', 
            'source_url', 'crawl_time'
        ]
        self.writer = csv.DictWriter(self.file, fieldnames=self.fieldnames)
        self.writer.writeheader()
    
    def close_spider(self, spider):
        self.file.close()
    
    def process_item(self, item, spider):
        if item is None:
            return None
        adapter = ItemAdapter(item)
        # 确保所有字段都存在
        row = {}
        for field in self.fieldnames:
            row[field] = adapter.get(field, '')
        self.writer.writerow(row)
        return item


class SqlitePipeline:
    """SQLite数据库存储管道"""
    
    def open_spider(self, spider):
        # 从spider设置中获取文件名，如果没有则使用默认值
        filename = getattr(spider, 'sqlite_file', 'torrents.db')
        # 确保输出目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.connection = sqlite3.connect(filename)
        self.cursor = self.connection.cursor()
        
        # 创建表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS torrents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                torrent_url TEXT,
                magnet_url TEXT,
                size TEXT,
                seeders INTEGER,
                leechers INTEGER,
                upload_time TEXT,
                category TEXT,
                duration TEXT,
                description TEXT,
                source_url TEXT,
                crawl_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.connection.commit()
    
    def close_spider(self, spider):
        self.connection.close()
    
    def process_item(self, item, spider):
        if item is None:
            return None
        adapter = ItemAdapter(item)
        
        # 插入数据
        insert_sql = '''
            INSERT INTO torrents (
                name, torrent_url, magnet_url, size, seeders, leechers,
                upload_time, category, duration, description, source_url, crawl_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        values = (
            adapter.get('name', ''),
            adapter.get('torrent_url', ''),
            adapter.get('magnet_url', ''),
            adapter.get('size', ''),
            adapter.get('seeders', 0),
            adapter.get('leechers', 0),
            adapter.get('upload_time', ''),
            adapter.get('category', ''),
            adapter.get('duration', ''),
            adapter.get('description', ''),
            adapter.get('source_url', ''),
            adapter.get('crawl_time', '')
        )
        
        self.cursor.execute(insert_sql, values)
        self.connection.commit()
        
        return item


class DuplicatesPipeline:
    """去重管道"""
    
    def __init__(self):
        self.seen_urls = set()
        self.seen_magnets = set()
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # 检查重复的种子URL
        torrent_url = adapter.get('torrent_url')
        if torrent_url and torrent_url in self.seen_urls:
            spider.logger.info(f"Duplicate torrent URL found: {torrent_url}")
            return None
        elif torrent_url:
            self.seen_urls.add(torrent_url)
        
        # 检查重复的磁力链接
        magnet_url = adapter.get('magnet_url')
        if magnet_url and magnet_url in self.seen_magnets:
            spider.logger.info(f"Duplicate magnet URL found: {magnet_url}")
            return None
        elif magnet_url:
            self.seen_magnets.add(magnet_url)
        
        return item


class FilterPipeline:
    """过滤管道"""
    
    def __init__(self):
        # 默认过滤条件，会被spider配置覆盖
        self.min_seeders = 0
        self.blocked_keywords = ['spam', 'fake', 'virus']
    
    def open_spider(self, spider):
        """从spider获取过滤配置"""
        if hasattr(spider, 'filter_config'):
            config = spider.filter_config
            self.min_seeders = config.get('min_seeders', 0)
            self.blocked_keywords = config.get('blocked_keywords', ['spam', 'fake', 'virus'])
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # 过滤种子数太少的项目
        seeders = adapter.get('seeders', 0)
        if isinstance(seeders, int) and seeders < self.min_seeders:
            spider.logger.info(f"Filtered item with low seeders: {seeders}")
            return None
        
        # 过滤包含屏蔽关键词的项目
        name = adapter.get('name', '').lower()
        for keyword in self.blocked_keywords:
            if keyword in name:
                spider.logger.info(f"Filtered item with blocked keyword '{keyword}': {name}")
                return None
        
        return item
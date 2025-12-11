#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Torrent Spider - 使用Scrapy爬取网站上的torrents链接地址

使用方法:
1. 基本使用: python app.py
2. 指定URL: python app.py --urls "http://example.com,http://another.com"
3. 指定输出格式: python app.py --output json  # 支持: json, csv, sqlite, all

"""

import os
import sys
import json
import argparse
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from torrent_spider.spiders.torrent_spider import TorrentSpider


def apply_timestamp(config):
    """为配置文件中的文件名应用时间戳"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 处理输出设置中的文件名
    if 'output_settings' in config:
        for key, filename in config['output_settings'].items():
            if isinstance(filename, str) and '{timestamp}' in filename:
                config['output_settings'][key] = filename.replace('{timestamp}', timestamp)
    
    return config


def load_config(config_file='config.json'):
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)
    
    # 默认配置
    default_config = {
        "default_urls": [],
        "spider_settings": {
            "download_delay": 2.0,
            "concurrent_requests": 1,
            "output_format": "all",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
        "filter_settings": {
            "min_seeders": 0,
            # "blocked_keywords": ["spam", "fake", "virus"],
            "max_pages": 10
        },
        "output_settings": {
            "json_file": "torrents.json",
            "csv_file": "torrents.csv",
            "sqlite_file": "torrents.db"
        }
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置和用户配置
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                    elif isinstance(default_config[key], dict):
                        for subkey in default_config[key]:
                            if subkey not in config[key]:
                                config[key][subkey] = default_config[key][subkey]
                
                # 处理时间戳替换
                config = apply_timestamp(config)
                return config
        else:
            print(f"配置文件 {config_file} 不存在，使用默认配置")
            return apply_timestamp(default_config)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        print("使用默认配置")
        return apply_timestamp(default_config)


def setup_pipelines(output_format='all'):
    """根据输出格式配置管道"""
    pipelines = {
        'torrent_spider.pipelines.TorrentSpiderPipeline': 100,
        'torrent_spider.pipelines.DuplicatesPipeline': 200,
        'torrent_spider.pipelines.FilterPipeline': 250,
    }
    
    if output_format in ['json', 'all']:
        pipelines['torrent_spider.pipelines.JsonWriterPipeline'] = 300
    
    if output_format in ['csv', 'all']:
        pipelines['torrent_spider.pipelines.CsvWriterPipeline'] = 400
    
    if output_format in ['sqlite', 'all']:
        pipelines['torrent_spider.pipelines.SqlitePipeline'] = 500
    
    return pipelines


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Torrent Spider - 爬取种子链接')
    parser.add_argument(
        '--urls', 
        type=str, 
        help='要爬取的URL列表，用逗号分隔（覆盖配置文件中的设置）',
        default=''
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='配置文件路径 (默认: config.json)'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        choices=['json', 'csv', 'sqlite', 'all'],
        help='输出格式（覆盖配置文件中的设置）',
        default='all'
    )
    parser.add_argument(
        '--delay',
        type=float,
        help='请求延迟时间（秒）（覆盖配置文件中的设置）'
    )
    parser.add_argument(
        '--concurrent',
        type=int,
        help='并发请求数（覆盖配置文件中的设置）'
    )
    
    args = parser.parse_args()
    
    # 加载配置文件
    config = load_config(args.config)
    
    # 合并命令行参数和配置文件设置（命令行参数优先）
    output_format = args.output if args.output else config['spider_settings']['output_format']
    delay = args.delay if args.delay is not None else config['spider_settings']['download_delay']
    concurrent = args.concurrent if args.concurrent is not None else config['spider_settings']['concurrent_requests']
    
    # 获取项目设置
    settings = get_project_settings()
    
    # 配置管道
    settings.set('ITEM_PIPELINES', setup_pipelines(output_format))
    
    # 配置请求延迟和并发
    settings.set('DOWNLOAD_DELAY', delay)
    settings.set('CONCURRENT_REQUESTS', concurrent)
    settings.set('CONCURRENT_REQUESTS_PER_DOMAIN', concurrent)
    
    # 配置用户代理
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en',
        'User-Agent': config['spider_settings']['user_agent']
    })
    
    # 创建爬虫进程
    process = CrawlerProcess(settings)
    
    # 处理URL参数
    if args.urls:
        urls = args.urls.split(',')
    else:
        urls = config['default_urls']
        if not urls:
            print("警告: 没有指定要爬取的URL")
            print("请在配置文件中设置 default_urls 或使用 --urls 参数指定要爬取的网站")
            print("例如:")
            print("python app.py --urls \"https://example.com,https://another.com\"")
            print("或者编辑 config.json 文件中的 default_urls 字段")
            print("\\n注意: 请确保遵守网站的robots.txt和使用条款")
            return
    
    print(f"开始爬取以下网站:")
    for url in urls:
        print(f"  - {url}")
    print(f"输出格式: {output_format}")
    print(f"请求延迟: {delay}秒")
    print(f"并发数: {concurrent}")
    print(f"配置文件: {args.config}")
    print("-" * 50)
    
    # 记录开始时间
    start_time = datetime.now()
    # print(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 启动爬虫，传递配置参数
    process.crawl(
        TorrentSpider, 
        urls=','.join(urls),
        json_file=config['output_settings']['json_file'],
        csv_file=config['output_settings']['csv_file'],
        sqlite_file=config['output_settings']['sqlite_file'],
        filter_config=config['filter_settings']
    )
    process.start()
    
    # 记录结束时间并计算耗时
    end_time = datetime.now()
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())
    
    print("\r\n爬取完成!")
    print(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"任务结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总共耗时: {total_seconds}秒 ({duration})")
    print("输出文件:")
    if output_format in ['json', 'all'] and os.path.exists(config['output_settings']['json_file']):
        print(f"  - {config['output_settings']['json_file']}")
    if output_format in ['csv', 'all'] and os.path.exists(config['output_settings']['csv_file']):
        print(f"  - {config['output_settings']['csv_file']}")
    if output_format in ['sqlite', 'all'] and os.path.exists(config['output_settings']['sqlite_file']):
        print(f"  - {config['output_settings']['sqlite_file']}")


def show_examples():
    """显示使用示例"""
    examples = '''
使用示例:

1. 使用配置文件中的默认设置:
   python app.py

2. 指定要爬取的网站（覆盖配置文件）:
   python app.py --urls "https://example.com"

3. 爬取多个网站:
   python app.py --urls "https://site1.com,https://site2.com"

4. 使用自定义配置文件:
   python app.py --config my_config.json

5. 只输出JSON格式（覆盖配置文件）:
   python app.py --output json

6. 设置请求延迟和并发数（覆盖配置文件）:
   python app.py --delay 3 --concurrent 2

配置文件示例 (config.json):
{
  "default_urls": [
    "https://example-torrent-site.com"
  ],
  "spider_settings": {
    "download_delay": 2.0,
    "concurrent_requests": 1,
    "output_format": "all"
  }
}

注意事项:
- 配置文件使用JSON格式，请确保语法正确
- 命令行参数会覆盖配置文件中的相应设置
- 请确保遵守目标网站的robots.txt和使用条款
- 建议设置适当的请求延迟，避免对服务器造成过大压力
- 某些网站可能需要额外的反爬虫处理
- 请仅用于合法用途
'''
    print(examples)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_examples()
    else:
        main()
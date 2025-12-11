import scrapy
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from torrent_spider.items import TorrentItem


class TorrentSpider(scrapy.Spider):
    name = 'torrents'
    allowed_domains = []  # 将根据start_urls自动设置
    
    # 示例网站列表 - 用户可以根据需要修改
    start_urls = [
        # 'https://example-torrent-site.com',  # 请替换为实际的种子网站
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }
    
    def __init__(self, urls=None, json_file=None, csv_file=None, sqlite_file=None, filter_config=None, *args, **kwargs):
        super(TorrentSpider, self).__init__(*args, **kwargs)
        if urls:
            # 支持通过命令行参数传入URL
            self.start_urls = urls.split(',')
        
        # 自动设置allowed_domains
        self.allowed_domains = [urlparse(url).netloc for url in self.start_urls]
        
        # 设置输出文件名
        if json_file:
            self.json_file = json_file
        if csv_file:
            self.csv_file = csv_file
        if sqlite_file:
            self.sqlite_file = sqlite_file
        
        # 设置过滤配置
        if filter_config:
            self.filter_config = filter_config
        else:
            self.filter_config = {
                'min_seeders': 0,
                'blocked_keywords': ['spam', 'fake', 'virus'],
                'max_pages': 10
            }
    
    def start_requests(self):
        """生成初始请求"""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'source_url': url}
            )
    
    def parse(self, response):
        """解析主页面，查找种子链接"""
        source_url = response.meta.get('source_url', response.url)
        
        # 检查是否是RARBG种子详情页
        if 'rarbg' in response.url.lower() and '/torrent/' in response.url:
            # 直接解析RARBG详情页
            yield from self.parse_rarbg_detail(response)
            return
        
        # 检查是否是RARBG搜索页面
        if 'rarbg' in response.url.lower() and '/search/' in response.url:
            # 解析RARBG搜索页面
            yield from self.parse_rarbg_search(response)
            return
        
        # 通用的种子链接选择器
        torrent_selectors = [
            'a[href$=".torrent"]',  # 直接的.torrent文件链接
            'a[href*="download"]',   # 包含download的链接
            'a[href*="torrent"]',    # 包含torrent的链接
            'a[href*="magnet:"]',    # 磁力链接
        ]
        
        # 查找种子链接
        for selector in torrent_selectors:
            links = response.css(selector)
            for link in links:
                href = link.css('::attr(href)').get()
                if href:
                    # 处理相对链接
                    full_url = urljoin(response.url, href)
                    
                    # 如果是磁力链接，直接提取
                    if href.startswith('magnet:'):
                        yield self.create_torrent_item(link, response, magnet_url=href, source_url=source_url)
                    # 如果是.torrent文件
                    elif href.endswith('.torrent') or 'download' in href.lower():
                        yield self.create_torrent_item(link, response, torrent_url=full_url, source_url=source_url)
        
        # 查找详情页链接进行进一步爬取
        detail_links = response.css('a[href*="details"], a[href*="view"], a[href*="torrent/"]::attr(href)').getall()
        for link in detail_links[:10]:  # 限制详情页数量
            full_url = urljoin(response.url, link)
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_detail,
                meta={'source_url': source_url}
            )
        
        # 查找分页链接
        next_page_selectors = [
            'a[href*="page"]:contains("Next")',
            'a[href*="page"]:contains("下一页")',
            'a.next::attr(href)',
            'a[rel="next"]::attr(href)',
        ]
        
        for selector in next_page_selectors:
            next_page = response.css(selector).get()
            if next_page:
                yield scrapy.Request(
                    url=urljoin(response.url, next_page),
                    callback=self.parse,
                    meta={'source_url': source_url}
                )
                break  # 只跟踪一个下一页链接
    
    def parse_rarbg_detail(self, response):
        """专门解析RARBG详情页面"""
        source_url = response.meta.get('source_url', response.url)
        
        # 检查是否有从搜索页面传递过来的基本信息
        base_item = response.meta.get('base_item')
        if base_item:
            # 使用搜索页面的基本信息
            item = base_item
        else:
            # 创建新的种子项目
            item = TorrentItem()
            
            # 提取标题 - RARBG特定选择器
            title = response.css('h2::text').get()
            if not title:
                title = response.css('title::text').get()
                if title:
                    title = title.replace(' - RARBG', '').strip()
            
            item['name'] = self.clean_text(title) if title else 'Unknown'
            item['source_url'] = source_url or response.url
            item['crawl_time'] = datetime.now().isoformat()
        
        # 查找下载链接
        download_link = response.css('a[href*="download.php"]::attr(href)').get()
        if download_link:
            item['torrent_url'] = urljoin(response.url, download_link)
        
        # 查找磁力链接
        magnet_link = response.css('a[href^="magnet:"]::attr(href)').get()
        if magnet_link:
            item['magnet_url'] = magnet_link
        
        # 提取页面文本进行信息挖掘
        page_text = response.text
        
        # 提取文件大小
        size_match = re.search(r'Size[:\s]*([0-9.]+\s*[KMGT]?B)', page_text, re.IGNORECASE)
        if size_match:
            item['size'] = size_match.group(1)
        
        # 提取种子数和下载数
        seeders_match = re.search(r'Seeders[:\s]*([0-9]+)', page_text, re.IGNORECASE)
        if seeders_match:
            item['seeders'] = int(seeders_match.group(1))
        
        leechers_match = re.search(r'Leechers[:\s]*([0-9]+)', page_text, re.IGNORECASE)
        if leechers_match:
            item['leechers'] = int(leechers_match.group(1))
        
        # 提取上传时间
        upload_time_match = re.search(r'Uploaded[:\s]*([^<\n]+)', page_text, re.IGNORECASE)
        if upload_time_match:
            item['upload_time'] = upload_time_match.group(1).strip()
        
        # 提取分类
        category_match = re.search(r'Category[:\s]*([^<\n]+)', page_text, re.IGNORECASE)
        if category_match:
            item['category'] = category_match.group(1).strip()
        
        # 提取视频长度/时长
        duration_patterns = [
            r'Duration[:\s]*([0-9]+:[0-9]+)',         # Duration: MM:SS格式 (优先)
            r'Duration[:\s]*([0-9]+:[0-9]+:[0-9]+)',  # Duration: HH:MM:SS格式
            r'Runtime[:\s]*([0-9]+:[0-9]+:[0-9]+)',   # Runtime: HH:MM:SS
            r'Runtime[:\s]*([0-9]+:[0-9]+)',          # Runtime: MM:SS
            r'Length[:\s]*([0-9]+:[0-9]+:[0-9]+)',    # Length: HH:MM:SS
            r'Length[:\s]*([0-9]+:[0-9]+)',           # Length: MM:SS
            r'Time[:\s]*([0-9]+:[0-9]+:[0-9]+)',      # Time: HH:MM:SS
            r'Time[:\s]*([0-9]+:[0-9]+)',             # Time: MM:SS
            r'([0-9]+:[0-9]+:[0-9]+)',                # 直接匹配HH:MM:SS格式
            r'Duration[:\s]*([0-9]+\s*min)',          # Duration: XX min
            r'Runtime[:\s]*([0-9]+\s*min)',           # Runtime: XX min
            r'([0-9]+\s*min\s*[0-9]*\s*sec)',        # XX min XX sec格式
        ]
        
        for pattern in duration_patterns:
            duration_match = re.search(pattern, page_text, re.IGNORECASE)
            if duration_match:
                item['duration'] = duration_match.group(1).strip()
                break
        
        yield item
    
    def parse_rarbg_search(self, response):
        """解析RARBG搜索页面，批量提取torrent链接"""
        source_url = response.meta.get('source_url', response.url)
        
        # 根据网页结构，RARBG搜索页面的torrent链接在表格中
        # 每一行包含一个torrent的信息
        torrent_rows = response.css('table tr')
        
        # 调试：打印页面内容和找到的行数
        self.logger.info(f"Found {len(torrent_rows)} table rows")
        
        for row in torrent_rows[1:]:  # 跳过表头
            # 提取torrent名称和链接 - 尝试多种选择器
            name_cell = row.css('td a[href*="/torrent/"]')
            if not name_cell:
                # 尝试其他可能的选择器
                name_cell = row.css('td:nth-child(2) a')
            if not name_cell:
                continue
                
            torrent_name = name_cell.css('::text').get()
            torrent_detail_url = name_cell.css('::attr(href)').get()
            
            if torrent_name and torrent_detail_url:
                # 构建完整的详情页URL
                full_detail_url = urljoin(response.url, torrent_detail_url)
                
                # 提取基本信息
                cells = row.css('td')
                if len(cells) >= 8:
                    category = cells[0].css('::text').get() or ''
                    size = cells[4].css('::text').get() or ''
                    seeders_text = cells[5].css('::text').get() or '0'
                    leechers_text = cells[6].css('::text').get() or '0'
                    upload_time = cells[3].css('::text').get() or ''
                    # 清理数据
                    try:
                        seeders = int(seeders_text.strip()) if seeders_text.strip().isdigit() else 0
                        leechers = int(leechers_text.strip()) if leechers_text.strip().isdigit() else 0
                    except:
                        seeders = 0
                        leechers = 0
                    
                    # 创建基本的torrent item
                    item = TorrentItem()
                    item['name'] = self.clean_text(torrent_name)
                    item['source_url'] = full_detail_url
                    item['crawl_time'] = datetime.now().isoformat()
                    item['size'] = self.clean_text(size)
                    item['seeders'] = seeders
                    item['leechers'] = leechers
                    item['upload_time'] = self.clean_text(upload_time)
                    item['category'] = self.clean_text(category)
                    
                    # 发起请求获取详细信息（包括磁力链接和duration）
                    yield scrapy.Request(
                        url=full_detail_url,
                        callback=self.parse_rarbg_detail,
                        meta={
                            'source_url': source_url,
                            'base_item': item  # 传递基本信息
                        }
                    )
        
        # 查找下一页链接
        next_page_links = response.css('a[href*="/search/"]:contains("next"), a[href*="/search/"]:contains("下一页"), a[href*="/search/"]:contains(">")')
        for next_link in next_page_links:
            next_url = next_link.css('::attr(href)').get()
            if next_url and 'search' in next_url:
                full_next_url = urljoin(response.url, next_url)
                yield scrapy.Request(
                    url=full_next_url,
                    callback=self.parse_rarbg_search,
                    meta={'source_url': source_url}
                )
                break  # 只跟踪一个下一页链接
    
    def parse_detail(self, response):
        """解析详情页面"""
        source_url = response.meta.get('source_url', response.url)
        
        # 在详情页查找更精确的种子信息
        torrent_links = response.css('a[href$=".torrent"], a[href*="download"]')
        magnet_links = response.css('a[href^="magnet:"]')
        
        # 提取种子链接
        for link in torrent_links:
            href = link.css('::attr(href)').get()
            if href:
                full_url = urljoin(response.url, href)
                item = self.create_detailed_torrent_item(response, torrent_url=full_url, source_url=source_url)
                if item:
                    yield item
        
        # 提取磁力链接
        for link in magnet_links:
            href = link.css('::attr(href)').get()
            if href:
                item = self.create_detailed_torrent_item(response, magnet_url=href, source_url=source_url)
                if item:
                    yield item
    
    def create_torrent_item(self, link_element, response, torrent_url=None, magnet_url=None, source_url=None):
        """创建基础的种子项目"""
        item = TorrentItem()
        
        # 提取名称
        name = link_element.css('::text').get() or link_element.css('::attr(title)').get()
        item['name'] = self.clean_text(name) if name else 'Unknown'
        
        item['torrent_url'] = torrent_url
        item['magnet_url'] = magnet_url
        item['source_url'] = source_url or response.url
        item['crawl_time'] = datetime.now().isoformat()
        
        return item
    
    def create_detailed_torrent_item(self, response, torrent_url=None, magnet_url=None, source_url=None):
        """创建详细的种子项目"""
        item = TorrentItem()
        
        # 尝试提取标题
        title_selectors = [
            'h1::text',
            '.title::text',
            '#title::text',
            'title::text'
        ]
        
        name = None
        for selector in title_selectors:
            name = response.css(selector).get()
            if name:
                break
        
        item['name'] = self.clean_text(name) if name else 'Unknown'
        item['torrent_url'] = torrent_url
        item['magnet_url'] = magnet_url
        item['source_url'] = source_url or response.url
        item['crawl_time'] = datetime.now().isoformat()
        
        # 尝试提取文件大小
        size_patterns = [
            r'Size[:\s]*([0-9.]+\s*[KMGT]?B)',
            r'大小[:\s]*([0-9.]+\s*[KMGT]?B)',
            r'([0-9.]+\s*[KMGT]B)',
        ]
        
        page_text = response.text
        for pattern in size_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                item['size'] = match.group(1)
                break
        
        # 尝试提取种子数和下载数
        seeders_pattern = r'Seed[ers]*[:\s]*([0-9]+)'
        leechers_pattern = r'Leech[ers]*[:\s]*([0-9]+)'
        
        seeders_match = re.search(seeders_pattern, page_text, re.IGNORECASE)
        if seeders_match:
            item['seeders'] = int(seeders_match.group(1))
        
        leechers_match = re.search(leechers_pattern, page_text, re.IGNORECASE)
        if leechers_match:
            item['leechers'] = int(leechers_match.group(1))
        
        # 尝试提取描述
        description_selectors = [
            '.description::text',
            '#description::text',
            '.content::text',
        ]
        
        for selector in description_selectors:
            description = response.css(selector).get()
            if description:
                item['description'] = self.clean_text(description)
                break
        
        return item
    
    def clean_text(self, text):
        """清理文本"""
        if not text:
            return ''
        return re.sub(r'\s+', ' ', text.strip())
    
    def parse_magnet_link(self, magnet_url):
        """解析磁力链接获取更多信息"""
        # 从磁力链接中提取哈希值和名称
        info = {}
        if magnet_url and magnet_url.startswith('magnet:'):
            # 提取名称
            name_match = re.search(r'dn=([^&]+)', magnet_url)
            if name_match:
                info['name'] = name_match.group(1).replace('+', ' ')
            
            # 提取哈希值
            hash_match = re.search(r'xt=urn:btih:([a-fA-F0-9]+)', magnet_url)
            if hash_match:
                info['hash'] = hash_match.group(1)
        
        return info
# Torrent Spider - 种子链接爬虫

使用Scrapy框架开发的通用种子链接爬虫，可以从各种种子网站爬取torrents链接地址。

## 功能特性

- 🕷️ 基于Scrapy框架，高效稳定
- 🔗 支持爬取.torrent文件链接和磁力链接
- 📊 多种输出格式：JSON、CSV、SQLite数据库
- 🚫 内置去重和过滤功能
- ⚙️ 可配置的爬取参数
- 🛡️ 内置反爬虫保护机制

## 项目结构

```
torrent_spider/
├── scrapy.cfg              # Scrapy项目配置
├── requirements.txt        # 项目依赖
├── app.py                  # 主运行脚本
├── config.json             # 配置文件
├── README.md               # 项目说明
└── torrent_spider/         # 爬虫项目包
    ├── __init__.py
    ├── settings.py         # Scrapy设置
    ├── items.py            # 数据项目定义
    ├── pipelines.py        # 数据处理管道
    └── spiders/            # 爬虫目录
        ├── __init__.py
        └── torrent_spider.py  # 主爬虫类
```

## 安装依赖

```bash
# 激活虚拟环境（如果使用）
# Windows
myenv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 配置文件设置

首先编辑 `config.json` 文件，设置默认的爬取网站和参数：

```json
{
  "default_urls": [
    "https://example-torrent-site.com",
    "https://another-torrent-site.com"
  ],
  "spider_settings": {
    "download_delay": 2.0,
    "concurrent_requests": 1,
    "output_format": "all",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  },
  "filter_settings": {
    "min_seeders": 0,
    "blocked_keywords": ["spam", "fake", "virus"],
    "max_pages": 10
  },
  "output_settings": {
    "json_file": "output/torrents_{timestamp}.json",
    "csv_file": "output/torrents_{timestamp}.csv",
    "sqlite_file": "output/torrents_{timestamp}.db"
  }
}
```

### 基本使用

```bash
# 使用配置文件中的默认设置
python app.py

# 指定要爬取的网站（覆盖配置文件）
python app.py --urls "https://example-torrent-site.com"

# 爬取多个网站
python app.py --urls "https://site1.com,https://site2.com"
```

### 高级选项

```bash
# 指定输出格式
python app.py --urls "https://example.com" --output json

# 使用自定义配置文件
python app.py --config my_config.json

# 设置请求延迟和并发数
python app.py --urls "https://example.com" --delay 3 --concurrent 2

# 查看帮助信息
python app.py --help
```

### 命令行参数

- `--urls`: 要爬取的URL列表，用逗号分隔
- `--config`: 配置文件路径 (默认: config.json)
- `--output`: 输出格式，支持 json/csv/sqlite/all（默认：all）
- `--delay`: 请求延迟时间，单位秒（默认：2.0）
- `--concurrent`: 并发请求数（默认：1）

## 输出文件

爬取完成后，会在项目的 `output` 文件夹下生成以下文件（文件名包含时间戳）：

- `output/torrents_YYYYMMDD_HHMMSS.json`: JSON格式的种子数据
- `output/torrents_YYYYMMDD_HHMMSS.csv`: CSV格式的种子数据
- `output/torrents_YYYYMMDD_HHMMSS.db`: SQLite数据库文件

**时间戳格式说明：**
- `YYYYMMDD`: 年月日（如：20231018）
- `HHMMSS`: 时分秒（如：143025）
- 完整示例：`torrents_20231018_143025.json`

## 数据字段

每个种子项目包含以下字段：

| 字段名 | 描述 |
|--------|------|
| name | 种子名称 |
| torrent_url | .torrent文件下载链接 |
| magnet_url | 磁力链接 |
| size | 文件大小 |
| seeders | 种子数 |
| leechers | 下载数 |
| upload_time | 上传时间 |
| category | 分类 |
| description | 描述 |
| source_url | 来源网站 |
| crawl_time | 爬取时间 |

## 配置说明

### 时间戳功能

项目支持自动为输出文件添加时间戳，避免文件覆盖：

- 在配置文件中使用 `{timestamp}` 占位符
- 程序运行时会自动替换为当前时间戳
- 时间戳格式：`YYYYMMDD_HHMMSS`（年月日_时分秒）
- 示例：`torrents_{timestamp}.json` → `torrents_20231018_143025.json`

### 爬虫设置

可以在 `torrent_spider/settings.py` 中修改以下设置：

- `DOWNLOAD_DELAY`: 请求延迟
- `CONCURRENT_REQUESTS`: 并发请求数
- `USER_AGENT`: 用户代理
- `ROBOTSTXT_OBEY`: 是否遵守robots.txt

### 数据管道

在 `torrent_spider/pipelines.py` 中包含多个数据处理管道：

- `TorrentSpiderPipeline`: 基础数据清理
- `DuplicatesPipeline`: 去重处理
- `FilterPipeline`: 数据过滤
- `JsonWriterPipeline`: JSON输出
- `CsvWriterPipeline`: CSV输出
- `SqlitePipeline`: SQLite数据库存储

## 注意事项

⚠️ **重要提醒**

1. **合法使用**: 请确保仅用于合法用途，遵守相关法律法规
2. **网站条款**: 使用前请阅读目标网站的robots.txt和使用条款
3. **请求频率**: 建议设置适当的请求延迟，避免对服务器造成过大压力
4. **反爬虫**: 某些网站可能有反爬虫机制，需要额外处理
5. **数据准确性**: 爬取的数据可能不完整或不准确，请谨慎使用

## 扩展开发

### 添加新的种子网站支持

1. 在 `torrent_spider/spiders/torrent_spider.py` 中修改 `start_urls`
2. 根据网站结构调整CSS选择器
3. 添加特定的解析逻辑

### 自定义数据处理

1. 在 `pipelines.py` 中添加新的管道类
2. 在 `settings.py` 中注册新管道
3. 实现自定义的数据处理逻辑

## 故障排除

### 常见问题

1. **ImportError**: 确保已安装所有依赖包
2. **网络错误**: 检查网络连接和目标网站可访问性
3. **解析错误**: 目标网站结构可能已变化，需要更新选择器
4. **权限错误**: 确保有写入文件的权限

### 调试模式

```bash
# 启用详细日志
export SCRAPY_SETTINGS_MODULE=torrent_spider.settings
scrapy crawl torrents -L DEBUG
```

## 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。您可以在遵守许可证条款的前提下自由使用、修改和分发本项目的代码。使用者需自行承担使用风险，并确保遵守相关法律法规。

## 更新日志

- v1.0.0: 初始版本，支持基本的种子链接爬取功能

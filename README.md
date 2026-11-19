# so.qq.com SearXNG 自定义搜索引擎

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![SearXNG](https://img.shields.io/badge/SearXNG-custom%20engine-blue)](https://github.com/searxng/searxng)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

> SearXNG custom search engine for **so.qq.com (Tencent Yuanbao Search / 腾讯元宝搜索)**.
> Pure Python stdlib, no dependencies, no browser, no API key. Covers web, academic,
> WeChat official-account articles (公众号), video, government, media and images.
> 关键词 / keywords: searxng, searxng custom engine, so.qq.com, 元宝搜索, 腾讯搜索,
> 公众号搜索, wechat article search, meta search engine, Chinese search.


把腾讯元宝搜索（[so.qq.com](https://so.qq.com)）接进 SearXNG 的自定义引擎。纯 Python 标准库实现，**无第三方依赖**，解析页面内嵌数据（Next.js RSC 数据流 / `__INITIAL_STATE__`），不调用浏览器、不需要登录、不需要 API Key。

海外 IP 实测可直接访问 so.qq.com（HTTP 200，无反爬拦截），比爬取百度网页接口稳定。

## 功能

一个引擎覆盖元宝搜索的全部搜索分类，每个分类注册为独立引擎，可在 SearXNG 界面/API 分别选用：

| 引擎名 | 分类 | 说明 | 实测条数 |
|---|---|---|---|
| `soqq` | general | 综合网页搜索 | 12–15 |
| `soqq xueshu` | general | 学术科普（期刊论文、来源、日期）| 4 |
| `soqq weixin` | general | **公众号文章**（真实 mp.weixin.qq.com 链接、作者、日期）| 29 |
| `soqq video` | general | 视频号（作者、描述、export 链接）| 40 |
| `soqq gov` | general | 组织机构（政府/官方站点）| 11–13 |
| `soqq media` | general | 主流媒体（央媒/权威媒体）| 9 |
| `soqq images` | images | 图片（原图、缩略图、来源页、尺寸）| 48 |

## 安装

环境要求：SearXNG（Docker 部署，本文以容器名 `searxng`、宿主机配置目录 `/root/searxng/` 为例）。

### 1. 复制引擎文件进容器

```bash
docker cp engines/soqq.py        searxng:/usr/local/searxng/searx/engines/soqq.py
docker cp engines/soqq_images.py searxng:/usr/local/searxng/searx/engines/soqq_images.py
```

### 2. 注册引擎

把 [settings_snippet.yml](settings_snippet.yml) 的内容加入宿主机的 `/root/searxng/settings.yml` 中 `engines:` 列表里（注意保持 YAML 缩进一致）。

每个引擎共用 `engine: soqq`（图片是 `soqq_images`），靠 `soqq_tab` 选项区分分类。如果只想要某几个功能，删掉对应的条目即可。

### 3. 重启并验证

```bash
docker restart searxng

# 引擎是否注册成功
curl -s http://127.0.0.1:8081/config | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print([e['name'] for e in d['engines'] if e['name'].startswith('soqq')])"

# 公众号搜索测试
curl -s -X POST http://127.0.0.1:8081/search \
  --data-urlencode 'q=新能源汽车' -d 'format=json&engines=soqq_weixin' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('results:', len(d.get('results',[])))"
```

返回 `results:` 后面是正数即成功。若 `unresponsive_engines` 有报错，先看启动日志：

```bash
docker logs --tail 60 searxng 2>&1 | grep -iE "can't register|field is missing"
```

## 项目结构

```
.
├── engines/
│   ├── soqq.py          # 主引擎：6 个 general 分类（RSC 解析）
│   └── soqq_images.py   # 图片引擎（__INITIAL_STATE__ 解析）
├── settings_snippet.yml # SearXNG 注册配置
├── tests/
│   ├── test_mcp.py      # MCP 方案连通性测试（历史参考）
│   └── fixtures/        # 真实页面快照，用于回归测试
└── references/          # 参考的 GitHub 项目源码副本（.gitignore 忽略，不入库）
```

## 实现来源

整合了以下开源项目的方法（源码副本见 `references/`）：

- [JoxAnde/soqq-search-api](https://github.com/JoxAnde/soqq-search-api) — RSC 数据流解析、字段提取
- [27Aaron/yuanban_so_mcp](https://github.com/27Aaron/yuanban_so_mcp) — 分类参数、图片 `__INITIAL_STATE__` 解析
- [wadeld2026/soqq-wechat-search](https://github.com/wadeld2026/soqq-wechat-search) — 公众号分类
- [xbbkok/dsh-yuanbao-search](https://github.com/xbbkok/dsh-yuanbao-search) — 元宝搜索入口说明

与上游的差异：用纯 RSC 解析替代 playwright（服务器无需装浏览器）；节流/重试交给 SearXNG 网络层处理，不在引擎内重复实现。

## 注意事项

- so.qq.com 是公开页面，前端改版会导致解析失效，需更新 `CARD_BY_TAB`、字段正则或 `STATE_PAT`。`tests/fixtures/` 里保留了真实页面快照，可用于回归测试。
- 请低频使用，不要高频抓取。
- 返回内容版权归原网站与作者所有；商用前请自行评估 so.qq.com 服务条款合规风险。
- 本引擎需要请求携带浏览器 UA 与 Referer，已内置。

## 许可证

MIT — 详见 [LICENSE](LICENSE)。

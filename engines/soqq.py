# SPDX-License-Identifier: AGPL-3.0-or-later
"""SearXNG custom engine(s): 腾讯元宝搜索 so.qq.com — multi-tab via SSR /isearch.

Integrates all 4 GitHub projects' approaches, verified 2026-11 with lightpanda:
  - 27Aaron/yuanban_so_mcp        : request headers / tabs / source overview
  - JoxAnde/soqq-search-api       : RSC (self.__next_f.push) parsing pattern
  - wadeld2026/soqq-wechat-search : weixin_article (公众号) tab
  - xbbkok/dsh-yuanbao-search     : /iaimode AI-answer mode (documented; not scraped)

so.qq.com search_nav tabs (from live DOM):
  all | xueshu(学术科普) | weixin_article(公众号) | weixin_video(视频)
  pic(图片, /ipics) | gov(组织机构) | media(主流媒体)

Register ONE engine and choose tab via settings.yml option `soqq_tab`.
Pure Python stdlib. Returns legacy list[dict] (compatible old + new SearXNG).
"""

import html
import re
import urllib.parse

about = {
    "website": "https://so.qq.com",
    "wikidata_id": None,
    "official_api_documentation": "https://so.qq.com",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["general"]
paging = True

BASE_URL = "https://so.qq.com/isearch"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Override in settings.yml: soqq_tab: weixin_article  (all|xueshu|weixin_article|weixin_video|gov|media)
soqq_tab = "all"

# card name per tab (verified from live RSC data 2026-11)
CARD_BY_TAB = {
    "all": "card-pc/card_normal_result",
    "gov": "card-pc/card_normal_result",
    "media": "card-pc/card_normal_result",
    "weixin_article": "card-common/card30010612",
    "weixin_video": "card-common/card_tab_weixin_video",
    "xueshu": "card-common/card30010614",
}

RSC_PAT = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.S)


def _unescape_rsc(s):
    for a, b in [('\\"', '"'), ('\\/', '/'), ('\\u0026', '&'),
                 ('\\u003c', '<'), ('\\u003e', '>'), ('\\n', ' '), ('\\t', ' ')]:
        s = s.replace(a, b)
    return s


def _clean(text):
    text = html.unescape(text)
    text = re.sub(r'[\ue000-\uf8ff]', '', text)   # highlight private-use markers (e.g. )
    text = re.sub(r'<[^>]+>', '', text)            # strip <em>/<strong> highlight tags
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _field(block, key):
    m = re.search(r'"' + re.escape(key) + r'":"([^"]*)"', block)
    return _clean(m.group(1)) if m else ""


def _blocks(s, card_name):
    starts = [m.start() for m in re.finditer(re.escape(card_name), s)]
    out = []
    for i, st in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(s)
        out.append(s[st:e])
    return out


def _parse(text, tab):
    s = _unescape_rsc("".join(RSC_PAT.findall(text)))
    card = CARD_BY_TAB.get(tab, CARD_BY_TAB["all"])
    results, seen = [], set()

    if tab == "weixin_article":
        for b in _blocks(s, card):
            url = _field(b, "jumpUrl") or _field(b, "url")
            if not url or url in seen:
                continue
            seen.add(url)
            author = _field(b, "authorName") or _field(b, "showname")
            date = _field(b, "publishTime") or _field(b, "showdate")
            title = _field(b, "title")
            content = _field(b, "content") or _field(b, "summary")
            results.append({
                "title": (f"[{author}] " if author else "") + title,
                "url": url,
                "content": (f"({date}) " if date else "") + content,
            })
    elif tab == "weixin_video":
        for b in _blocks(s, card):
            # no direct link; use exportId-based channel (video page) as best effort
            eid = _field(b, "exportId") or _field(b, "export_id")
            url = "https://channels.weixin.qq.com/" + eid if eid else ""
            if not url or url in seen:
                continue
            seen.add(url)
            author = _field(b, "authorName") or _field(b, "nick_name")
            title = _field(b, "title")
            content = _field(b, "description") or _field(b, "content")
            results.append({
                "title": (f"[{author}] " if author else "") + title,
                "url": url,
                "content": content,
            })
    elif tab == "xueshu":
        for b in _blocks(s, card):
            url = _field(b, "url") or _field(b, "jumpUrl")
            if not url or url in seen:
                continue
            seen.add(url)
            journal = _field(b, "journalName") or _field(b, "journal_name")
            date = _field(b, "publishTime") or _field(b, "publication_date")
            results.append({
                "title": _field(b, "title"),
                "url": url,
                "content": ((f"[{journal}] " if journal else "") + (f"({date}) " if date else "") + _field(b, "content")),
            })
    else:  # all / gov / media
        for b in _blocks(s, card):
            url = _field(b, "url")
            if not url or url in seen:
                continue
            seen.add(url)
            site = _field(b, "sourcename") or _field(b, "host")
            date = _field(b, "date")
            results.append({
                "title": _field(b, "title"),
                "url": url,
                "content": ((f"[{site}] " if site else "") + (f"({date}) " if date else "") + _field(b, "content")),
            })
    return results


def request(query, params):
    tab = params.get("soqq_tab", soqq_tab)
    args = {"query": query, "quick": "1", "page": str(params.get("pageno", 1))}
    if tab and tab != "all":
        args["tab"] = tab
    params["url"] = BASE_URL + "?" + urllib.parse.urlencode(args)
    params.setdefault("headers", {})
    params["headers"]["User-Agent"] = DEFAULT_UA
    params["headers"]["Accept-Language"] = "zh-CN,zh;q=0.9"
    params["headers"]["Referer"] = "https://so.qq.com/"
    return params


def response(resp):
    # Prefer the per-request tab from params (new core sets resp.search_params);
    # fall back to the module-level value injected by settings.yml.
    tab = soqq_tab
    params = getattr(resp, "search_params", None)
    if params and params.get("soqq_tab"):
        tab = params["soqq_tab"]
    return _parse(resp.text, tab)

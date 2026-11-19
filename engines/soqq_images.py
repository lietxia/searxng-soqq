# SPDX-License-Identifier: AGPL-3.0-or-later
"""SearXNG custom engine: 腾讯元宝搜索 so.qq.com — 图片 (/ipics).

Parses window.__INITIAL_STATE__ JSON embedded in the /ipics SSR page.
Approach from 27Aaron/yuanban_so_mcp (pic_search). Pure stdlib.
Returns legacy list[dict] with images.html template (works old + new core).
"""

import html
import json
import re
import urllib.parse

about = {
    "website": "https://so.qq.com",
    "wikidata_id": None,
    "official_api_documentation": "https://so.qq.com",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["images"]
paging = False

BASE_URL = "https://so.qq.com/ipics"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

STATE_PAT = re.compile(r'__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', re.S)


def _clean(text):
    text = html.unescape(text or "")
    return re.sub(r'\s+', ' ', text).strip()


def request(query, params):
    params["url"] = BASE_URL + "?" + urllib.parse.urlencode({"query": query})
    params.setdefault("headers", {})
    params["headers"]["User-Agent"] = DEFAULT_UA
    params["headers"]["Accept-Language"] = "zh-CN,zh;q=0.9"
    params["headers"]["Referer"] = "https://so.qq.com/"
    return params


def response(resp):
    if getattr(resp, "ok", True) is False:
        return []
    text = getattr(resp, "text", "") or ""
    if not text:
        return []
    m = STATE_PAT.search(text)
    if not m:
        return []
    try:
        state = json.loads(m.group(1))
    except (ValueError, TypeError):
        return []
    items = ((state.get("searchList") or {}).get("searchList")) or []
    results, seen = [], set()
    for it in items:
        if not isinstance(it, dict):
            continue
        img = it.get("oriPicUrl") or it.get("thumbUrl") or ""
        if not img or img in seen:
            continue
        seen.add(img)
        thumb = it.get("thumbUrl") or img
        results.append({
            "template": "images.html",
            "title": _clean(it.get("title"))[:120],
            "img_src": img,
            "thumbnail_src": thumb,
            "url": it.get("url") or it.get("link") or "",
            "source": _clean(it.get("ch_site_name")),
            "resolution": (f"{it.get('width')} x {it.get('height')}"
                           if it.get("width") and it.get("height") else ""),
        })
    return results

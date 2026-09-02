# -*- coding: utf-8 -*-
"""批量优化图片以利于百度收录：
1. 将空 alt 填充为"页面关键词+图片描述"，缺 title 时补充
2. 修复损坏的 base64 src（https://vr013.com/data:image/...）
3. 为本地 /images/ 图片补 width/height
保留已有非空 alt 与已有属性，避免破坏。
"""
import os, re, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
LOCAL = "https://vr013.com/images/"

# 本地图片 拼音文件名 -> 中文产品名  → 尺寸
IMG_META = {
    "jingangshixuanxingji-01": ("金刚石选型机", "800x800"),
    "jingangshixuanxingji-02": ("金刚石选型机", "800x800"),
    "jingangshixuanxingji-03": ("金刚石选型机", "800x800"),
    "taociqiushaixuanji-01":   ("陶瓷球筛选机", "800x450"),
    "taocizhushaifenji-01":    ("陶瓷筛选机",   "800x450"),
    "taocizhushaifenji-02":    ("陶瓷筛选机",   "800x450"),
    "taocizhuxuanxingji-fahuo":("陶瓷选型机",   "800x800"),
    "yanghuagaozhufenxuanji-01":("氧化铝分选机","800x450"),
    "yanghuagaozhufenxuanji-02":("氧化铝分选机","800x450"),
    "yanghuagaozhushaifenji-01":("氧化铝筛选机","800x450"),
    "yanghuagaozhuxuanxingji-01":("氧化铝选型机","800x800"),
}

SUFFIXES = ["设备实拍图", "设备现场图", "设备工作现场", "厂家实拍设备"]  # 轮换增加变化

def page_keyword(title):
    """从 <title> 提取主题词（去掉品牌/站名分隔后缀）"""
    t = title.strip()
    t = re.split(r"[_|_]|-", t)[0]  # 取第一个分隔段
    t = t.replace("金刚石选型机", "金刚石选型机") if False else t
    return t.strip()

def chinese_name_for(src):
    """本地图 src -> (中文名, WxH)；非本地图返回 (None, None)"""
    if LOCAL not in src:
        return None, None
    base = os.path.basename(src.split("?")[0])
    stem = re.sub(r"\.(jpg|jpeg|png|webp|gif)$", "", base)
    return IMG_META.get(stem, (stem, None))

def _chop_closer(tag):
    """去掉 img 结尾的 > 或 />，返回 (主体, 结尾)"""
    if tag.endswith("/>"):
        return tag[:-2].rstrip(), " />"
    return tag[:-1].rstrip(), ">"

def rewrite_img(m, kw, ctr):
    tag = m.group(0)
    src_m = re.search(r'\ssrc="([^"]*)"', tag)
    src = src_m.group(1) if src_m else ""
    cn, dims = chinese_name_for(src)

    # 1) 修复损坏的 base64 / data 前缀
    if "base64" in src or "data:image" in src or src.startswith("data:"):
        src = LOCAL + "jingangshixuanxingji-01.jpg"
        tag = re.sub(r'\ssrc="[^"]*"', f' src="{src}"', tag, count=1)

    # 2) 填充/补全 alt 与 title
    suffix = SUFFIXES[ctr % len(SUFFIXES)]
    alt_text = f"{kw}{suffix}"
    def _altr(m):
        inner = m.group(1).strip()
        if inner == "":
            return f' alt="{alt_text}"'
        return m.group(0)
    if re.search(r'\salt="([^"]*)"', tag):
        tag = re.sub(r'\salt="([^"]*)"', _altr, tag, count=1)

    # 3) 收集需追加的属性（一次插入，兼容自闭合标签）
    append = []
    if not re.search(r'\salt="', tag):
        append.append(f'alt="{alt_text}"')
    if not re.search(r'\stitle="', tag):
        append.append(f'title="{kw}"')
    if dims:
        w, h = dims.split("x")
        if not re.search(r'\swidth="', tag):
            append.append(f'width="{w}"')
        if not re.search(r'\sheight="', tag):
            append.append(f'height="{h}"')
    if append:
        body, closer = _chop_closer(tag)
        tag = body + " " + " ".join(append) + closer
    return tag

def process_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    tm = re.search(r"<title>([^<]*)</title>", html, re.I)
    kw = page_keyword(tm.group(1)) if tm else "设备"
    if not kw:
        kw = "设备"
    ctr = [0]
    def _cb(m):
        ctr[0] += 1
        return rewrite_img(m, kw, ctr[0])
    new = re.sub(r"<(img|mip-img)\b[^>]*>", _cb, html)
    if new != html:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return f"{os.path.relpath(path, ROOT)}: 已处理 {ctr[0]} 个 img"
    return None

def main():
    files = sorted(
        glob.glob(os.path.join(ROOT, "article", "**", "*.html"), recursive=True)
        + glob.glob(os.path.join(ROOT, "page", "**", "*.html"), recursive=True)
        + [os.path.join(ROOT, "index.html")]
    )
    changed = 0
    for p in files:
        r = process_file(p)
        if r:
            print(r)
            changed += 1
    print(f"\n共修改 {changed} 个文件")

if __name__ == "__main__":
    main()
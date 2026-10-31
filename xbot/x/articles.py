"""HTML article body -> X Articles Draft.js ``content_state``.

The panel stores article bodies as contenteditable HTML. X's article editor
submits a Draft.js-like document in a snake_case wire format::

    {"blocks": [{"data": {}, "text": "...", "key": "a1b2c",
                 "type": "unstyled", "entity_ranges": [],
                 "inline_style_ranges": []}],
     "entity_map": [{"key": "0", "value": {"data": {"url": "..."},
                                            "type": "LINK",
                                            "mutability": "Mutable"}}]}

This module converts the common block/inline tags produced by the editor.
"""
import random
import re
import string

from bs4 import BeautifulSoup, NavigableString, Tag

_BLOCK_TYPES = {
    "h1": "header-one",
    "h2": "header-two",
    "h3": "header-two",
    "h4": "header-two",
    "h5": "header-two",
    "h6": "header-two",
    "blockquote": "blockquote",
    "pre": "unstyled",
    "p": "unstyled",
    "div": "unstyled",
    "section": "unstyled",
    "article": "unstyled",
}
_BLOCK_TAGS = set(_BLOCK_TYPES) | {"ul", "ol", "li"}
_STYLE_TAGS = {
    "b": "Bold", "strong": "Bold",
    "i": "Italic", "em": "Italic",
    "s": "Strikethrough", "strike": "Strikethrough", "del": "Strikethrough",
}
_SKIP_TAGS = {"script", "style", "img", "video", "audio", "iframe", "svg", "noscript"}

# Block-level span data. X renders @mentions / #hashtags / $cashtags as links
# only when the block carries these ranges; plain text is not enough.
_MENTION_RE = re.compile(r"(?<![\w/])@([A-Za-z0-9_]{1,15})")
_HASHTAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_]{1,50})")
_CASHTAG_RE = re.compile(r"(?<![\w/])\$([A-Za-z]{1,6})\b")


def _new_key() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=5))


def _clean(text: str) -> str:
    return text.replace("\xa0", " ")


def _merge_styles(ranges: list) -> list:
    merged = []
    for item in sorted(ranges, key=lambda r: (r["style"], r["offset"])):
        last = merged[-1] if merged else None
        if last and last["style"] == item["style"] \
                and last["offset"] + last["length"] >= item["offset"]:
            end = max(last["offset"] + last["length"],
                      item["offset"] + item["length"])
            last["length"] = end - last["offset"]
        else:
            merged.append(dict(item))
    return sorted(merged, key=lambda r: (r["offset"], r["style"]))


class _InlineBuilder:
    def __init__(self):
        self.parts = []
        self.styles = []
        self.links = []  # (offset, length, url)

    def add(self, text: str, styles=frozenset(), link: str = None):
        if not text:
            return
        offset = len("".join(self.parts))
        length = len(text)
        self.parts.append(text)
        for style in styles:
            self.styles.append({"offset": offset, "length": length, "style": style})
        if link:
            self.links.append((offset, length, link))

    @property
    def text(self) -> str:
        return "".join(self.parts)


def _walk_inline(item, builder: _InlineBuilder, styles=frozenset(), link=None):
    if isinstance(item, NavigableString):
        builder.add(_clean(str(item)), styles, link)
        return
    if not isinstance(item, Tag):
        return
    name = item.name.lower()
    if name in _SKIP_TAGS:
        return
    if name == "br":
        builder.add("\n", styles)
        return
    if name == "a":
        href = (item.get("href") or "").strip()
        _walk_children(item, builder, styles, href or link)
        return
    next_styles = styles
    style = _STYLE_TAGS.get(name)
    if style:
        next_styles = styles | {style}
    _walk_children(item, builder, next_styles, link)


def _walk_children(tag, builder: _InlineBuilder, styles, link):
    for child in tag.children:
        _walk_inline(child, builder, styles, link)


def _make_block(item, block_type: str, entity_map: list) -> dict:
    builder = _InlineBuilder()
    _walk_inline(item, builder)
    return _make_block_from_builder(builder, block_type, entity_map)


def _plain_block(text: str, block_type: str = "unstyled") -> dict:
    return {"data": _block_data(text, []), "text": text, "key": _new_key(),
            "type": block_type, "entity_ranges": [], "inline_style_ranges": []}


def _is_block_tag(tag) -> bool:
    return isinstance(tag, Tag) and tag.name.lower() in _BLOCK_TAGS


def _has_block_children(tag) -> bool:
    return any(_is_block_tag(child) for child in tag.children)


def _walk_blocks(node, blocks: list, entity_map: list):
    pending = []

    def flush_pending():
        if not pending:
            return
        builder = _InlineBuilder()
        for item in pending:
            _walk_inline(item, builder)
        pending.clear()
        if builder.text.strip():
            block = _make_block_from_builder(builder, "unstyled", entity_map)
            blocks.append(block)

    for child in node.children:
        if isinstance(child, Tag) and child.name.lower() in _BLOCK_TAGS:
            flush_pending()
            name = child.name.lower()
            if name in ("ul", "ol"):
                block_type = ("unordered-list-item" if name == "ul"
                              else "ordered-list-item")
                for li in child.find_all("li", recursive=False):
                    block = _make_block(li, block_type, entity_map)
                    if block["text"].strip():
                        blocks.append(block)
            elif name == "li":
                block = _make_block(child, "unstyled", entity_map)
                if block["text"].strip():
                    blocks.append(block)
            elif _has_block_children(child) and name in ("div", "section", "article"):
                _walk_blocks(child, blocks, entity_map)
            else:
                block = _make_block(child, _BLOCK_TYPES.get(name, "unstyled"),
                                    entity_map)
                if block["text"].strip() or not blocks:
                    blocks.append(block)
        else:
            pending.append(child)
    flush_pending()


def _block_data(text: str, links: list) -> dict:
    """Build the block-level data spans (mentions/hashtags/cashtags).

    ``from_index`` is inclusive, ``to_index`` exclusive, both in code points.
    Spans that overlap a LINK entity are skipped (e.g. an @handle in a URL).
    """
    data = {}
    for key, regex in (("mentions", _MENTION_RE),
                       ("hashtags", _HASHTAG_RE),
                       ("cashtags", _CASHTAG_RE)):
        spans = []
        for match in regex.finditer(text):
            start, end = match.start(), match.end()
            if any(start < offset + length and offset < end
                   for offset, length, _ in links):
                continue
            spans.append({"from_index": start, "to_index": end,
                          "text": match.group(0)})
        if spans:
            data[key] = spans
    return data


def _make_block_from_builder(builder: _InlineBuilder, block_type: str,
                             entity_map: list) -> dict:
    ranges = []
    for offset, length, url in builder.links:
        key = len(entity_map)
        entity_map.append({"key": str(key), "value": {
            "data": {"url": url}, "type": "LINK", "mutability": "Mutable"}})
        ranges.append({"key": key, "offset": offset, "length": length})
    return {
        "data": _block_data(builder.text, builder.links),
        "text": builder.text,
        "key": _new_key(),
        "type": block_type,
        "entity_ranges": ranges,
        "inline_style_ranges": _merge_styles(builder.styles),
    }


def _plain_text(value: str) -> str:
    return _clean(BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True))


def content_state_from_html(body_html: str, subtitle: str = "") -> dict:
    """Build the ``content_state`` sent to ArticleEntityUpdateContent."""
    entity_map = []
    blocks = []

    sub = _plain_text(subtitle)
    if sub:
        blocks.append(_plain_block(sub, "header-two"))

    soup = BeautifulSoup(body_html or "", "html.parser")
    root = soup.body or soup
    has_blocks = any(_is_block_tag(child) for child in root.children)
    if has_blocks:
        _walk_blocks(root, blocks, entity_map)
    else:
        plain = _clean(root.get_text("\n", strip=True))
        if "\n" in plain:
            for para in re.split(r"\n+", plain):
                if para.strip():
                    blocks.append(_plain_block(para.strip()))
        elif plain or not blocks:
            blocks.append(_make_block(root, "unstyled", entity_map))

    if not blocks:
        blocks.append(_plain_block(""))
    return {"blocks": blocks, "entity_map": entity_map}

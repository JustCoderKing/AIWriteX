# -*- coding: utf-8 -*-
"""把带样式表的公众号预览 HTML 适配成文章，并抽取可复用模板。"""

import re
from bs4 import BeautifulSoup, NavigableString

CONTENT_PLACEHOLDER = "{{内容}}"
_CHROME_SELECTORS = (".toolbar", ".foot", ".acct")


def adapt_preview_html(html: str) -> dict:
    """去掉预览外壳，把类样式转成内联样式，并给出可填充模板。"""
    soup = BeautifulSoup(html or "", "html.parser")
    variables, rules = _collect_css(soup)
    _apply_rules(soup, rules, variables)
    for selector in _CHROME_SELECTORS:
        for node in soup.select(selector):
            node.decompose()
    for tag in soup.find_all(["style", "script", "link", "meta"]):
        tag.decompose()

    root = soup.select_one(".phone") or soup.body or soup
    title = ""
    heading = root.find(["h1", "h2"])
    if heading:
        title = heading.get_text(" ", strip=True)

    _divs_to_sections(root)
    _drop_presentation_attrs(root)
    body_style = _body_style(soup, variables)
    article_inner = root.decode_contents() if root.name in ("body", "div", "section") else str(root)
    article_html = _wrap_document(title or "导入文章", article_inner, body_style)
    template_html = _wrap_document(
        "导入模板",
        _placeholder_copy(article_inner),
        body_style,
    )
    return {
        "title": title or "导入文章",
        "article_html": article_html,
        "template_html": template_html,
    }


def _collect_css(soup: BeautifulSoup):
    variables = {}
    rules = []
    for style in soup.find_all("style"):
        _scan_css(style.get_text() or "", variables, rules)
    return variables, rules


def _scan_css(css: str, variables: dict, rules: list):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    index = 0
    length = len(css)
    while index < length:
        while index < length and css[index].isspace():
            index += 1
        if index >= length:
            break
        if css[index] == "@":
            index = _skip_block(css, index)
            continue
        brace = css.find("{", index)
        if brace < 0:
            break
        selector = css[index:brace].strip()
        end = _block_end(css, brace)
        body = css[brace + 1 : end - 1]
        if selector.startswith(":root"):
            variables.update(_declarations(body))
        else:
            for part in selector.split(","):
                part = part.strip()
                if part and not any(char in part for char in ":|>+~*["):
                    rules.append((part, _declarations(body)))
        index = end


def _skip_block(css: str, index: int) -> int:
    brace = css.find("{", index)
    if brace < 0:
        return len(css)
    return _block_end(css, brace)


def _block_end(css: str, brace: int) -> int:
    depth = 0
    for pos in range(brace, len(css)):
        if css[pos] == "{":
            depth += 1
        elif css[pos] == "}":
            depth -= 1
            if depth == 0:
                return pos + 1
    return len(css)


def _declarations(body: str) -> dict:
    result = {}
    for chunk in body.split(";"):
        if ":" not in chunk:
            continue
        name, value = chunk.split(":", 1)
        name = name.strip()
        value = value.strip()
        if name and value:
            result[name] = value
    return result


def _apply_rules(soup, rules, variables):
    for element in soup.find_all(True):
        merged = {}
        for selector, declarations in rules:
            if _matches(element, selector):
                merged.update(declarations)
        if not merged and not element.get("style"):
            continue
        inline = _declarations(element.get("style") or "")
        merged.update(inline)
        resolved = {name: _resolve_vars(value, variables) for name, value in merged.items()}
        if resolved:
            element["style"] = "; ".join(f"{name}: {value}" for name, value in resolved.items())


def _matches(element, selector: str) -> bool:
    parts = [part for part in selector.split() if part]
    if not parts or not _match_simple(element, parts[-1]):
        return False
    node = element
    for part in reversed(parts[:-1]):
        node = node.parent if node else None
        found = False
        while node is not None and getattr(node, "name", None):
            if _match_simple(node, part):
                found = True
                break
            node = node.parent
        if not found:
            return False
    return True


def _match_simple(element, selector: str) -> bool:
    classes = set(element.get("class") or [])
    if selector.startswith("."):
        needed = [item for item in selector[1:].split(".") if item]
        return bool(needed) and all(item in classes for item in needed)
    if "." in selector:
        tag, rest = selector.split(".", 1)
        if element.name != tag:
            return False
        needed = [item for item in rest.split(".") if item]
        return all(item in classes for item in needed)
    return element.name == selector


def _resolve_vars(value: str, variables: dict) -> str:
    def replace(match):
        return variables.get(match.group(1).strip(), match.group(0))

    resolved = value
    for _ in range(4):
        updated = re.sub(r"var\(\s*(--[\w-]+)\s*\)", replace, resolved)
        if updated == resolved:
            break
        resolved = updated
    return resolved


def _divs_to_sections(root):
    for element in list(root.find_all("div")):
        element.name = "section"


def _drop_presentation_attrs(root):
    for element in root.find_all(True):
        for attr in ("class", "id"):
            if attr in element.attrs:
                del element.attrs[attr]


def _body_style(soup, variables: dict) -> str:
    body = soup.body
    if body and body.get("style"):
        return body["style"]
    return "margin: 0; padding: 16px; color: #1f2328; font-size: 16px; line-height: 1.9;"


def _wrap_document(title: str, inner: str, body_style: str) -> str:
    safe_title = (title or "导入文章").replace("<", "")
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<title>{safe_title}</title></head>"
        f"<body><section style=\"{body_style}\">{inner}</section></body></html>"
    )


def _placeholder_copy(inner_html: str) -> str:
    soup = BeautifulSoup(f"<section>{inner_html}</section>", "html.parser")
    for text in list(soup.find_all(string=True)):
        if not isinstance(text, NavigableString):
            continue
        stripped = str(text).strip()
        if len(stripped) < 2:
            continue
        text.replace_with(str(text).replace(stripped, CONTENT_PLACEHOLDER))
    return soup.decode_contents()

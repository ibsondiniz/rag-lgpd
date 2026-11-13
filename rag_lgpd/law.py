"""Download the consolidated LGPD text (Lei 13.709/2018) from the official Planalto site and split it.

Struck-through passages are text that later laws replaced, so they are dropped.
Each article keeps its full text; each search chunk is one paragraph of an article,
prefixed by the start of the article's first sentence so a lone item ("I - mediante consentimento")
still says what it is about.
"""

import html
import json
import re
import urllib.request
from pathlib import Path

URL = "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"
DATA = Path(__file__).resolve().parent.parent / "data" / "lgpd.json"
NOTE = re.compile(r"\((Reda[çc][ãa]o dada|Inclu[íi]d[oa]|Vide|Vig[êe]ncia|Revogad|Promulga)[^)]*\)", re.IGNORECASE)
ART = re.compile(r"^Art\. ?(\d+(?:-[A-Z])?)[º°o]?\.?\s")


def paragraphs(page):
    """Visible paragraphs of the page, without struck text, tags or amendment notes."""
    page = re.sub(r"<(strike|s|del)\b[\s\S]*?</\1>", " ", page, flags=re.IGNORECASE)
    for p in re.findall(r"<p\b[\s\S]*?</p>", page, flags=re.IGNORECASE):
        text = html.unescape(re.sub(r"<[^>]+>", " ", p))
        text = re.sub(r"\s+", " ", NOTE.sub(" ", text)).strip()
        if text:
            yield text


def parse(page):
    """[{art, text}] in order. Stops at the signature ("Brasília, ...")."""
    arts = []
    for p in paragraphs(page):
        if p.startswith("Brasília,"):
            break
        if len(p) < 40 and re.search(r"\(VETADO\)\.?$", p):  # vetoed article or item: no content
            continue
        m = ART.match(p)
        if m and not any(a["art"] == m.group(1) for a in arts):
            arts.append({"art": m.group(1), "paras": [p]})
        elif arts and not re.match(r"^(CAPÍTULO|Seção|TÍTULO)\b", p, re.IGNORECASE) and not p.isupper():
            arts[-1]["paras"].append(p)
    return [{"art": a["art"], "text": "\n".join(a["paras"])} for a in arts]


def chunks(articles, head=160):
    """One chunk per paragraph: [{art, text}]."""
    out = []
    for a in articles:
        paras = a["text"].split("\n")
        caput = paras[0][:head]
        out.append({"art": a["art"], "text": paras[0]})
        out += [{"art": a["art"], "text": f"{caput} … {p}"} for p in paras[1:]]
    return out


def download():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (rag-lgpd)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("windows-1252", errors="replace")


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(articles, path=DATA):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(articles, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

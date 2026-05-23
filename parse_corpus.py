"""
Section-aware parser for Finlex + Vero HTML corpus.
Outputs: data/parsed_nodes.jsonl  (one JSON object per node)
"""
import json, re, os
from pathlib import Path
from bs4 import BeautifulSoup

def _long(p: Path) -> str:
    """Return absolute path string. On Windows uses str() which handles most cases."""
    return str(p.resolve())

def _iter_html(root: Path):
    """Recursively yield .html files using os.scandir to handle long paths."""
    try:
        with os.scandir(_long(root)) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        yield from _iter_html(Path(entry.path))
                    elif entry.name.endswith(".html"):
                        yield Path(entry.path)
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass

DATA_ROOT = Path(__file__).parent / "data/raw/finland_kb"
OUT_FILE  = Path(__file__).parent / "data/parsed_nodes.jsonl"

# ── helpers ──────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def extract_statute_refs(text: str) -> list[str]:
    """Pull explicit Finnish statute references like 'TVL 85 §', 'AVL 117 §', 'EPL 25 §'."""
    return re.findall(r"\b[A-ZÄÖÅ]{2,6}\s*\d+\s*[a-z]?\s*§", text)

def extract_links(tag) -> list[str]:
    return [a["href"] for a in tag.find_all("a", href=True)]

# ── Finlex statute parser ─────────────────────────────────────────────────────

def read_html(path: Path) -> str:
    long_path = _long(path)
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(long_path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(long_path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")

def parse_finlex_statute(path: Path) -> list[dict]:
    soup = BeautifulSoup(read_html(path), "html.parser")
    title = clean(soup.find("h1").get_text()) if soup.find("h1") else path.stem
    nodes = []
    current_section = None
    # Use relative path for unique ID prefix (avoids collisions from same stem in different dirs)
    rel_path = str(path.relative_to(DATA_ROOT)).replace("\\", "/")
    id_prefix = rel_path.replace("/", "_").replace(".html", "")

    for tag in soup.body.children:
        if not hasattr(tag, "name") or tag.name is None:
            continue
        text = clean(tag.get_text())
        if not text:
            continue

        if tag.name == "h1":
            title = text
        elif tag.name in ("h2", "h3"):
            current_section = text
        elif tag.name == "h4":
            current_section = text
        elif tag.name == "p":
            refs = extract_statute_refs(text)
            links = extract_links(tag)
            nodes.append({
                "id": f"finlex::{id_prefix}::{len(nodes)}",
                "source": "finlex",
                "doc_type": "statute",
                "doc_title": title,
                "section": current_section,
                "text": text,
                "statute_refs": refs,
                "links": links,
                "file": rel_path,
            })
    return nodes

# ── Finlex KHO case law parser ────────────────────────────────────────────────

def parse_kho(path: Path) -> list[dict]:
    soup = BeautifulSoup(read_html(path), "html.parser")
    title = clean(soup.find("h1").get_text()) if soup.find("h1") else path.stem
    paragraphs = [clean(p.get_text()) for p in soup.find_all("p") if clean(p.get_text())]
    refs = []
    for p in paragraphs:
        refs.extend(extract_statute_refs(p))

    # date from last paragraph that looks like a date
    date = None
    for p in reversed(paragraphs):
        m = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", p)
        if m:
            date = m.group()
            break

    # Use relative path for unique ID prefix
    rel_path = str(path.relative_to(DATA_ROOT)).replace("\\", "/")
    id_prefix = rel_path.replace("/", "_").replace(".html", "")

    nodes = []
    for i, p in enumerate(paragraphs):
        nodes.append({
            "id": f"finlex::{id_prefix}::{i}",
            "source": "finlex",
            "doc_type": "case_law",
            "doc_title": title,
            "section": None,
            "text": p,
            "statute_refs": extract_statute_refs(p),
            "links": [],
            "date": date,
            "file": rel_path,
        })
    return nodes

# ── Vero guidance parser ──────────────────────────────────────────────────────

def parse_vero(path: Path) -> list[dict]:
    soup = BeautifulSoup(read_html(path), "html.parser")

    # title
    title_tag = soup.find(class_="taxxa-title") or soup.find("h1")
    title = clean(title_tag.get_text()) if title_tag else path.stem

    # TOC for section hierarchy
    toc_tag = soup.find("taxfi-table-of-contents-mobile")
    toc_map = {}
    if toc_tag and toc_tag.get(":toc-data"):
        try:
            toc_data = json.loads(toc_tag[":toc-data"])
            for item in toc_data.get("IndexItems", []):
                anchor = item["LinkUrl"].lstrip("#")
                toc_map[anchor] = item["Title"]
        except Exception:
            pass

    nodes = []
    current_section = None
    is_example = False
    # Use relative path for unique ID prefix
    rel_path = str(path.relative_to(DATA_ROOT)).replace("\\", "/")
    id_prefix = rel_path.replace("/", "_").replace(".html", "")

    article = soup.find("article") or soup.find("div", class_="main-body") or soup.body
    if not article:
        return nodes

    for tag in article.descendants:
        if not hasattr(tag, "name") or tag.name is None:
            continue
        if tag.name in ("h1", "h2", "h3", "h4"):
            text = clean(tag.get_text())
            if text:
                hid = tag.get("id", "")
                current_section = toc_map.get(hid, text)
                is_example = False
        elif tag.name == "section" and "example" in tag.get("class", []):
            is_example = True
        elif tag.name == "p" and tag.parent.name not in ("h1","h2","h3","h4"):
            text = clean(tag.get_text())
            if not text or len(text) < 10:
                continue
            refs = extract_statute_refs(text)
            links = extract_links(tag)
            nodes.append({
                "id": f"vero::{id_prefix}::{len(nodes)}",
                "source": "vero",
                "doc_type": "guidance_example" if is_example else "guidance",
                "doc_title": title,
                "section": current_section,
                "text": text,
                "statute_refs": refs,
                "links": links,
                "file": rel_path,
            })
            if is_example and tag == tag.parent.find_all("p")[-1]:
                is_example = False

    return nodes

# ── walk corpus ───────────────────────────────────────────────────────────────

def walk_finlex(root: Path) -> list[dict]:
    nodes = []
    try:
        with os.scandir(_long(root)) as it:
            subdirs = [(entry.name, Path(entry.path)) for entry in it if entry.is_dir()]
    except OSError:
        return nodes
    for name, subdir in subdirs:
        for html in _iter_html(subdir):
            try:
                if "Korkein" in name:
                    nodes.extend(parse_kho(html))
                else:
                    nodes.extend(parse_finlex_statute(html))
            except Exception:
                pass
    return nodes

def walk_vero(root: Path) -> list[dict]:
    nodes = []
    for html in _iter_html(root):
        try:
            nodes.extend(parse_vero(html))
        except Exception:
            pass
    return nodes

# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    OUT_FILE.parent.mkdir(exist_ok=True)
    all_nodes = []

    print("Parsing Finlex...")
    finlex_nodes = walk_finlex(DATA_ROOT / "finlex")
    print(f"  {len(finlex_nodes)} nodes")
    all_nodes.extend(finlex_nodes)

    print("Parsing Vero...")
    vero_nodes = walk_vero(DATA_ROOT / "vero")
    print(f"  {len(vero_nodes)} nodes")
    all_nodes.extend(vero_nodes)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        for node in all_nodes:
            f.write(json.dumps(node, ensure_ascii=False) + "\n")

    print(f"Total nodes: {len(all_nodes)} -> {OUT_FILE}")

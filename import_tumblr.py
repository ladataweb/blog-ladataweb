import re
from pathlib import Path
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import yaml
from slugify import slugify

EXPORT_DIR = Path("tumblr-export")
OUTPUT_DIR = Path("_posts")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_title(soup):
    for h1 in soup.find_all("h1"):
        text = h1.get_text(" ", strip=True)
        if text:
            return text
    return "Sin título"

def extract_timestamp(soup):
    ts = soup.select_one("#timestamp")
    if not ts:
        return None
    return dateparser.parse(ts.get_text(" ", strip=True))

def extract_tags(soup):
    return [tag.get_text(" ", strip=True).lower().replace(" ", "-") for tag in soup.select(".tag")]

def clean_body(soup):
    body = soup.body
    if not body:
        return ""

    footer = body.select_one("#footer")
    if footer:
        footer.extract()

    h1s = body.find_all("h1")
    removed_title = False
    for h in h1s:
        txt = h.get_text(" ", strip=True)
        if not txt:
            h.extract()
        elif not removed_title:
            h.extract()
            removed_title = True
            break

    html = "".join(str(node) for node in body.contents).strip()
    html = html.replace("[[MORE]]", "<!--more-->")
    return html
    
def escape_liquid_syntax(html):
    html = html.replace("{{", "&#123;&#123;")
    html = html.replace("}}", "&#125;&#125;")
    html = html.replace("{%", "&#123;%")
    html = html.replace("%}", "%&#125;")
    return html
    
def normalize_smart_quotes(html):
    return (
        html.replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
    )

def process_file(path):
    post_id = path.stem
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    title = extract_title(soup)
    dt = extract_timestamp(soup)
    tags = extract_tags(soup)
    body = clean_body(soup)
    body = normalize_smart_quotes(body)
    body = escape_liquid_syntax(body)

    if not dt:
        raise ValueError(f"No se encontró fecha en {path.name}")

    slug_base = re.sub(r"^\[[^\]]+\]\s*", "", title).strip()
    slug = slugify(slug_base)

    front_matter = {
        "layout": "post",
        "title": title,
        "date": dt.strftime("%Y-%m-%d %H:%M:%S -0300"),
        "slug": slug,
        "tags": tags,
        "legacy": True,
        "tumblr_id": post_id
    }

    filename = f"{dt.strftime('%Y-%m-%d')}-{slug}.html"
    output_path = OUTPUT_DIR / filename

    content = "---\n"
    content += yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True)
    content += "---\n"
    content += body + "\n"

    output_path.write_text(content, encoding="utf-8")
    print(f"Creado: {output_path}")

def main():
    for file in EXPORT_DIR.glob("*.html"):
        process_file(file)

if __name__ == "__main__":
    main()
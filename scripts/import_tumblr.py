import re
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from slugify import slugify
from dateutil import parser as dateparser
import yaml

EXPORT_DIR = Path("tumblr-export")
POSTS_DIR = Path("_posts")
MEDIA_DIR = Path("assets/uploads/tumblr")

POSTS_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

def extract_title(soup):
    h1s = soup.find_all("h1")
    for h in h1s:
      text = h.get_text(" ", strip=True)
      if text:
        return text
    return "Untitled"

def extract_timestamp(soup):
    ts = soup.select_one("#timestamp")
    if not ts:
        return None
    return dateparser.parse(ts.get_text(" ", strip=True))

def extract_tags(soup):
    return [tag.get_text(" ", strip=True).lower().replace(" ", "-") for tag in soup.select(".tag")]

def infer_category(title):
    m = re.match(r"^\[([^\]]+)\]", title)
    if m:
        return slugify(m.group(1))
    return None

def build_body(soup):
    body = soup.body
    if not body:
        return ""

    footer = body.select_one("#footer")
    if footer:
        footer.extract()

    h1s = body.find_all("h1")
    removed_first_nonempty = False
    for h in h1s:
        txt = h.get_text(" ", strip=True)
        if not txt:
            h.extract()
        elif not removed_first_nonempty:
            h.extract()
            removed_first_nonempty = True
            break

    html = "".join(str(node) for node in body.contents).strip()
    html = html.replace("[[MORE]]", "<!--more-->")
    return html

def rewrite_images(html, post_id, year):
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")
    count = 1
    for img in images:
        src = img.get("src", "")
        ext = Path(src.split("?")[0]).suffix or ".png"
        filename = f"{post_id}-{count:02d}{ext}"
        local_rel = f"/assets/uploads/tumblr/{year}/{filename}"
        year_dir = MEDIA_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder strategy:
        # if you already have local media matches, copy them here and rewrite
        # otherwise keep remote src
        img["data-original-src"] = src
        count += 1

    return str(soup)

def process_file(path: Path):
    post_id = path.stem
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    title = extract_title(soup)
    dt = extract_timestamp(soup)
    if not dt:
        raise ValueError(f"No timestamp found in {path}")

    tags = extract_tags(soup)
    category = infer_category(title)
    slug = slugify(re.sub(r"^\[[^\]]+\]\s*", "", title), lowercase=True)

    body = build_body(soup)
    body = rewrite_images(body, post_id, dt.year)

    front_matter = {
        "layout": "post",
        "title": title,
        "date": dt.strftime("%Y-%m-%d %H:%M:%S -0300"),
        "slug": slug,
        "tags": tags,
        "tumblr_id": post_id,
        "legacy": True,
        "excerpt_separator": "<!--more-->"
    }

    if category:
        front_matter["categories"] = [category]

    filename = f"{dt.strftime('%Y-%m-%d')}-{slug}.html"
    out_path = POSTS_DIR / filename

    content = "---\n"
    content += yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True)
    content += "---\n"
    content += body.strip() + "\n"

    out_path.write_text(content, encoding="utf-8")
    print(f"Created {out_path}")

def main():
    for html_file in EXPORT_DIR.glob("*.html"):
        process_file(html_file)

if __name__ == "__main__":
    main()
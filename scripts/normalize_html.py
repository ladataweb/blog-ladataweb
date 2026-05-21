import requests
from pathlib import Path
from bs4 import BeautifulSoup

POSTS_DIR = Path("_posts")

for post_file in POSTS_DIR.glob("*.html"):
    html = post_file.read_text(encoding="utf-8")
    parts = html.split("---", 2)
    if len(parts) < 3:
        continue

    front, body = parts[1], parts[2]
    soup = BeautifulSoup(body, "html.parser")
    changed = False

    for i, img in enumerate(soup.find_all("img"), start=1):
        src = img.get("src", "")
        if "media.tumblr.com" not in src:
            continue

        post_id = "unknown"
        for line in front.splitlines():
            if line.startswith("tumblr_id:"):
                post_id = line.split(":", 1)[1].strip().strip('"')
                break

        ext = Path(src.split("?")[0]).suffix or ".png"
        year = post_file.name[:4]
        out_dir = Path(f"assets/uploads/tumblr/{year}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{post_id}-{i:02d}{ext}"

        if not out_file.exists():
            r = requests.get(src, timeout=30)
            r.raise_for_status()
            out_file.write_bytes(r.content)

        img["src"] = f"/assets/uploads/tumblr/{year}/{out_file.name}"
        changed = True

    if changed:
        updated = f"---{front}---{str(soup)}"
        post_file.write_text(updated, encoding="utf-8")
        print(f"Updated images in {post_file}")
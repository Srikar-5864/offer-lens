"""Download Archivo (400/500/800) and JetBrains Mono (400) woff2 into web/fonts/ (self-hosted, no runtime CDN)."""

from __future__ import annotations

import re
from pathlib import Path

import httpx

FONTS = {
    "archivo-400": "Archivo:wght@400",
    "archivo-500": "Archivo:wght@500",
    "archivo-800": "Archivo:wght@800",
    "jetbrains-mono-400": "JetBrains+Mono:wght@400",
}
OUT = Path(__file__).resolve().parents[1] / "web" / "fonts"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers=UA, timeout=30, follow_redirects=True) as client:
        for name, family in FONTS.items():
            target = OUT / f"{name}.woff2"
            if target.exists():
                continue
            css = client.get(f"https://fonts.googleapis.com/css2?family={family}&display=swap").text
            # Last @font-face block is the latin subset.
            url = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", css)[-1]
            target.write_bytes(client.get(url).content)
            print(f"{target.name}: {target.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()

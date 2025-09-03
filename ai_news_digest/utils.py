from urllib.parse import urlparse
from typing import Iterable, List

def domains_from_urls(urls: Iterable[str]) -> List[str]:
    out = []
    for u in urls:
        try:
            d = urlparse(u).netloc
            if d and d not in out:
                out.append(d)
        except Exception:
            pass
    return out

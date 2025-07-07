import concurrent.futures
import json
import urllib.parse
from typing import Dict, Tuple, List

import requests
from bs4 import BeautifulSoup

from ..context import get_label          
from .pg_manager import apply_patch_and_relaunch


def get_patch(url: str) -> str:
    """
    Download a PostgreSQL mailing-list message and all its patch attachments.

    If agent.context.get_label() is set, apply **each** patch in
    filename-sorted order to that sandbox, rebuilding and relaunching after
    every patch.

    Returns a JSON string:
        {
          "message": "<plain-text body>",
          "patches": { "<patch filename>": "<patch text>", ... },
          "applied": "<ACTIVE_LABEL|None>",
          "applied_patches": ["patch1.diff", "patch2.diff", ...]
        }
    """
    # 1. Fetch the message HTML
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 2. Extract plain-text body
    body_div = soup.find("div", class_="message-content")
    message_text = body_div.get_text("\n", strip=True) if body_div else ""

    # 3. Locate attachment links
    attachment_tags = soup.find_all(
        "a", href=lambda h: h and h.startswith("/message-id/attachment/")
    )
    base = "https://www.postgresql.org"
    attachments: Dict[str, str] = {
        tag["href"].split("/")[-1]: urllib.parse.urljoin(base, tag["href"])
        for tag in attachment_tags
    }

    # 4. Download attachments concurrently
    def _download(item: Tuple[str, str]) -> Tuple[str, str]:
        name, url_ = item
        r = requests.get(url_, timeout=30)
        r.raise_for_status()
        return name, r.text

    patches: Dict[str, str] = {}
    if attachments:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            for name, text in pool.map(_download, attachments.items()):
                patches[name] = text

    applied_patches: List[str] = []
    applied_label = None

    # 5. Apply all patches (if ACTIVE_LABEL set)
    label = get_label()
    print("active label: ", label, "patches: ", patches)
    if label and patches:
        print("applying patches")
        for name in sorted(patches.keys()):
            apply_patch_and_relaunch(label, patches[name])
            applied_patches.append(name)
        applied_label = label

    # 6. Return JSON-encoded result
    return json.dumps(
        {
            "message": message_text,
            "patches": patches,
            "applied": applied_label,
            "applied_patches": applied_patches,
        },
        indent=2,
    )


tool_spec = {
    "type": "function",
    "name": "get_patch",
    "description": (
        "Download a PostgreSQL mailing-list message (body + patch attachments). "
        "This tool automatically applies the patches to the active DB, so any "
        "future queries you run can test the patch."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL of the message on postgresql.org"
            }
        },
        "required": ["url"],
        "additionalProperties": False
    }
}

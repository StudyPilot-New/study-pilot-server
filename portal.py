"""Public landing page; no credentials or account data."""
from pathlib import Path
from html import escape
from urllib.parse import urlsplit

def home_html(download_url='',local_download=False):
    parsed=urlsplit(download_url)
    valid=parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password
    link='/download' if local_download else download_url if valid else '/guia'
    return (Path(__file__).parent/'landing.html').read_text(encoding='utf-8').replace('{{DOWNLOAD}}',escape(link,quote=True))

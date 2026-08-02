import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scholarly import ProxyGenerator, scholarly


def configure_scholarly() -> None:
    """Keep failed requests bounded and optionally route them through ScraperAPI."""
    scholarly.set_timeout(60)
    scholarly.set_retries(2)

    scraper_api_key = os.getenv("SCRAPER_API_KEY", "").strip()
    if not scraper_api_key:
        print("SCRAPER_API_KEY is not configured; trying Google Scholar directly.")
        return

    proxy = ProxyGenerator()
    if not proxy.ScraperAPI(scraper_api_key):
        raise RuntimeError("Could not initialize ScraperAPI. Check SCRAPER_API_KEY.")
    scholarly.use_proxy(proxy, proxy)
    print("ScraperAPI proxy enabled.")


def fetch_author() -> dict:
    scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID", "").strip()
    if not scholar_id:
        raise RuntimeError("GOOGLE_SCHOLAR_ID is required.")

    author = scholarly.search_author_id(scholar_id)
    scholarly.fill(
        author,
        sections=["basics", "indices", "counts", "publications"],
    )
    author["updated"] = datetime.now(timezone.utc).isoformat()
    author["publications"] = {
        publication["author_pub_id"]: publication
        for publication in author.get("publications", [])
        if publication.get("author_pub_id")
    }
    return author


def write_results(author: dict) -> None:
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    with (results_dir / "gs_data.json").open("w", encoding="utf-8") as outfile:
        json.dump(author, outfile, ensure_ascii=False, indent=2, default=str)

    shield_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(author.get("citedby", 0)),
    }
    with (results_dir / "gs_data_shieldsio.json").open(
        "w", encoding="utf-8"
    ) as outfile:
        json.dump(shield_data, outfile, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    configure_scholarly()
    scholar_author = fetch_author()
    write_results(scholar_author)
    print(
        "Updated citation data for "
        f"{scholar_author.get('name', 'author')}: "
        f"{scholar_author.get('citedby', 0)} total citations."
    )

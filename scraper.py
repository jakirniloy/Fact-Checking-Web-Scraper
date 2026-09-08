import time
import random
from urllib.parse import urljoin

import requests
import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36 "
        "(research data collection; contact: mdjakirhossen13@gmail.com)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 20
REQUEST_DELAY_MIN = 2
REQUEST_DELAY_MAX = 4

MAX_PAGES = 5


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def polite_delay():
    """Random delay between requests."""
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))


def fetch_page(url, retries=3):
    """
    Fetch a webpage with retry handling.
    """
    for attempt in range(1, retries + 1):
        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            response.raise_for_status()

            return response.text

        except requests.RequestException as exc:
            print(
                f"Request failed ({attempt}/{retries}): "
                f"{url}\nReason: {exc}"
            )

            if attempt < retries:
                time.sleep(3 * attempt)

    return None


# ============================================================
# GENERIC HELPERS
# ============================================================

def clean_text(text):
    """Normalize whitespace."""
    if not text:
        return None

    return " ".join(text.split())


def get_first_text(element, selectors):
    """
    Try several CSS selectors and return the first matching text.
    """
    for selector in selectors:
        found = element.select_one(selector)

        if found:
            text = clean_text(found.get_text(" ", strip=True))

            if text:
                return text

    return None


def get_first_link(element, selectors, base_url):
    """
    Try several selectors and return an absolute URL.
    """
    for selector in selectors:
        found = element.select_one(selector)

        if found and found.get("href"):
            return urljoin(base_url, found["href"])

    return None


# ============================================================
# SNOPES
# ============================================================

def scrape_snopes(max_pages=5):

    records = []

    print("\n" + "=" * 70)
    print("SCRAPING SNOPES")
    print("=" * 70)

    for page in range(1, max_pages + 1):

        # Snopes fact-check archive pagination
        if page == 1:
            url = "https://www.snopes.com/fact-check/"
        else:
            url = f"https://www.snopes.com/fact-check/?pagenum={page}"

        print(f"\n[Snopes] Page {page}: {url}")

        html = fetch_page(url)

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Current/fallback article-card selectors
        cards = soup.select(
            "article"
        )

        if not cards:
            cards = soup.select(
                ".article-list-item, "
                ".article-card, "
                ".media-wrapper, "
                "div[class*='article']"
            )

        print(f"  Candidate article elements: {len(cards)}")

        page_records = []

        for card in cards:

            # Snopes article links
            article_url = get_first_link(
                card,
                [
                    "h2 a",
                    "h3 a",
                    "h4 a",
                    "a[href*='/fact-check/']",
                    "a[href*='/articles/']",
                ],
                url,
            )

            if not article_url:
                continue

            # Avoid duplicate/non-article navigation links
            if "snopes.com" not in article_url:
                continue

            title = get_first_text(
                card,
                [
                    "h2",
                    "h3",
                    "h4",
                    ".title",
                    "[class*='title']",
                ],
            )

            if not title:
                continue

            # Attempt to find rating/claim label
            label = get_first_text(
                card,
                [
                    "[class*='rating']",
                    "[class*='verdict']",
                    "[class*='label']",
                    "[class*='claim']",
                ],
            )

            page_records.append(
                {
                    "source": "Snopes",
                    "title": title,
                    "url": article_url,
                    "label": label,
                }
            )

        # Remove duplicates from current page
        unique = {}

        for record in page_records:
            unique[record["url"]] = record

        page_records = list(unique.values())

        print(f"  Articles discovered: {len(page_records)}")

        # Visit individual articles
        for record in page_records:

            polite_delay()

            print(f"    Article: {record['title'][:80]}")

            article_html = fetch_page(record["url"])

            if not article_html:
                record["text"] = None
                continue

            article_soup = BeautifulSoup(
                article_html,
                "html.parser",
            )

            # Remove unwanted page elements
            for tag in article_soup.select(
                "script, style, nav, footer, header, "
                "aside, form, noscript"
            ):
                tag.decompose()

            # Article body fallback selectors
            body = None

            body_selectors = [
                "article",
                "[class*='article-body']",
                "[class*='article-content']",
                "[class*='entry-content']",
                ".single-post-content",
                "main",
            ]

            for selector in body_selectors:

                candidate = article_soup.select_one(selector)

                if candidate:

                    text = clean_text(
                        candidate.get_text(" ", strip=True)
                    )

                    if text and len(text) > 200:
                        body = text
                        break

            record["text"] = body

            # Try extracting the verdict from the article page
            if not record["label"]:

                record["label"] = get_first_text(
                    article_soup,
                    [
                        "[class*='rating']",
                        "[class*='verdict']",
                        "[class*='label']",
                        "[class*='claim-rating']",
                    ],
                )

            records.append(record)

        polite_delay()

    return records


# ============================================================
# FACTCHECK.ORG
# ============================================================

def scrape_factcheck(max_pages=5):

    records = []

    print("\n" + "=" * 70)
    print("SCRAPING FACTCHECK.ORG")
    print("=" * 70)

    # FactCheck has several useful archives.
    # Ask FactCheck is particularly useful for question/answer data.
    archive_urls = [
        "https://www.factcheck.org/ask-factcheck/",
        "https://www.factcheck.org/2026/",
    ]

    for archive_url in archive_urls:

        print(f"\n[FactCheck] Archive: {archive_url}")

        html = fetch_page(archive_url)

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        # WordPress-style article containers
        cards = soup.select(
            "article"
        )

        if not cards:
            cards = soup.select(
                ".post",
                ".entry",
            )

        print(f"  Candidate article elements: {len(cards)}")

        page_records = []

        for card in cards:

            article_url = get_first_link(
                card,
                [
                    "h2 a",
                    "h3 a",
                    "h4 a",
                    ".entry-title a",
                    "a[href*='/2026/']",
                    "a[href*='/2025/']",
                    "a[href*='/2024/']",
                ],
                archive_url,
            )

            if not article_url:
                continue

            if "factcheck.org" not in article_url:
                continue

            title = get_first_text(
                card,
                [
                    "h2",
                    "h3",
                    "h4",
                    ".entry-title",
                    ".title",
                ],
            )

            if not title:
                continue

            summary = get_first_text(
                card,
                [
                    ".entry-summary",
                    ".excerpt",
                    ".entry-content",
                    "p",
                ],
            )

            page_records.append(
                {
                    "source": "FactCheck.org",
                    "title": title,
                    "url": article_url,
                    "label": None,
                    "summary": summary,
                }
            )

        unique = {}

        for record in page_records:
            unique[record["url"]] = record

        page_records = list(unique.values())

        print(f"  Articles discovered: {len(page_records)}")

        # Scrape article pages
        for record in page_records:

            polite_delay()

            print(f"    Article: {record['title'][:80]}")

            article_html = fetch_page(record["url"])

            if not article_html:
                record["text"] = None
                continue

            article_soup = BeautifulSoup(
                article_html,
                "html.parser",
            )

            # Remove irrelevant elements
            for tag in article_soup.select(
                "script, style, nav, footer, "
                "header, aside, form, noscript"
            ):
                tag.decompose()

            body = None

            body_selectors = [
                ".entry-content",
                ".post-content",
                "article",
                "main",
            ]

            for selector in body_selectors:

                candidate = article_soup.select_one(selector)

                if candidate:

                    text = clean_text(
                        candidate.get_text(" ", strip=True)
                    )

                    if text and len(text) > 200:
                        body = text
                        break

            record["text"] = body

            records.append(record)

        # Only use the requested number of archives/pages
        if len(records) >= max_pages * 20:
            break

    return records


# ============================================================
# DATA CLEANING
# ============================================================

def clean_dataset(df):

    print("\n" + "=" * 70)
    print("CLEANING DATASET")
    print("=" * 70)

    if df.empty:
        return df

    # Normalize text
    for column in ["title", "text", "label", "summary"]:

        if column in df.columns:
            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )

    # Remove rows without article text
    if "text" in df.columns:
        df = df[df["text"].str.len() > 100]

    # Remove duplicate URLs
    if "url" in df.columns:
        df = df.drop_duplicates(
            subset=["url"],
            keep="first",
        )

    # Remove duplicate title/text combinations
    duplicate_columns = [
        column
        for column in ["title", "text"]
        if column in df.columns
    ]

    if duplicate_columns:
        df = df.drop_duplicates(
            subset=duplicate_columns,
            keep="first",
        )

    # Reset index
    df = df.reset_index(drop=True)

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("\nStarting fact-checking web scraper...")

    snopes_records = scrape_snopes(
        max_pages=MAX_PAGES
    )

    factcheck_records = scrape_factcheck(
        max_pages=MAX_PAGES
    )

    print("\nCombining datasets...")

    all_records = (
        snopes_records +
        factcheck_records
    )

    if not all_records:

        print(
            "\nNo records were collected."
            "\nCheck website accessibility or selectors."
        )

        return

    df = pd.DataFrame(all_records)

    # Ensure consistent columns
    expected_columns = [
        "source",
        "title",
        "url",
        "label",
        "summary",
        "text",
    ]

    for column in expected_columns:

        if column not in df.columns:
            df[column] = None

    df = df[expected_columns]

    # Clean
    df = clean_dataset(df)

    # Save
    output_file = "factcheck_dataset.csv"

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)

    print(f"Total records: {len(df)}")
    print(f"Output file: {output_file}")

    if not df.empty:

        print("\nRecords by source:")
        print(
            df["source"]
            .value_counts()
            .to_string()
        )

        print("\nFirst 5 records:")
        print(
            df[
                [
                    "source",
                    "title",
                    "url",
                ]
            ]
            .head()
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
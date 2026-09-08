# Fact-Check Article Scraper

A general-purpose Python scraper for building a labeled dataset of
fact-checked articles (article text, veracity label, source URL) for
fake-news / misinformation classification research.

## Before you run this

This script ships with **placeholder CSS selectors**, not working ones.
That's intentional:

1. **Check permissions first.** Read the target site's Terms of Service
   and `robots.txt`. Many fact-checking sites restrict automated scraping,
   even for research. Prefer an official API or a dataset the site
   publishes directly, if one exists.
2. **Inspect the real HTML.** Open the site in your browser, use
   DevTools → Inspect on an article listing page, and find the actual
   CSS selectors for the article container, title, link, label, and body.
3. **Fill in `SITE_CONFIGS`** in `scraper.py` with those real selectors.

## Setup

```bash
pip install requests beautifulsoup4 pandas
```

## Usage

```bash
python scraper.py
```

Output: `factcheck_dataset.csv` with columns `source, title, url, label, text`.

## Design notes

- Requests are spaced out (`REQUEST_DELAY_SECONDS`) to avoid hammering
  the target server.
- A descriptive `User-Agent` is set — replace the contact email with
  your own so site operators can reach you if needed.
- `clean_dataset()` drops rows with missing text/label and de-duplicates
  on article text.
- The listing/detail-page split (`fetch_listing_page` + `fetch_article_body`)
  mirrors how most fact-check sites structure their content: a
  paginated index page linking out to full article pages.

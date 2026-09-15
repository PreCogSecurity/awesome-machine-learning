#!/usr/bin/env python3
"""Scrape the CRAN Machine Learning task view and format the packages in
GitHub markdown style for this awesome-machine-learning repo.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request

from pyquery import PyQuery as pq

CRAN_ML_VIEW_URL = "https://cran.r-project.org/web/views/MachineLearning.html"
CRAN_WEB_BASE = "https://cran.r-project.org/web"
DEFAULT_OUTPUT = "Packages.txt"

# A package entry: (name, url, description).
Package = tuple[str, str, str]


def fetch_page(url: str) -> str:
    """Fetch *url* and return its body decoded as UTF-8 text."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def resolve_cran_url(href: str) -> str:
    """Resolve a relative CRAN link against the CRAN web base.

    Task view links look like ``../../packages/ada/index.html``; the leading
    ``../`` segments are stripped and the result is joined to
    :data:`CRAN_WEB_BASE`.
    """
    while href.startswith("../"):
        href = href[3:]
    return f"{CRAN_WEB_BASE}/{href}"


def parse_packages(html: str) -> list[tuple[str, str]]:
    """Extract (name, url) pairs from the task view HTML.

    Only list items whose link points back into the CRAN web tree (relative
    links containing ``..``) are kept; external links are ignored.
    """
    packages = []
    for item in pq(html)("li").items():
        link = item("a").eq(0)
        name = link.text()
        href = link.attr("href")
        if not name or not href or ".." not in href:
            continue
        packages.append((name, resolve_cran_url(href)))
    return packages


def fetch_description(url: str) -> str | None:
    """Fetch the package page at *url* and return its ``<h2>`` text.

    Returns ``None`` (after printing a warning) when the page cannot be
    fetched, so one failing package does not abort the whole run.
    """
    try:
        page_html = fetch_page(url)
    except OSError as exc:
        print(f"warning: could not fetch {url}: {exc}", file=sys.stderr)
        return None
    return pq(page_html)("h2").html()


def build_packages(html: str) -> list[Package]:
    """Build the full (name, url, description) list from the task view HTML."""
    packages = []
    for name, url in parse_packages(html):
        description = fetch_description(url)
        if description is None:
            continue
        packages.append((name, url, description))
    return packages


def format_packages(packages: list[Package]) -> str:
    """Render the packages as GitHub markdown list items."""
    return "".join(
        f"* [{name}]({url}) - {description}\n" for name, url, description in packages
    )


def write_packages(packages: list[Package], output_path: str) -> None:
    """Write the formatted package list to *output_path* as UTF-8."""
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(format_packages(packages))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape the CRAN Machine Learning task view and format the "
            "packages in GitHub markdown style."
        )
    )
    parser.add_argument(
        "--url",
        default=CRAN_ML_VIEW_URL,
        help="URL of the CRAN Machine Learning task view (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="path of the markdown file to write (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the scraper; returns a process exit code."""
    args = parse_args(argv)
    try:
        html = fetch_page(args.url)
    except OSError as exc:
        print(f"error: could not fetch {args.url}: {exc}", file=sys.stderr)
        return 1
    packages = build_packages(html)
    write_packages(packages, args.output)
    print(f"wrote {len(packages)} packages to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tests for scripts/pull_R_packages.py."""

from scripts.pull_R_packages import (
    CRAN_WEB_BASE,
    build_packages,
    fetch_page,
    format_packages,
    main,
    parse_packages,
)

TASK_VIEW_HTML = """
<html><body><ul>
  <li><a href="../../packages/ada/index.html">ada</a></li>
  <li><a href="https://external.example.com/tool">external tool</a></li>
  <li><a href="../../packages/arules/index.html">arules</a></li>
</ul></body></html>
"""

PACKAGE_PAGE_HTML = "<html><body><h2>ada: Boosted Regression</h2></body></html>"


def test_parse_packages_extracts_relative_links_only():
    packages = parse_packages(TASK_VIEW_HTML)

    assert packages == [
        ("ada", f"{CRAN_WEB_BASE}/packages/ada/index.html"),
        ("arules", f"{CRAN_WEB_BASE}/packages/arules/index.html"),
    ]


def test_parse_packages_strips_markup_from_names():
    html = """
    <html><body><ul>
      <li>
        <a href="../../packages/nnet/index.html"><span class="CRAN">nnet</span></a>
        <a href="../../packages/neuralnet/index.html">neuralnet</a>
        <a href="../../packages/keras/index.html">keras</a>
      </li>
    </ul></body></html>
    """

    packages = parse_packages(html)

    assert packages == [("nnet", f"{CRAN_WEB_BASE}/packages/nnet/index.html")]


def test_format_packages_renders_markdown_list():
    packages = [("ada", "http://example.org/ada", "Boosted Regression")]

    assert (
        format_packages(packages)
        == "* [ada](http://example.org/ada) - Boosted Regression\n"
    )


def test_build_packages_fetches_descriptions(mocker):
    mocker.patch(
        "scripts.pull_R_packages.fetch_page",
        side_effect=[PACKAGE_PAGE_HTML, PACKAGE_PAGE_HTML],
    )

    packages = build_packages(TASK_VIEW_HTML)

    assert len(packages) == 2
    assert packages[0] == (
        "ada",
        f"{CRAN_WEB_BASE}/packages/ada/index.html",
        "ada: Boosted Regression",
    )


def test_fetch_page_decodes_utf8(mocker):
    response = mocker.MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = "caf\u00e9".encode("utf-8")
    mocker.patch("urllib.request.urlopen", return_value=response)

    assert fetch_page("http://example.org") == "caf\u00e9"


def test_main_writes_output_file(mocker, tmp_path):
    mocker.patch("scripts.pull_R_packages.fetch_page", return_value=TASK_VIEW_HTML)
    mocker.patch(
        "scripts.pull_R_packages.fetch_description", return_value="Boosted Regression"
    )
    output = tmp_path / "Packages.txt"

    assert main(["--output", str(output)]) == 0

    content = output.read_text(encoding="utf-8")
    assert "* [ada]" in content
    assert "* [arules]" in content


def test_main_returns_error_when_fetch_fails(mocker):
    mocker.patch(
        "scripts.pull_R_packages.fetch_page",
        side_effect=OSError("connection refused"),
    )

    assert main(["--output", "Packages.txt"]) == 1

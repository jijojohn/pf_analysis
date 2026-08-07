"""Tests for shared report styling helpers (table rendering + HTML escaping)."""

from report_style import html_escape, render_table


def test_html_escape_blocks_injection():
    raw = "XYZ</td><script>alert('x')</script>"
    escaped = html_escape(raw)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_render_table_escapes_scalar_cells():
    rows = [["<b>evil</b>", 5]]
    html = render_table(["A", "B"], rows)
    assert "<b>evil</b>" not in html
    assert "&lt;b&gt;evil&lt;/b&gt;" in html


def test_render_table_allows_explicit_html_cells():
    rows = [[{"text": "<b>ok</b>", "html": True}]]
    html = render_table(["A"], rows)
    assert "<b>ok</b>" in html


def test_render_table_applies_class_and_align():
    rows = [[{"text": "1.0", "class": "positive", "align": "right"}]]
    html = render_table(["A"], rows)
    assert 'class="positive"' in html
    assert "text-align:right" in html


def test_render_table_sort_hint_toggle():
    assert "Click any column header to sort" in render_table(["A"], [[1]])
    assert "Click any column header to sort" not in render_table(["A"], [[1]], sort_hint=False)


def test_render_table_sortable_headers():
    html = render_table(["A", "B"], [[1, 2]])
    assert 'onclick="sortTable(this)"' in html

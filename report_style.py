#!/usr/bin/env python3
"""
Shared Report Style Module
Provides unified dark-theme CSS, sortable-table JS, navigation bar,
and "How This Report Works" helpers for all portfolio report generators.
"""

from datetime import date, datetime


def get_base_css() -> str:
    """Return unified dark-theme CSS used by every report."""
    return """
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Segoe UI',Arial,sans-serif; background:#0d1117; color:#c9d1d9; line-height:1.6; padding:0; margin:0; }
    .container { width:100%; padding:20px 24px; }

    /* ── Navigation Bar ── */
    .nav-bar { background:#161b22; border-bottom:1px solid #30363d; padding:10px 24px; display:flex; align-items:center; gap:16px; flex-wrap:wrap; position:sticky; top:0; z-index:100; }
    .nav-bar a { color:#58a6ff; text-decoration:none; font-weight:600; font-size:0.95em; }
    .nav-bar a:hover { text-decoration:underline; }
    .nav-bar .sep { color:#30363d; }
    .nav-bar .current { color:#c9d1d9; font-weight:400; }

    /* ── Headers ── */
    h1 { color:#58a6ff; text-align:center; margin:20px 0 5px; font-size:2em; }
    h2 { color:#58a6ff; margin:0 0 15px; padding-bottom:8px; border-bottom:1px solid #30363d; font-size:1.4em; }
    h3 { color:#c9d1d9; margin:0 0 10px; font-size:1.15em; }
    .subtitle { text-align:center; color:#8b949e; margin-bottom:25px; font-size:1.05em; }

    /* ── Cards & Sections ── */
    .section { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:20px; margin-bottom:20px; }
    .cards { display:flex; flex-wrap:wrap; gap:15px; margin-bottom:20px; justify-content:center; }
    .card { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:16px 20px; min-width:160px; text-align:center; flex:1 1 160px; }
    .card .label { color:#8b949e; font-size:0.85em; margin-bottom:4px; }
    .card .value { font-size:1.7em; font-weight:bold; }
    .card .sub { color:#8b949e; font-size:0.8em; margin-top:3px; }

    /* ── Grids ── */
    .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:15px; margin-bottom:20px; }
    .reports-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; }

    /* ── How-It-Works / Methodology ── */
    .how-it-works { background:#1c2128; border-left:4px solid #58a6ff; padding:16px 20px; margin:15px 0; border-radius:0 8px 8px 0; }
    .how-it-works h3 { color:#58a6ff; margin-bottom:8px; }
    .how-it-works p, .how-it-works li { color:#8b949e; font-size:0.9em; line-height:1.7; }
    .how-it-works ul { padding-left:20px; margin:6px 0; }
    .methodology { background:#1c2128; border-left:4px solid #58a6ff; padding:12px 16px; margin:15px 0; font-size:0.9em; color:#8b949e; border-radius:0 6px 6px 0; }

    /* ── Table Wrapper (scrollable, frozen header + 1st col) ── */
    .table-wrapper { overflow:auto; max-height:80vh; border:1px solid #30363d; border-radius:8px; margin:10px 0; position:relative; }
    table { width:100%; border-collapse:separate; border-spacing:0; font-size:0.85em; }
    thead th { background:#21262d; color:#58a6ff; padding:10px 8px; text-align:left; position:sticky; top:0; z-index:10; cursor:pointer; white-space:nowrap; border-bottom:2px solid #30363d; user-select:none; }
    thead th:first-child { position:sticky; left:0; z-index:15; }
    tbody td { padding:8px; border-bottom:1px solid #21262d; white-space:nowrap; }
    tbody td:first-child { position:sticky; left:0; z-index:5; background:#161b22; font-weight:600; border-right:1px solid #30363d; }
    tbody tr:hover { background:#1c2128; }
    tbody tr:hover td:first-child { background:#1c2128; }
    th .sort-arrow { font-size:0.7em; margin-left:3px; opacity:0.5; }
    th.sort-asc .sort-arrow::after { content:'▲'; }
    th.sort-desc .sort-arrow::after { content:'▼'; }

    /* ── Conditional Colors ── */
    .positive { color:#3fb950; }
    .negative { color:#f85149; }
    .neutral  { color:#d29922; }
    .profit   { color:#3fb950; font-weight:bold; }
    .loss     { color:#f85149; font-weight:bold; }
    .overbought { color:#f0883e; font-weight:bold; }
    .oversold   { color:#a371f7; font-weight:bold; }

    /* ── Report Link Buttons (for master/index) ── */
    .report-link { display:block; background:#21262d; color:#c9d1d9; text-decoration:none; padding:14px 18px; border-radius:8px; border:1px solid #30363d; transition:all 0.2s ease; font-weight:500; }
    .report-link:hover { background:#30363d; border-color:#58a6ff; transform:translateY(-2px); }
    .dataset-link { border-left:4px solid #3fb950; }
    .portfolio-link { border-left:4px solid #f0883e; }
    .analytics-link { border-left:4px solid #a371f7; }
    .filter-link { border-left:4px solid #58a6ff; }

    /* ── Misc ── */
    .bar { display:inline-block; height:18px; border-radius:3px; }
    .footer { text-align:center; color:#484f58; margin-top:30px; padding:20px; font-size:0.85em; border-top:1px solid #21262d; }
    .config-info { background:#1c2128; border-left:4px solid #58a6ff; padding:15px; border-radius:0 6px 6px 0; margin:15px 0; }
    .config-info .config-label { font-weight:600; color:#58a6ff; }
    .sort-hint { color:#484f58; font-size:0.8em; margin:4px 0 8px; }

    /* ── Quick Actions ── */
    .quick-actions { display:flex; gap:12px; flex-wrap:wrap; margin:15px 0; }
    .action-btn { background:#21262d; color:#58a6ff; padding:10px 20px; border-radius:20px; text-decoration:none; font-weight:500; border:1px solid #30363d; transition:all 0.2s; font-size:0.9em; }
    .action-btn:hover { background:#30363d; border-color:#58a6ff; }

    /* ── Guide Section (What / How / Actions) ── */
    .report-guide { background:#1c2128; border-radius:8px; padding:18px; margin:15px 0; }
    .guide-section { margin:12px 0; }
    .guide-section h3 { color:#58a6ff; font-size:1em; margin-bottom:4px; }
    .guide-section p { color:#8b949e; font-size:0.9em; line-height:1.6; }

    /* ── Filter Sidebar ── */
    .filter-selector { margin:15px 0; }
    .filter-selector h3 { color:#58a6ff; margin-bottom:8px; }
    .filter-selector ul { list-style:none; padding:0; display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:4px; }
    .filter-selector li { padding:4px 0; }
    .filter-selector li a { color:#58a6ff; text-decoration:none; font-size:0.85em; }
    .filter-selector li a:hover { text-decoration:underline; }

    /* ── Chart Sections ── */
    .chart-section { margin:15px 0; }
    .chart-container { margin:10px 0; }

    /* ── Animations ── */
    @keyframes pulse { 0%,100%{box-shadow:0 0 15px rgba(88,166,255,0.2);} 50%{box-shadow:0 0 25px rgba(88,166,255,0.4);} }
    .highlight { animation:pulse 2.5s infinite; border-color:#58a6ff !important; }

    /* ── Responsive ── */
    @media (max-width:768px) {
        .container { padding:10px 12px; }
        h1 { font-size:1.5em; }
        h2 { font-size:1.15em; }
        .nav-bar { padding:8px 12px; font-size:0.85em; }
        .cards { gap:8px; }
        .card { min-width:120px; padding:10px; }
        .card .value { font-size:1.3em; }
        .summary-grid { grid-template-columns:1fr 1fr; gap:8px; }
        .reports-grid { grid-template-columns:1fr; }
        table { font-size:0.75em; }
        thead th, tbody td { padding:6px 4px; }
        .report-guide { padding:12px; }
        .quick-actions { justify-content:center; }
        .filter-selector ul { grid-template-columns:1fr; }
    }
    @media (max-width:480px) {
        .summary-grid { grid-template-columns:1fr; }
        .card { min-width:100%; }
    }
"""


def get_sortable_table_js() -> str:
    """Return JS that sorts any table when a <th> is clicked."""
    return """
    function sortTable(header) {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const idx = Array.from(header.parentNode.children).indexOf(header);
        const asc = !header.classList.contains('sort-asc');

        // Reset all headers
        header.parentNode.querySelectorAll('th').forEach(th => {
            th.classList.remove('sort-asc','sort-desc');
        });
        header.classList.add(asc ? 'sort-asc' : 'sort-desc');

        rows.sort((a,b) => {
            let va = a.children[idx]?.textContent.trim() || '';
            let vb = b.children[idx]?.textContent.trim() || '';
            // Strip currency/percent symbols for numeric sort
            let na = parseFloat(va.replace(/[₹,%★☆x]/g,'').replace(/,/g,''));
            let nb = parseFloat(vb.replace(/[₹,%★☆x]/g,'').replace(/,/g,''));
            if (!isNaN(na) && !isNaN(nb)) return asc ? na-nb : nb-na;
            return asc ? va.localeCompare(vb) : vb.localeCompare(va);
        });
        rows.forEach(r => tbody.appendChild(r));
    }
"""


def get_nav_bar(current_title: str) -> str:
    """Return a sticky navigation bar linking back to index.html."""
    return f"""
    <nav class="nav-bar">
        <a href="index.html">&#127968; Home</a>
        <span class="sep">&#8250;</span>
        <span class="current">{current_title}</span>
    </nav>
"""


def get_how_it_works(title: str, items: list) -> str:
    """Return a 'How This Report Works' section.

    Args:
        title: Section heading (e.g. "How This Report Works")
        items: List of (label, description) tuples.
    """
    rows = ""
    for label, desc in items:
        rows += f"            <li><strong>{label}:</strong> {desc}</li>\n"
    return f"""
    <div class="how-it-works">
        <h3>&#128214; {title}</h3>
        <ul>
{rows}        </ul>
    </div>
"""


def get_report_header(title: str, subtitle: str = "", nav_title: str = "") -> str:
    """Return standard dark-theme HTML head + opening body/container + nav bar.

    Args:
        title: Page <title> and <h1>
        subtitle: Optional subtitle below h1
        nav_title: Nav bar current page label (defaults to title)
    """
    nav = get_nav_bar(nav_title or title)
    sub_html = f'    <p class="subtitle">{subtitle}</p>' if subtitle else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{get_base_css()}</style>
<script>{get_sortable_table_js()}</script>
</head>
<body>
{nav}
<div class="container">
    <h1>{title}</h1>
{sub_html}
"""


def get_report_footer() -> str:
    """Return standard footer + closing tags."""
    return f"""
    <div class="footer">
        Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} &bull; Portfolio Analysis System v2.0
    </div>
</div>
</body>
</html>
"""


def html_escape(value) -> str:
    """Escape a value for safe insertion into HTML (prevents injection/XSS).

    Any value type is accepted and converted to ``str`` first.
    """
    import html as _html
    return _html.escape(str(value), quote=True)


def render_table(columns, rows, sortable: bool = True, sort_hint: bool = True) -> str:
    """Render a sortable, frozen-header HTML table from data.

    Centralizes table generation that was previously duplicated (and
    inconsistently escaped) across report modules.

    Args:
        columns: List of header labels (str). Headers are NOT escaped so callers
            may pass small HTML snippets (e.g. arrows); pass plain text normally.
        rows: List of rows. Each row is a list of cells. A cell may be:
            - a scalar (str/number) -> escaped and rendered as text, or
            - a dict with keys:
                'text'  : cell content (escaped unless 'html' is True),
                'class' : optional CSS class for the <td>,
                'html'  : if True, 'text' is treated as raw HTML (caller-safe),
                'align' : optional text alignment ('left'/'center'/'right').
        sortable: If True, headers get the onclick sort handler.
        sort_hint: If True, prepend a "Click any column header to sort" hint.

    Returns:
        HTML string containing an optional hint plus a ``.table-wrapper`` table.
    """
    # Header
    th_parts = []
    for col in columns:
        onclick = ' onclick="sortTable(this)"' if sortable else ''
        th_parts.append(f'<th{onclick}>{col}</th>')
    header_html = '<thead><tr>' + ''.join(th_parts) + '</tr></thead>'

    # Body (build as list then join — avoids string concatenation in loops)
    body_parts = []
    for row in rows:
        cell_parts = []
        for cell in row:
            if isinstance(cell, dict):
                raw = cell.get('text', '')
                content = str(raw) if cell.get('html') else html_escape(raw)
                attrs = ''
                css = cell.get('class')
                if css:
                    attrs += f' class="{css}"'
                align = cell.get('align')
                if align:
                    attrs += f' style="text-align:{align}"'
                cell_parts.append(f'<td{attrs}>{content}</td>')
            else:
                cell_parts.append(f'<td>{html_escape(cell)}</td>')
        body_parts.append('<tr>' + ''.join(cell_parts) + '</tr>')
    body_html = '<tbody>' + ''.join(body_parts) + '</tbody>'

    hint = '<p class="sort-hint">Click any column header to sort</p>' if (sortable and sort_hint) else ''
    return f"""{hint}
<div class="table-wrapper">
<table>
{header_html}
{body_html}
</table>
</div>"""


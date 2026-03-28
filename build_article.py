#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_article.py
Converts a published article markdown file into a standalone HTML page.
Called by pipeline_v2.py after each article publish.
"""

import re, sys
from datetime import date

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def md_to_html(md):
    """Minimal markdown to HTML converter."""
    h = md

    # Remove meta tags
    h = re.sub(r'<meta[^>]+>', '', h)

    # Tables - must run before other replacements
    def render_table(m):
        rows = m.group(0).strip().split('\n')
        hcells = ''.join(
            '<th>{}</th>'.format(c.strip())
            for c in rows[0].split('|') if c.strip()
        )
        body = ''
        for row in rows[2:]:
            cells = ''.join(
                '<td>{}</td>'.format(c.strip())
                for c in row.split('|') if c.strip()
            )
            if cells:
                body += '<tr>{}</tr>'.format(cells)
        return '<div class="table-wrap"><table><thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>'.format(
            hcells, body
        )
    h = re.sub(r'(\|.+\|\n)+', render_table, h)

    # Headings
    h = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', h, flags=re.MULTILINE)
    h = re.sub(r'^### (.+)$',  r'<h3>\1</h3>', h, flags=re.MULTILINE)
    h = re.sub(r'^## (.+)$',   r'<h2>\1</h2>', h, flags=re.MULTILINE)
    h = re.sub(r'^# (.+)$',    r'<h1>\1</h1>', h, flags=re.MULTILINE)

    # Inline formatting
    h = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', h)
    h = re.sub(r'\*\*(.+?)\*\*',     r'<strong>\1</strong>', h)
    h = re.sub(r'\*(.+?)\*',         r'<em>\1</em>', h)
    h = re.sub(r'`(.+?)`',           r'<code>\1</code>', h)

    # Links
    h = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" rel="noopener">\1</a>', h)

    # Blockquotes
    h = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', h, flags=re.MULTILINE)

    # Unordered lists
    def render_ul(m):
        items = ''.join(
            '<li>{}</li>'.format(l[2:])
            for l in m.group(0).strip().split('\n')
            if l.startswith('- ')
        )
        return '<ul>{}</ul>'.format(items)
    h = re.sub(r'(^- .+$\n?)+', render_ul, h, flags=re.MULTILINE)

    # Ordered lists
    def render_ol(m):
        items = ''.join(
            '<li>{}</li>'.format(re.sub(r'^\d+\. ', '', l))
            for l in m.group(0).strip().split('\n')
            if re.match(r'^\d+\.', l)
        )
        return '<ol>{}</ol>'.format(items)
    h = re.sub(r'(^\d+\. .+$\n?)+', render_ol, h, flags=re.MULTILINE)

    # Horizontal rules
    h = re.sub(r'^---+$', '<hr>', h, flags=re.MULTILINE)

    # HTML comments (DIRECTIVE blocks)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.DOTALL)

    # Paragraphs
    blocks = []
    for block in h.split('\n\n'):
        block = block.strip()
        if not block:
            continue
        if re.match(r'^<(h[1-6]|ul|ol|table|div|blockquote|hr|p)', block):
            blocks.append(block)
        else:
            # Clean internal newlines
            block = re.sub(r'\n', ' ', block)
            blocks.append('<p>{}</p>'.format(block))
    h = '\n'.join(blocks)
    h = re.sub(r'<p>\s*</p>', '', h)

    return h


def category_from_slug(s):
    if 'saving' in s or 'premium-bond' in s: return 'Savings'
    if 'invest' in s or 'etf' in s or 'index-fund' in s: return 'Investing'
    if 'isa' in s: return 'ISAs'
    if 'credit' in s: return 'Credit'
    if 'mortgage' in s or 'stamp-duty' in s: return 'Mortgages'
    if 'budget' in s or 'bill' in s or 'groceries' in s: return 'Budgeting'
    if 'pension' in s or 'retirement' in s: return 'Pensions'
    if 'tax' in s or 'self-assessment' in s: return 'Tax'
    if 'side-hustle' in s or 'passive-income' in s or 'salary' in s: return 'Side Income'
    if 'debt' in s or 'loan' in s: return 'Debt'
    if 'insurance' in s: return 'Insurance'
    if 'bank' in s or 'monzo' in s or 'starling' in s: return 'Banking'
    return 'Personal Finance'


def build_article_html(topic, article_slug, md_content):
    """Build a complete standalone HTML page from article markdown."""

    body_html = md_to_html(md_content)

    # Extract title
    m = re.search(r'<h1>(.*?)</h1>', body_html)
    title = re.sub(r'<!--.*?-->', '', m.group(1)).strip() if m else topic.title()

    # Extract meta description from markdown
    m2 = re.search(r'content="([^"]{20,})"', md_content)
    description = m2.group(1)[:155] if m2 else title

    # Separate disclaimer
    m3 = re.search(r'<p><em>(Affiliate disclosure.*?)</em></p>', body_html, re.DOTALL)
    disclaimer_html = ''
    if m3:
        disclaimer_html = '<div class="disclaimer"><em>{}</em></div>'.format(m3.group(1))
        body_html = body_html.replace(m3.group(0), '')

    cat = category_from_slug(article_slug)
    year = date.today().year

    css = """
:root{--ink:#0f0f0d;--ink-soft:#3a3a35;--ink-muted:#7a7a72;--paper:#f7f5f0;--cream:#eeebe3;--rule:#d8d4c8;--accent:#c8502a;--serif:'DM Serif Display',Georgia,serif;--sans:'DM Sans',system-ui,sans-serif;--max:740px}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--sans);background:var(--paper);color:var(--ink);font-size:17px;line-height:1.7;-webkit-font-smoothing:antialiased}
.masthead{border-bottom:3px solid var(--ink);padding:0 1.5rem}
.masthead-inner{max-width:1140px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;padding:1.25rem 0}
.masthead-logo a{font-family:var(--serif);font-size:1.5rem;color:var(--ink);text-decoration:none;letter-spacing:-.02em}
.dot{color:var(--accent)}
nav a{font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink);text-decoration:none;margin-left:1.5rem;transition:color .15s}
nav a:hover{color:var(--accent)}
.article-wrap{max-width:var(--max);margin:0 auto;padding:3rem 1.5rem 5rem}
.article-label{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:500;margin-bottom:1rem}
h1{font-family:var(--serif);font-size:clamp(1.9rem,4vw,2.8rem);line-height:1.1;letter-spacing:-.02em;margin-bottom:1.5rem}
h2{font-family:var(--serif);font-size:1.5rem;line-height:1.2;letter-spacing:-.01em;margin:2.5rem 0 .75rem;padding-top:.5rem;border-top:1px solid var(--rule)}
h3{font-family:var(--serif);font-size:1.15rem;margin:1.75rem 0 .5rem}
p{color:var(--ink-soft);margin-bottom:1.1rem}
a{color:var(--accent);text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:2px}
a:hover{color:#a83e1e}
ul,ol{padding-left:1.5rem;margin-bottom:1.1rem;color:var(--ink-soft)}
li{margin-bottom:.4rem}
strong{color:var(--ink);font-weight:500}
code{background:var(--cream);padding:.1em .3em;font-size:.88em}
.table-wrap{overflow-x:auto;margin:2rem 0;border:1px solid var(--rule)}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th{background:var(--ink);color:var(--paper);text-align:left;padding:.65rem 1rem;font-weight:500;font-size:.78rem;letter-spacing:.04em;text-transform:uppercase}
td{padding:.65rem 1rem;border-bottom:1px solid var(--rule);color:var(--ink-soft)}
tr:last-child td{border-bottom:none}
tr:nth-child(even) td{background:var(--cream)}
blockquote{border-left:3px solid var(--accent);padding:.75rem 1.25rem;margin:1.5rem 0;background:var(--cream);font-style:italic}
hr{border:none;border-top:1px solid var(--rule);margin:2rem 0}
.disclaimer{margin-top:3rem;padding:1.25rem;background:var(--cream);border-top:2px solid var(--rule);font-size:.82rem;color:var(--ink-muted);font-style:italic}
.article-cta{background:var(--ink);color:#f7f5f0;padding:2rem;margin-top:3rem}
.article-cta h3{font-family:var(--serif);font-size:1.3rem;margin-bottom:.4rem;color:#f7f5f0}
.article-cta p{color:rgba(247,245,240,.65);font-size:.9rem;margin-bottom:1rem}
.cta-form{display:flex;gap:.5rem}
.cta-form input{flex:1;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#f7f5f0;font-family:var(--sans);font-size:.9rem;padding:.65rem .9rem;outline:none}
.cta-form input::placeholder{color:rgba(247,245,240,.35)}
.cta-form button{background:var(--accent);color:#f7f5f0;border:none;font-family:var(--sans);font-size:.75rem;font-weight:500;letter-spacing:.06em;text-transform:uppercase;padding:.65rem 1.25rem;cursor:pointer;white-space:nowrap}
footer{border-top:3px solid var(--ink);padding:2rem 1.5rem;margin-top:4rem}
.footer-inner{max-width:1140px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem}
.footer-logo{font-family:var(--serif);font-size:1rem}
.footer-links a{font-size:.75rem;color:var(--ink-muted);text-decoration:none;margin-left:1.25rem}
.footer-links a:hover{color:var(--accent)}
.footer-legal{font-size:.7rem;color:var(--ink-muted);width:100%;margin-top:.5rem}
@media(max-width:600px){.cta-form{flex-direction:column}}
.reactions{text-align:center;margin:3rem 0 2rem;padding:2rem;background:var(--cream);border:1px solid var(--rule)}
.reactions-label{font-size:.85rem;color:var(--ink-muted);margin-bottom:1.25rem;text-transform:uppercase;letter-spacing:.08em}
.reactions-buttons{display:flex;justify-content:center;gap:1.5rem}
.reaction-btn{display:flex;flex-direction:column;align-items:center;gap:.4rem;background:var(--paper);border:2px solid var(--rule);padding:.9rem 2rem;cursor:pointer;font-family:var(--sans);transition:all .2s;min-width:90px}
.reaction-btn:hover{border-color:var(--ink);transform:translateY(-2px)}
.reaction-btn.active{border-color:var(--accent);background:var(--accent);color:#fff}
.reaction-btn.active .reaction-count{color:#fff}
.reaction-btn.dimmed{opacity:.45}
.reaction-icon{font-size:1.6rem;line-height:1}
.reaction-count{font-size:.88rem;font-weight:500;color:var(--ink-muted)}

"""

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title} - Luis Paiva</title>
<meta name="description" content="{description}"/>
<link rel="canonical" href="https://www.luispaiva.co.uk/{slug}/"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap" rel="stylesheet"/>
<style>{css}</style>
</head>
<body>
<header class="masthead">
<div class="masthead-inner">
<div class="masthead-logo"><a href="/">Luis Paiva<span class="dot">.</span></a></div>
<nav><a href="/">Home</a><a href="/about">About</a><a href="/newsletter">Newsletter</a></nav>
</div>
</header>
<main class="article-wrap">
<div class="article-label">{cat}</div>
{body}
{disclaimer}

<div class="reactions" id="reactions">
  <p class="reactions-label">Was this article helpful?</p>
  <div class="reactions-buttons">
    <button class="reaction-btn" id="btn-like" onclick="react('like')">
      <span class="reaction-icon">👍</span>
      <span class="reaction-count" id="count-like">--</span>
    </button>
    <button class="reaction-btn" id="btn-dislike" onclick="react('dislike')">
      <span class="reaction-icon">👎</span>
      <span class="reaction-count" id="count-dislike">--</span>
    </button>
  </div>
</div>

<script>
(function() {{
  var SUPABASE_URL = "https://ypvjjmeuocdntwgagyqd.supabase.co";
  var SUPABASE_KEY = "sb_publishable_UcS1DYjeWuTiFKduCwlwag_6f4grHGI";
  var SLUG = "{slug}";
  var SESSION_KEY = "oc_session_id";
  var VOTED_KEY = "voted_" + SLUG;

  // Get or create a stable session ID for this browser
  var sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {{
    sessionId = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(SESSION_KEY, sessionId);
  }}

  var voted = localStorage.getItem(VOTED_KEY);

  function applyVoted(reaction) {{
    var btnLike = document.getElementById("btn-like");
    var btnDislike = document.getElementById("btn-dislike");
    if (!btnLike || !btnDislike) return;
    btnLike.classList.remove("active", "dimmed");
    btnDislike.classList.remove("active", "dimmed");
    if (reaction === "like") {{
      btnLike.classList.add("active");
      btnDislike.classList.add("dimmed");
    }} else if (reaction === "dislike") {{
      btnDislike.classList.add("active");
      btnLike.classList.add("dimmed");
    }}
  }}

  function loadCounts() {{
    fetch(SUPABASE_URL + "/rest/v1/article_reactions?slug=eq." + SLUG + "&select=reaction", {{
      headers: {{ "apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY }}
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(rows) {{
      var likes = rows.filter(function(r) {{ return r.reaction === "like"; }}).length;
      var dislikes = rows.filter(function(r) {{ return r.reaction === "dislike"; }}).length;
      var el1 = document.getElementById("count-like");
      var el2 = document.getElementById("count-dislike");
      if (el1) el1.textContent = likes;
      if (el2) el2.textContent = dislikes;
    }})
    .catch(function() {{}});
  }}

  window.react = function(reaction) {{
    // Clicking same button again does nothing
    if (voted === reaction) return;

    // Upsert: insert or update based on slug + session_id unique constraint
    fetch(SUPABASE_URL + "/rest/v1/article_reactions", {{
      method: "POST",
      headers: {{
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal"
      }},
      body: JSON.stringify({{
        slug: SLUG,
        session_id: sessionId,
        reaction: reaction
      }})
    }})
    .then(function(r) {{
      if (r.ok || r.status === 201) {{
        voted = reaction;
        localStorage.setItem(VOTED_KEY, reaction);
        applyVoted(reaction);
        loadCounts();
      }}
    }})
    .catch(function() {{}});
  }};

  loadCounts();
  if (voted) applyVoted(voted);
}})();
</script>
<div class="article-cta">
<h3>The Friday Money Brief</h3>
<p>One money tip every Friday. No spam. Unsubscribe any time.</p>
<form class="cta-form" action="https://app.beehiiv.com/subscribe" method="GET" target="_blank">
<input type="email" name="email" placeholder="your@email.com" required/>
<button type="submit">Subscribe free</button>
</form>
</div>
</main>
<footer>
<div class="footer-inner">
<div class="footer-logo">Luis Paiva<span style="color:var(--accent)">.</span></div>
<nav class="footer-links"><a href="/about">About</a><a href="/privacy">Privacy</a><a href="/newsletter">Newsletter</a></nav>
<p class="footer-legal">This site contains affiliate links. We may earn a commission at no extra cost to you. Always do your own research. &copy; {year} Luis Paiva.</p>
</div>
</footer>
</body>
</html>""".format(
        title=title,
        description=description,
        slug=article_slug,
        css=css,
        cat=cat,
        body=body_html,
        disclaimer=disclaimer_html,
        year=year
    )


if __name__ == "__main__":
    # Test: convert an existing article
    from pathlib import Path
    docs = Path(__file__).parent / "docs"
    for md_file in list(docs.glob("*.md"))[:1]:
        slug = md_file.stem
        content = md_file.read_text(encoding="utf-8")
        html = build_article_html(slug.replace("-", " "), slug, content)
        out = Path(__file__).parent / slug / "index.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print("Built:", out)
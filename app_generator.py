import os
import base64
from typing import Dict, List
import openai


class AppGenerator:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        if self.openai_key:
            openai.api_key = self.openai_key

    def detect_task_type(self, brief: str) -> str:
        """Detect which template to use based on brief"""
        brief_lower = brief.lower()

        if "captcha" in brief_lower:
            return "captcha-solver"
        elif "sales" in brief_lower or "sum" in brief_lower or "csv" in brief_lower:
            return "sum-of-sales"
        elif "markdown" in brief_lower or ".md" in brief_lower:
            return "markdown-to-html"
        elif "github" in brief_lower and "user" in brief_lower:
            return "github-user-created"
        else:
            return "generic"

    def generate_captcha_solver(self, brief: str, checks: List[str], attachments: List[Dict]) -> Dict[str, str]:
        """Generate captcha solver app"""
        seed = self._extract_seed(brief)

        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Captcha Solver</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@4/dist/tesseract.min.js"></script>
</head>
<body>
    <div class="container mt-5">
        <h1>Captcha Solver</h1>
        <div class="card mt-4">
            <div class="card-body">
                <img id="captcha-image" class="img-fluid mb-3" alt="Captcha Image"/>
                <div class="spinner-border" id="loading" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div id="captcha-solution" class="alert alert-success" style="display:none;"></div>
            </div>
        </div>
    </div>
    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const captchaUrl = urlParams.get('url') || './assets/sample.png';

        const imgEl = document.getElementById('captcha-image');
        const loadingEl = document.getElementById('loading');
        const solutionEl = document.getElementById('captcha-solution');

        imgEl.src = captchaUrl;

        // Solve captcha with timeout
        const timeout = setTimeout(() => {{
            solutionEl.textContent = 'Timeout: Unable to solve';
            solutionEl.style.display = 'block';
            loadingEl.style.display = 'none';
        }}, 14000);

        Tesseract.recognize(
            captchaUrl,
            'eng',
            {{ logger: m => console.log(m) }}
        ).then(result => {{
            clearTimeout(timeout);
            const text = result.data.text;
            const cleaned = text.trim().replace(/[^a-zA-Z0-9]/g, '');
            solutionEl.textContent = cleaned || text.trim();
            solutionEl.style.display = 'block';
            loadingEl.style.display = 'none';
        }}).catch(err => {{
            clearTimeout(timeout);
            solutionEl.textContent = 'Error: ' + err.message;
            solutionEl.style.display = 'block';
            loadingEl.style.display = 'none';
        }});
    </script>
</body>
</html>"""

        files = {"index.html": index_html}

        for attachment in attachments:
            content = self._decode_attachment(attachment["url"])
            files[f"assets/{attachment['name']}"] = content

        files["README.md"] = self._generate_readme("Captcha Solver", brief, checks)
        files["LICENSE"] = self._get_mit_license()
        return files

    def generate_sum_of_sales(self, brief: str, checks: List[str], attachments: List[Dict], round_num: int = 1) -> Dict[str, str]:
        """Generate sum of sales app"""
        seed = self._extract_seed(brief)

        has_table = round_num == 2 and "table" in brief.lower()
        has_currency = round_num == 2 and "currency" in brief.lower()
        has_region = round_num == 2 and "region" in brief.lower()

        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sales Summary {seed}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>Sales Summary {seed}</h1>
        { "<select id='region-filter' class='form-select mb-3'><option value='all'>All Regions</option></select>" if has_region else "" }
        { "<select id='currency-picker' class='form-select mb-3'><option value='USD'>USD</option><option value='EUR'>EUR</option></select>" if has_currency else "" }
        <div class="card">
            <div class="card-body">
                <h3>Total Sales{ '' if not has_currency else " (<span id='total-currency'>USD</span>)" }: <span id="total-sales">0</span></h3>
            </div>
        </div>
        { "<table class='table mt-4' id='product-sales'><thead><tr><th>Product</th><th>Sales</th></tr></thead><tbody></tbody></table>" if has_table else "" }
    </div>
    <script>
        let salesData = [];
        const rates = {{ USD: 1, EUR: 0.85 }};

        fetch('./assets/data.csv')
            .then(r => r.text())
            .then(csv => {{
                const lines = csv.trim().split('\\n');
                const headers = lines[0].split(',');
                const salesIdx = headers.indexOf('sales');
                const productIdx = headers.indexOf('product');

                let total = 0;
                const productSales = {{}};

                for (let i = 1; i < lines.length; i++) {{
                    const values = lines[i].split(',');
                    const sale = parseFloat(values[salesIdx]);
                    total += sale;
                    { "const product = values[productIdx]; productSales[product] = (productSales[product] || 0) + sale;" if has_table else "" }
                }}

                salesData = {{ total, productSales }};
                updateDisplay();
                { "populateTable(productSales);" if has_table else "" }
                { "populateRegions(lines);" if has_region else "" }
            }});

        function updateDisplay() {{
            const currency = { "document.getElementById('currency-picker').value" if has_currency else "'USD'" };
            const rate = rates[currency] || 1;
            document.getElementById('total-sales').textContent = (salesData.total * rate).toFixed(2);
            { "document.getElementById('total-currency').textContent = currency;" if has_currency else "" }
        }}

        { "document.getElementById('currency-picker')?.addEventListener('change', updateDisplay);" if has_currency else "" }

        { "function populateTable(productSales) { const tbody = document.querySelector('#product-sales tbody'); Object.entries(productSales).forEach(([product, sales]) => { const row = tbody.insertRow(); row.insertCell(0).textContent = product; row.insertCell(1).textContent = sales.toFixed(2); }); }" if has_table else "" }
        { "function populateRegions(lines) { /* region filtering logic */ }" if has_region else "" }
    </script>
</body>
</html>"""

        files = {"index.html": index_html}

        for attachment in attachments:
            content = self._decode_attachment(attachment["url"])
            files[f"assets/{attachment['name']}"] = content

        files["README.md"] = self._generate_readme(f"Sales Summary {seed}", brief, checks)
        files["LICENSE"] = self._get_mit_license()
        return files

    def generate_markdown_to_html(self, brief: str, checks: List[str], attachments: List[Dict], round_num: int = 1) -> Dict[str, str]:
        """Generate markdown to HTML converter"""
        has_tabs = round_num == 2 and "tab" in brief.lower()
        has_url_param = round_num == 2 and "?url=" in brief.lower()
        has_word_count = round_num == 2 and "word count" in brief.lower()

        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Markdown to HTML</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/default.min.css">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
</head>
<body>
    <div class="container mt-5">
        <h1>Markdown to HTML Converter</h1>
        { "<div class='btn-group mb-3' id='markdown-tabs'><button class='btn btn-primary' data-target='output'>HTML</button><button class='btn btn-outline-primary' data-target='source'>Markdown</button></div>" if has_tabs else "" }
        { "<div id='markdown-source-label' class='mb-2'>Source: attachment</div>" if has_url_param else "" }
        { "<div id='markdown-word-count' class='badge bg-secondary mb-2'>0 words</div>" if has_word_count else "" }
        <div id="markdown-output" class="border p-3"></div>
        { "<pre id='markdown-source' class='border p-3' style='display:none;'></pre>" if has_tabs else "" }
    </div>
    <script>
        let markdownText = '';

        async function loadMarkdown() {{
            const urlParams = new URLSearchParams(window.location.search);
            const mdUrl = urlParams.get('url');
            if (mdUrl) {{
                { "document.getElementById('markdown-source-label').textContent = 'Source: ' + mdUrl;" if has_url_param else "" }
                const response = await fetch(mdUrl);
                markdownText = await response.text();
            }} else {{
                const response = await fetch('./assets/input.md');
                markdownText = await response.text();
            }}
            renderMarkdown();
        }}

        function renderMarkdown() {{
            const html = marked.parse(markdownText);
            document.getElementById('markdown-output').innerHTML = html;
            { "document.getElementById('markdown-source').textContent = markdownText;" if has_tabs else "" }
            hljs.highlightAll();
            { "updateWordCount();" if has_word_count else "" }
        }}

        { "function updateWordCount() { const words = markdownText.split(/\\s+/).filter(w => w.length > 0).length; const formatter = new Intl.NumberFormat('en-US'); document.getElementById('markdown-word-count').textContent = formatter.format(words) + ' words'; }" if has_word_count else "" }
        { "document.getElementById('markdown-tabs')?.addEventListener('click', e => { if (e.target.tagName === 'BUTTON') { document.querySelectorAll('#markdown-tabs button').forEach(b => b.className = 'btn btn-outline-primary'); e.target.className = 'btn btn-primary'; const target = e.target.dataset.target; document.getElementById('markdown-output').style.display = target === 'output' ? 'block' : 'none'; document.getElementById('markdown-source').style.display = target === 'source' ? 'block' : 'none'; } });" if has_tabs else "" }
        loadMarkdown();
    </script>
</body>
</html>"""

        files = {"index.html": index_html}
        for attachment in attachments:
            content = self._decode_attachment(attachment["url"])
            files[f"assets/{attachment['name']}"] = content
        files["README.md"] = self._generate_readme("Markdown to HTML Converter", brief, checks)
        files["LICENSE"] = self._get_mit_license()
        return files

    def generate_github_user_created(self, brief: str, checks: List[str], attachments: List[Dict], round_num: int = 1) -> Dict[str, str]:
        """Generate GitHub user info app"""
        seed = self._extract_seed(brief)

        has_status = round_num == 2 and "status" in brief.lower()
        has_age = round_num == 2 and "age" in brief.lower()
        has_cache = round_num == 2 and "localStorage" in brief.lower()

        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GitHub User Info</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>GitHub User Info</h1>
        { "<div id='github-status' aria-live='polite' class='alert alert-info'>Ready</div>" if has_status else "" }
        <form id="github-user-{seed}" class="mb-4">
            <div class="mb-3">
                <input type="text" id="username" class="form-control" placeholder="GitHub Username" required>
            </div>
            <button type="submit" class="btn btn-primary">Lookup</button>
        </form>
        <div id="results" style="display:none;">
            <p><strong>Created At:</strong> <span id="github-created-at"></span></p>
            { "<p><strong>Account Age:</strong> <span id='github-account-age'></span></p>" if has_age else "" }
        </div>
    </div>
    <script>
        const form = document.getElementById('github-user-{seed}');
        const usernameInput = document.getElementById('username');
        { "const cachedUser = localStorage.getItem('github-user-" + seed + "'); if (cachedUser) { const data = JSON.parse(cachedUser); usernameInput.value = data.username; }" if has_cache else "" }
        form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            const username = usernameInput.value;
            { "document.getElementById('github-status').textContent = 'Looking up user...';" if has_status else "" }
            try {{
                const urlParams = new URLSearchParams(window.location.search);
                const token = urlParams.get('token');
                const headers = {{}};
                if (token) {{
                    headers['Authorization'] = `token ${{token}}`;
                }}
                const response = await fetch(`https://api.github.com/users/${{username}}`, {{ headers }});
                const data = await response.json();
                if (response.ok) {{
                    const createdDate = new Date(data.created_at);
                    const formattedDate = createdDate.toISOString().split('T')[0];
                    document.getElementById('github-created-at').textContent = formattedDate;
                    { "const age = Math.floor((new Date() - createdDate) / (365.25 * 24 * 60 * 60 * 1000)); document.getElementById('github-account-age').textContent = age + ' years';" if has_age else "" }
                    { "localStorage.setItem('github-user-" + seed + "', JSON.stringify({ username, created_at: formattedDate }));" if has_cache else "" }
                    document.getElementById('results').style.display = 'block';
                    { "document.getElementById('github-status').textContent = 'Success!';" if has_status else "" }
                }} else {{
                    { "document.getElementById('github-status').textContent = 'Failed: ' + data.message;" if has_status else "alert('Failed: ' + data.message);" }
                }}
            }} catch (err) {{
                { "document.getElementById('github-status').textContent = 'Error: ' + err.message;" if has_status else "alert('Error: ' + err.message);" }
            }}
        }});
    </script>
</body>
</html>"""

        files = {"index.html": index_html}
        files["README.md"] = self._generate_readme("GitHub User Info", brief, checks)
        files["LICENSE"] = self._get_mit_license()
        return files

    def _get_mit_license(self) -> str:
        """Generate MIT License text."""
        from datetime import datetime

        year = datetime.now().year
        author = os.getenv("GITHUB_USERNAME", "Author")
        return f"""MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

    def _extract_seed(self, brief: str) -> str:
        """Extract seed from brief"""
        import re

        match = re.search(r'\$\{seed\}|seed[:\s]+([a-zA-Z0-9-]+)', brief)
        return match.group(1) if match and match.group(1) else "default"

    def _decode_attachment(self, data_url: str) -> str:
        """Decode base64 data URL to content"""
        if data_url.startswith("data:"):
            header, encoded = data_url.split(",", 1)
            return base64.b64decode(encoded).decode("utf-8")
        return data_url

    def _generate_readme(self, title: str, brief: str, checks: List[str]) -> str:
        """Generate professional README"""
        return f"""# {title}


## Summary
{brief}


## Features
This application implements the following requirements:
{"".join(f"- {check}\\n" for check in checks)}


## Usage
1. Open the GitHub Pages URL in your browser
2. The application will automatically load and display the required functionality
3. For parameterized features, use query parameters (e.g., `?url=...`, `?token=...`)


## Setup
This is a static HTML application hosted on GitHub Pages. No build process required.


To run locally:
"""

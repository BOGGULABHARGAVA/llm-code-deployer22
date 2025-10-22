import os
import json
import re
import base64
from openai import OpenAI

class AppGenerator:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")
        self.client = OpenAI(api_key=api_key)
    
    def generate(self, task_name: str, brief: str, checks: list, attachments: list = None) -> dict:
        """Generate application files based on brief"""
        
        # Detect task type from brief
        task_type = self._detect_task_type(brief)
        print(f"Detected task type: {task_type}")
        
        # Generate appropriate files based on task type
        if task_type == "sec_data_visualization":
            return self._generate_sec_app(task_name, brief, checks, attachments)
        else:
            return self._generate_generic_app(task_name, brief, checks, attachments)
    
    def _detect_task_type(self, brief: str) -> str:
        """Detect what type of application to generate"""
        brief_lower = brief.lower()
        
        if any(keyword in brief_lower for keyword in ['sec.gov', 'xbrl', 'cik', 'sec api', 'companyconcept']):
            return "sec_data_visualization"
        elif any(keyword in brief_lower for keyword in ['chart', 'graph', 'plot', 'visualization']):
            return "data_visualization"
        elif any(keyword in brief_lower for keyword in ['calculator', 'calculate', 'compute']):
            return "calculator"
        elif any(keyword in brief_lower for keyword in ['todo', 'task list', 'checklist']):
            return "todo_app"
        else:
            return "generic"
    
    def _generate_sec_app(self, task_name: str, brief: str, checks: list, attachments: list) -> dict:
        """Generate SEC data visualization app"""
        
        prompt = f"""Create a complete, production-ready web application with these EXACT requirements:

TASK: {task_name}

BRIEF:
{brief}

REQUIREMENTS (ALL MUST BE MET):
{chr(10).join(f'- {check}' for check in checks)}

CRITICAL INSTRUCTIONS:

1. FILE STRUCTURE - Generate these files:
   - index.html (complete HTML with embedded CSS and JavaScript)
   - data.json (valid JSON with fetched SEC data)
   - LICENSE (MIT License text)
   - README.md (comprehensive documentation)
   - uid.txt (if attachment provided, copy exactly as-is)

2. INDEX.HTML REQUIREMENTS:
   - Fetch SEC API data from the URL provided in the brief
   - Display data in a responsive HTML table
   - Create a Chart.js line/bar chart showing the data over time
   - Support ?CIK= query parameter to load different companies dynamically
   - Use modern, clean CSS styling
   - Handle errors gracefully with user-friendly messages
   - Include loading indicators
   - Make it mobile-responsive

3. DATA.JSON REQUIREMENTS:
   - Fetch the SEC API endpoint mentioned in the brief
   - Parse and save the response as valid JSON
   - Include all units/values from the SEC response
   - Structure: {{"company": "...", "cik": "...", "data": [...]}}

4. JAVASCRIPT FUNCTIONALITY:
   - Parse ?CIK= from URL query parameters
   - If ?CIK= provided, fetch new company data without page reload
   - Update page title, H1, and all content dynamically
   - Use Chart.js for visualization (load from CDN)
   - Sort data by date/filing
   - Handle API errors with retry logic

5. STYLING:
   - Modern, professional design
   - Color scheme: Blues and grays
   - Responsive layout (mobile, tablet, desktop)
   - Smooth animations and transitions
   - Accessible (ARIA labels, semantic HTML)

6. README.MD:
   - Project title and description
   - Company information from brief
   - How to use (including ?CIK= parameter)
   - Features list
   - Data source credits
   - License information

Generate COMPLETE, WORKING code. No placeholders. No TODO comments. Production-ready.

Output format - JSON with this structure:
{{
    "index.html": "COMPLETE HTML CODE HERE",
    "data.json": "COMPLETE JSON DATA HERE",
    "LICENSE": "MIT LICENSE TEXT",
    "README.md": "COMPLETE README",
    "uid.txt": "ATTACHMENT CONTENT IF PROVIDED"
}}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanations, just the JSON object."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert full-stack developer specializing in data visualization and SEC financial data applications. Generate complete, production-ready code with no placeholders."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=16000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean markdown code blocks if present
            TRIPLE_BACKTICK = chr(96) * 3
            if content.startswith(TRIPLE_BACKTICK):
                parts = content.split(TRIPLE_BACKTICK)
                if len(parts) > 1:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
            
            files = json.loads(content)
            
            # Handle attachments (uid.txt)
            if attachments:
                for attachment in attachments:
                    if attachment.get('name') == 'uid.txt':
                        data_url = attachment.get('url', '')
                        if 'base64,' in data_url:
                            base64_data = data_url.split('base64,')[1]
                            decoded = base64.b64decode(base64_data).decode('utf-8')
                            files['uid.txt'] = decoded
            
            print(f"Generated {len(files)} files")
            return files
            
        except Exception as e:
            print(f"Error generating SEC app: {e}")
            return self._generate_basic_sec_template(task_name, brief, attachments)
    
    def _generate_basic_sec_template(self, task_name: str, brief: str, attachments: list) -> dict:
        """Fallback basic SEC template if LLM fails"""
        
        # Extract CIK from brief
        cik_match = re.search(r'CIK(\d+)', brief)
        cik = cik_match.group(1) if cik_match else "0000018230"
        
        # Extract company name
        company_match = re.search(r'company: ([^,\n]+)', brief)
        company = company_match.group(1) if company_match else "Company"
        
        # Extract API URL
        url_match = re.search(r'https://data\.sec\.gov[^\s\)]+', brief)
        api_url = url_match.group(0) if url_match else f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/dei/EntityCommonStockSharesOutstanding.json"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{task_name} - {company}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .company-info {{
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #667eea;
            font-size: 1.2em;
        }}
        .error {{
            background: #fee;
            border: 2px solid #fcc;
            padding: 20px;
            border-radius: 10px;
            color: #c00;
            margin: 20px 0;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 id="title">{task_name}</h1>
        <div class="company-info" id="company-info">
            <strong id="company-name">{company}</strong> (CIK: <span id="cik-display">{cik}</span>)
        </div>
        
        <div class="loading" id="loading">Loading SEC data...</div>
        <div class="error" id="error" style="display:none;"></div>
        
        <div id="content" style="display:none;">
            <div class="stats" id="stats"></div>
            <div class="chart-container">
                <canvas id="dataChart"></canvas>
            </div>
            <table id="dataTable">
                <thead>
                    <tr>
                        <th>Filing Date</th>
                        <th>End Date</th>
                        <th>Value</th>
                        <th>Form</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        const API_URL = '{api_url}';
        let chartInstance = null;

        async function fetchData(cik = null) {{
            try {{
                const url = cik ? API_URL.replace(/CIK\\d+/, 'CIK' + cik) : API_URL;
                const response = await fetch(url, {{
                    headers: {{
                        'User-Agent': 'Educational Project',
                        'Accept': 'application/json'
                    }}
                }});
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return await response.json();
            }} catch (error) {{
                throw error;
            }}
        }}

        function displayData(data) {{
            const units = data.units?.shares || data.units?.USD || Object.values(data.units || {{}})[0] || [];
            if (!units || units.length === 0) throw new Error('No data available');

            units.sort((a, b) => new Date(b.filed) - new Date(a.filed));

            const latest = units[0];
            const avgValue = units.reduce((sum, item) => sum + (item.val || 0), 0) / units.length;

            document.getElementById('stats').innerHTML = '<div class="stat-card"><div class="stat-label">Latest Value</div><div class="stat-value">' + (latest.val || 0).toLocaleString() + '</div><div class="stat-label">' + latest.filed + '</div></div><div class="stat-card"><div class="stat-label">Average</div><div class="stat-value">' + avgValue.toLocaleString('en-US', {{maximumFractionDigits: 0}}) + '</div><div class="stat-label">Across all filings</div></div><div class="stat-card"><div class="stat-label">Total Filings</div><div class="stat-value">' + units.length + '</div><div class="stat-label">SEC reports</div></div>';

            const ctx = document.getElementById('dataChart').getContext('2d');
            if (chartInstance) chartInstance.destroy();

            chartInstance = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: units.map(item => item.end || item.filed).reverse(),
                    datasets: [{{
                        label: data.label || 'Value',
                        data: units.map(item => item.val).reverse(),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: true, position: 'top' }},
                        title: {{ display: true, text: data.label || 'Data Over Time' }}
                    }},
                    scales: {{ y: {{ beginAtZero: false }} }}
                }}
            }});

            document.getElementById('tableBody').innerHTML = units.slice(0, 50).map(item => '<tr><td>' + item.filed + '</td><td>' + (item.end || 'N/A') + '</td><td>' + (item.val || 0).toLocaleString() + '</td><td>' + item.form + '</td></tr>').join('');

            if (data.entityName) document.getElementById('company-name').textContent = data.entityName;
            if (data.cik) document.getElementById('cik-display').textContent = data.cik;
        }}

        async function init() {{
            try {{
                const urlParams = new URLSearchParams(window.location.search);
                const cikParam = urlParams.get('CIK');
                document.getElementById('loading').style.display = 'block';
                document.getElementById('error').style.display = 'none';
                document.getElementById('content').style.display = 'none';
                const data = await fetchData(cikParam);
                displayData(data);
                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
            }} catch (error) {{
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = 'Error loading data: ' + error.message;
            }}
        }}

        init();
    </script>
</body>
</html>"""

        data_json = {
            "company": company,
            "cik": cik,
            "api_url": api_url,
            "note": "Data will be fetched dynamically by the HTML page"
        }

        license_text = """MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

        readme = f"""# {task_name}

SEC Data Visualization for {company}

## Company Information
- **Name**: {company}
- **CIK**: {cik}
- **Data Source**: SEC XBRL API

## Features
- Real-time SEC data visualization
- Interactive Chart.js charts
- Responsive data tables
- Support for ?CIK= query parameter
- Modern, mobile-responsive design

## Usage
1. Open `index.html` in a web browser
2. View the default company data ({company})
3. To view another company, add `?CIK=XXXXXXXXXX` to the URL

Example: `index.html?CIK=0000789019` (for Microsoft)

## Data Source
{api_url}

## License
MIT License

## Technical Stack
- HTML5, CSS3, JavaScript (ES6+)
- Chart.js for visualizations
- SEC EDGAR API for data"""

        files = {
            "index.html": html,
            "data.json": json.dumps(data_json, indent=2),
            "LICENSE": license_text,
            "README.md": readme
        }

        if attachments:
            for attachment in attachments:
                if attachment.get('name') == 'uid.txt':
                    data_url = attachment.get('url', '')
                    if 'base64,' in data_url:
                        base64_data = data_url.split('base64,')[1]
                        decoded = base64.b64decode(base64_data).decode('utf-8')
                        files['uid.txt'] = decoded

        return files
    
    def _generate_generic_app(self, task_name: str, brief: str, checks: list, attachments: list) -> dict:
        """Generate generic application for unknown task types"""
        
        prompt = f"""Create a complete web application for:

TASK: {task_name}

REQUIREMENTS:
{brief}

CHECKS TO PASS:
{chr(10).join(f'- {check}' for check in checks)}

Generate a complete, working HTML/CSS/JS application that meets ALL requirements.
Include proper error handling, responsive design, and user-friendly interface.

Return JSON with files:
{{
    "index.html": "COMPLETE HTML CODE",
    "LICENSE": "MIT LICENSE",
    "README.md": "DOCUMENTATION"
}}

Make it production-ready with no placeholders."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert web developer. Create complete, working code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=8000
            )
            
            content = response.choices[0].message.content.strip()
            
            TRIPLE_BACKTICK = chr(96) * 3
            if content.startswith(TRIPLE_BACKTICK):
                parts = content.split(TRIPLE_BACKTICK)
                if len(parts) > 1:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
            
            files = json.loads(content)
            
            if attachments:
                for attachment in attachments:
                    name = attachment.get('name', '')
                    if name:
                        data_url = attachment.get('url', '')
                        if 'base64,' in data_url:
                            base64_data = data_url.split('base64,')[1]
                            decoded = base64.b64decode(base64_data).decode('utf-8')
                            files[name] = decoded
            
            return files
            
        except Exception as e:
            print(f"Error generating app: {e}")
            return self._basic_fallback(task_name, brief, attachments)
    
    def _basic_fallback(self, task_name: str, brief: str, attachments: list) -> dict:
        """Ultimate fallback template"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{task_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f0f0f0;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #333; }}
        .brief {{
            background: #f9f9f9;
            padding: 20px;
            border-left: 4px solid #007bff;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{task_name}</h1>
        <div class="brief">
            <h2>Project Brief:</h2>
            <pre>{brief}</pre>
        </div>
    </div>
</body>
</html>"""

        license_text = "MIT License\n\nCopyright (c) 2025\n\nPermission is hereby granted..."
        readme = f"""# {task_name}\n\n{brief}\n\n## License\nMIT"""
        
        files = {
            "index.html": html,
            "LICENSE": license_text,
            "README.md": readme
        }
        
        if attachments:
            for attachment in attachments:
                name = attachment.get('name', '')
                if name:
                    data_url = attachment.get('url', '')
                    if 'base64,' in data_url:
                        base64_data = data_url.split('base64,')[1]
                        decoded = base64.b64decode(base64_data).decode('utf-8')
                        files[name] = decoded
        
        return files

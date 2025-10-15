
Then visit `http://localhost:8000`

## Code Structure
- `index.html` - Main application file with embedded JavaScript
- `assets/` - Static assets and data files
- `LICENSE` - MIT License
- `README.md` - This file

## Implementation Details
The application uses:
- Bootstrap 5 for styling
- Vanilla JavaScript for functionality
- CDN-hosted libraries (marked, highlight.js, tesseract.js as needed)
- GitHub Pages for hosting

## License
MIT License - see LICENSE file for details
"""
    
    def _get_mit_license(self) -> str:
        """Generate MIT license"""
        from datetime import datetime
        year = datetime.now().year
        username = os.getenv("GITHUB_USERNAME", "Student")
        
        return f"""MIT License

Copyright (c) {year} {username}

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
SOFTWARE.
"""

import requests
import json
import base64

# Test configuration
API_URL = "http://localhost:8000/api-endpoint"
STUDENT_EMAIL = "23f2003741@ds.study.iitm.ac.in"
SECRET = "Bhargava123"

# Sample captcha solver request
captcha_request = {
    "email": STUDENT_EMAIL,
    "secret": SECRET,
    "task": "captcha-solver-test1",
    "round": 1,
    "nonce": "test-nonce-001",
    "brief": "Create a captcha solver that handles ?url=https://.../image.png. Default to attached sample.",
    "checks": [
        "Repo has MIT license",
        "README.md is professional",
        "Page displays captcha URL passed at ?url=...",
        "Page displays solved captcha text within 15 seconds"
    ],
    "evaluation_url": "https://httpbin.org/post",
    "attachments": [
        {
            "name": "sample.png",
            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
    ]
}

# Sample sum of sales request
sales_request = {
    "email": STUDENT_EMAIL,
    "secret": SECRET,
    "task": "sum-of-sales-test1",
    "round": 1,
    "nonce": "test-nonce-002",
    "brief": "Publish a single-page site that fetches data.csv, sums its sales column, sets title to 'Sales Summary 2025', displays total inside #total-sales, and loads Bootstrap 5.",
    "checks": [
        "Repo has MIT license",
        "Page title is correct",
        "Bootstrap is loaded",
        "Total sales is displayed correctly"
    ],
    "evaluation_url": "https://httpbin.org/post",
    "attachments": [
        {
            "name": "data.csv",
            "url": f"data:text/csv;base64,{base64.b64encode(b'product,sales,region\\nProduct A,100.50,North\\nProduct B,250.75,South\\nProduct C,150.25,East').decode()}"
        }
    ]
}

def test_endpoint(request_data, test_name):
    """Test the API endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            API_URL,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print(f"✅ Test passed: {test_name}")
        else:
            print(f"❌ Test failed: {test_name}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Starting endpoint tests...")
    print("Make sure the server is running on http://localhost:8000")
    
    # Test health endpoint
    try:
        health = requests.get("http://localhost:8000/health")
        print(f"\nHealth Check: {health.json()}")
    except:
        print("\n❌ Server is not running! Start it with: python app.py")
        exit(1)
    
    # Run tests
    test_endpoint(captcha_request, "Captcha Solver")
    test_endpoint(sales_request, "Sum of Sales")
    
    print("\n" + "="*60)
    print("Tests complete! Check the server logs for deployment progress.")
    print("Repos will be created and Pages will be enabled automatically.")
    print("="*60)

import requests

session = requests.Session()
login_url = "http://localhost:8000/login/"
dashboard_url = "http://localhost:8000/administration/dashboard/"
personnels_url = "http://localhost:8000/administration/personnel/"
types_membres_url = "http://localhost:8000/administration/types-membres/"

# 1. Login
print("Testing Login...")
# We need to realize that the login view might use 'login' and 'password' as fields
# AND it might be redirecting.
response = session.get(login_url)
csrf_token = session.cookies.get('csrftoken')
login_data = {
    "login": "admin_test",
    "password": "admin123",
    "csrfmiddlewaretoken": csrf_token
}

response = session.post(login_url, data=login_data, headers={'Referer': login_url}, allow_redirects=True)
print(f"Login Response URL: {response.url}")
print(f"Login Status: {response.status_code}")

# 2. Test Endpoints
endpoints = [
    ("Dashboard", dashboard_url),
    ("Personnels", personnels_url),
    ("Types Membres", types_membres_url)
]

for name, url in endpoints:
    print(f"Testing {name} ({url})...")
    res = session.get(url)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print(f"Content contains 'admin_test': {'admin_test' in res.text}")
        # Look for table or specific data indicative of MSSQL results
        if "<table" in res.text or "<tbody>" in res.text:
            print(f"SUCCESS: Data table found on {name}")
        else:
            print(f"WARNING: No data table found on {name}")
            # print(res.text[:500]) # Debug info
    else:
        print(f"FAILURE: Could not load {name}")

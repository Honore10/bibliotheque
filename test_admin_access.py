import requests
from bs4 import BeautifulSoup
import sys

BASE_URL = 'http://127.0.0.1:8000'
LOGIN_URL = f'{BASE_URL}/login/'
DASHBOARD_URL = f'{BASE_URL}/administration/dashboard/'
PERSONNEL_URL = f'{BASE_URL}/administration/personnel/'
TYPES_MEMBRES_URL = f'{BASE_URL}/administration/types-membres/'

session = requests.Session()

try:
    # 1. Load login page to get CSRF token
    response = session.get(LOGIN_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    print(f'CSRF Token obtained: {csrf_token}')

    # 2. Submit login
    login_data = {
        'username': 'admin_test',
        'password': 'admin123',
        'csrfmiddlewaretoken': csrf_token
    }
    response = session.post(LOGIN_URL, data=login_data, headers={'Referer': LOGIN_URL})
    print(f'Login Status Code: {response.status_code}')
    if 'logout' not in response.text.lower() and 'dashboard' not in response.text.lower():
        print('Login might have failed. Checking content...')

    # 3. Test admin pages
    pages = [DASHBOARD_URL, PERSONNEL_URL, TYPES_MEMBRES_URL]
    for url in pages:
        print(f'\n--- Testing Page: {url} ---')
        response = session.get(url)
        print(f'Status Code: {response.status_code}')
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for data snippets
        if 'dashboard' in url:
            # Look for stats or counts
            stats = soup.find_all(['div', 'span', 'p', 'h3'], class_=lambda x: x and ('card' in x or 'stat' in x or 'count' in x))
            for stat in stats[:5]:  # Show first 5 matches
                print(f'Data Snippet: {stat.get_text(strip=True)}')
        elif 'personnel' in url or 'types-membres' in url:
            # Look for table rows or lists
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows[1:4]: # First 3 data rows
                    print(f'Data Row: {row.get_text(strip=True, separator="|")}')
            else:
                print('No table found, searching for content...')
                content = soup.find_all(['li', 'div'], class_=lambda x: x and ('item' in x or 'list' in x))
                for item in content[:5]:
                    print(f'Content Snippet: {item.get_text(strip=True)}')

except Exception as e:
    print(f'Error: {e}')


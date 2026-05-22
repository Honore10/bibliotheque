import requests
import re

base_url = 'http://localhost:8000'
login_url = f'{base_url}/login/'
dashboard_url = f'{base_url}/staff/dashboard/'
books_url = f'{base_url}/staff/livres/'
categories_url = f'{base_url}/staff/categories/'

credentials = {
    'identifiant': 'staff_test',
    'password': 'staff123'
}

def clean_html(text):
    return re.sub(r'\s+', ' ', text).strip()

def test_endpoints():
    with requests.Session() as session:
        # 1. Login
        session.get(login_url)
        csrf_token = session.cookies.get('csrftoken')
        
        login_data = {
            'identifiant': credentials['identifiant'],
            'password': credentials['password'],
            'csrfmiddlewaretoken': csrf_token
        }
        
        print(f'Attempting login to {login_url}...')
        response = session.post(login_url, data=login_data, headers={'Referer': login_url}, allow_redirects=True)
        print(f'Login Status: {response.status_code}, Final URL: {response.url}')
        
        # 2. Staff Dashboard
        print(f'\nFetching Dashboard: {dashboard_url}')
        resp_dashboard = session.get(dashboard_url)
        print(f'Status: {resp_dashboard.status_code}')
        print(f'Snippet: {clean_html(resp_dashboard.text)[:300]}...')
        if 'Dashboard Staff' in resp_dashboard.text:
            print("Check: 'Dashboard Staff' found in content.")

        # 3. Staff Books
        print(f'\nFetching Books: {books_url}')
        resp_books = session.get(books_url)
        print(f'Status: {resp_books.status_code}')
        # Look for table data or count
        print(f'Snippet: {clean_html(resp_books.text)[:300]}...')
        if 'Gestion Livres' in resp_books.text:
            print("Check: 'Gestion Livres' found in content.")

        # 4. Staff Categories
        print(f'\nFetching Categories: {categories_url}')
        resp_categories = session.get(categories_url)
        print(f'Status: {resp_categories.status_code}')
        print(f'Snippet: {clean_html(resp_categories.text)[:300]}...')
        if 'Gestion Catégories' in resp_categories.text:
            print("Check: 'Gestion Catégories' found in content.")

if __name__ == '__main__':
    test_endpoints()

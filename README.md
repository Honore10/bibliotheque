# Bibliothèque - Frontend Django

Scaffold minimal pour une application Django qui consomme l'API distante:
https://bibliotheque-emprunts.onrender.com

Prérequis
- Python 3.10+
- pip
- (optionnel) node si vous souhaitez configurer Tailwind localement

Installation rapide
1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. cp .env.example .env (adapter API_BASE_URL / SECRET_KEY)
5. python manage.py migrate
6. python manage.py runserver
7. Ouvrir http://127.0.0.1:8000/

Notes
- Le JWT est stocké dans la session Django (request.session["jwt"]) pour meilleure sécurité.
- Le client API central est `core.api_client.ApiClient`.
- Middleware `core.middleware.RemoteAuthMiddleware` hydrate `request.remote_user`.
- Tailwind est utilisé via CDN pour accélérer le prototypage. Pour production, configurez Tailwind avec npm et build.
- Aucun modèle local n'est requis pour stocker la donnée métier. Django est utilisé comme frontend consommant l'API.
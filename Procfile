web: gunicorn run-heroku:app
init: python manage.py db init
upgrade: python manage.py db upgrade
celery: celery -A application.celery worker -B --loglevel=info
worker: python coffeebot.py

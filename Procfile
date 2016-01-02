web: gunicorn run-heroku:app
init: python create_db.py
celery: celery -A application.celery worker -B --loglevel=info
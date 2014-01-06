
DEBUG = True
CSFR_ENABLED = True
SECRET_KEY = "HyP0oHYnYeqv47uXohfvOkiv"
#SQLALCHEMY_DATABASE_URI = "mysql+mysqldb://flask:@localhost/coffeerun"
if os.environ.get('DATABASE_URL') is None:
    SQLALCHEMY_DATABASE_URI = "mysql+mysqldb://flask:@localhost/coffeerun"
else:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

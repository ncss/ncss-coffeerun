import logging

from application import app


logging.basicConfig(level=logging.DEBUG)
app.run(port=8000, host='0.0.0.0')

"""Insta485 package initializer."""
import flask
from flask_mail import Mail

# app is a single object used by all the code modules in this package
app = flask.Flask(__name__)  # pylint: disable=invalid-name


# Read settings from config module (insta485/config.py)
app.config.from_object("insta485.config")
mail = Mail(app)

# Overlay settings read from a Python file whose path is set in the environment
# variable INSTA485_SETTINGS. Setting this environment variable is optional.
# Docs: http://flask.pocoo.org/docs/latest/config/
#
# EXAMPLE:
# $ export INSTA485_SETTINGS=secret_key_config.py
app.config.from_envvar("INSTA485_SETTINGS", silent=True)


import insta485.views  # noqa: E402  pylint: disable=wrong-import-position
import insta485.model  # noqa: E402  pylint: disable=wrong-import-position
import insta485.api    # noqa: E402  pylint: disable=wrong-import-position

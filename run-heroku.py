# NOTE: We explicitly import this first, to ensure that it integrates correctly.
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    "https://a4ba88dce1234b4ea13f5c3111a67efa@sentry.io/1366725",
    integrations=[FlaskIntegration()])

from application import app  # noqa: F401,I100

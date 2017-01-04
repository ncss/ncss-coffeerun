import logging
import json
import requests

from application import app, db
from application.models import Run, User, Coffee, SlackTeamAccessToken
from application.events import EventType

logger = logging.getLogger('slack-integration')

API_URL = 'https://slack.com/api/chat.postMessage'
DEFAULT_PARAMS = {
    'username': 'coffeebot',
    'as_user': False,
    'icon_emoji': ':coffee:'
}


def get_params():
  params = dict(DEFAULT_PARAMS)
  token = SlackTeamAccessToken.query.get(app.config['SLACK_TEAM_ID'])
  params['token'] = token.access_token
  return params


def notify_channel(message):
  params = get_params()
  params['text'] = message
  params['channel'] = '#coffee'
  resp = requests.get(API_URL, params=params)
  content = json.loads(resp.content)
  logger.info('Posted to channel: response:%s, content:%s', resp.status_code, content)


def notify_user(message, user):
  params = get_params()
  params['text'] = message
  params['channel'] = '@' + user.name
  resp = requests.get(API_URL, params=params)
  content = json.loads(resp.content)
  logger.info('Posted to user %s: response:%s, content:%s', user.id, resp.status_code, content)


def process_event(event):
  '''
  Events come as dictionaries in the form {type: TYPE_ENUM, <additional type-specific info>}
  '''
  event_type = event['type']

  if event_type == EventType.RUN_CREATED:
    run = Run.query.get(event['run_id'])
    msg = '<!channel> Want a coffee? {} is making a run at {} (pickup: {}).'.format(run.fetcher.get_slack_mention(), run.prettyprint(), run.pickup)
    notify_channel(msg)

  elif event_type == EventType.RUN_CLOSED:
    run = Run.query.get(event['run_id'])
    msg = 'No more coffees can be added to {}\'s run. (pickup will be at: {}).'.format(run.fetcher.get_slack_mention(), run.pickup)
    notify_channel(msg)

  elif event_type == EventType.RUN_DELIVERED:
    run = Run.query.get(event['run_id'])
    for coffee in Coffee.query.filter_by(run=run):
      msg = 'Your {} has arrived at {} (thanks to {}!).'.format(coffee.pretty_print(), run.pickup, run.fetcher.name)
      notify_user(msg, coffee.addict)

  elif event_type == EventType.COFFEE_ADDED:
    run = Run.query.get(event['run_id'])
    coffee = Coffee.query.get(event['coffee_id'])
    msg = '{} added a {} to your run.'.format(coffee.addict.name, coffee.pretty_print())

    notify_user(msg, run.fetcher)

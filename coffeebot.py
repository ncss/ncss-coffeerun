# vim: set et nosi ai ts=2 sts=2 sw=2:
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals

import logging
import pprint
import random
import re
import time

from slackclient import SlackClient

from application import app, db
from application.models import Run, User, Coffee, Event, sydney_timezone_now

from flask.ext import babel

import coffeespecs
import utils


TOKEN = None
USER_ID = None
TEAM_ID = None

MENTION_RE = re.compile(r'<@([A-Z0-9]+)\|?[^>]*>:?')
EMOJI_RE = re.compile(r':[a-z]+:')

DISPATCH = {}
ORDERS_DISPATCH = {}
TRIGGERS = {}


def list_runs(slackclient, user, channel, match):
  """Handle the 'open runs' command.

  This command only displays the open runs. If there are multiple runs
  currently open, it orders them by time (on the assumption that you want
  things in the first available run).

  Args:
    slackclient: the slackclient.SlackClient object for the current
      connection to Slack.
    user: the slackclient.User object for the user who send the
      message to us.
    channel: the slackclient.Channel object for the channel the
      message was received on.
    match: the object returned by re.match (an _sre.SRE_Match object).
  """
  now = sydney_timezone_now()
  q = Run.query.filter_by(is_open=True).order_by('time').all()
  if not q:
    channel.send_message('No open runs')
  for run in q:
    person = User.query.filter_by(id=run.person).first()
    time_to_run = run.time - now
    channel.send_message(
        'Run {}: {} is going to {} in {} (at {})'.format(
          run.id, person.name, run.cafe.name,
          babel.format_timedelta(time_to_run), run.time))


def order_coffee(slackclient, user, channel, match):
  """Handle adding coffee to existing orders.

  Args:
    slackclient: the slackclient.SlackClient object for the current
      connection to Slack.
    user: the slackclient.User object for the user who send the
      message to us.
    channel: the slackclient.Channel object for the channel the
      message was received on.
    match: the object returned by re.match (an _sre.SRE_Match object).
  """
  logger = logging.getLogger('order_coffee')
  logger.info('Matches: %s', pprint.pformat(match.groupdict()))
  runid = match.groupdict().get('runid', None)
  run = None
  if runid and runid.isdigit():
    run = Run.query.filter_by(id=int(runid)).first()
  if not run:
    # Pick a run
    runs = Run.query.filter_by(is_open=True).order_by('time').all()
    if len(runs) > 1:
      channel.send_message(
          'More than one open run, please specify by adding run=<id> on the end.')
      list_runs(slackclient, user, channel, match=None)
      return
    if len(runs) == 0:
      channel.send_message('No open runs')
      return
    run = runs[0]

  # Create the coffee
  coffee = Coffee(match.group(1), 0, run.id)

  # Find the user that requested this
  dbuser = utils.get_or_create_user(user.id, TEAM_ID, user.name)
  logger.info('User: %s', dbuser)

  # Put it all together
  coffee.person = dbuser.id
  db.session.add(coffee)
  db.session.commit()

  # Write the event
  event = Event(coffee.person, "created", "coffee", coffee.id)
  event.time = sydney_timezone_now()
  db.session.add(event)
  db.session.commit()
  logger.info('Parsed coffee: %s', coffee)

  runuser = User.query.filter_by(id=run.person).first()

  channel.send_message(
      'That\'s a {} for {} (added to <@{}>\'s run.)'.format(
        coffee.pretty_print(),
        mention(user),
        runuser.slack_user_id))


def set_up_orders():
  ORDERS_DISPATCH[re.compile('(?:(?:open|list) )?runs')] = list_runs
  ORDERS_DISPATCH[re.compile('order(?: an?)? ([^\=]+)(?: run=(?P<runid>[0-9]+))?')] = order_coffee
  ORDERS_DISPATCH[re.compile('([^\=]+) (?:plz|please)(?: run=(?P<runid>[0-9]+))?')] = order_coffee


def load_triggers(filename):
  """Parse the sass file, loading them into the TRIGGERS global.
  """
  trigger = None
  for line in open(filename):
    if not line.strip():
      continue
    if line.startswith('@@@ '):
      trigger = re.compile(line[4:].strip())
      if trigger not in TRIGGERS:
        TRIGGERS[trigger] = []
    elif trigger:
      TRIGGERS[trigger].append(line.strip())


def trigger_check(slackclient, user, channel, text):
  """Check if we need to sass the user.

  Args:
    slackclient: the slackclient.SlackClient object for the current
      connection to Slack.
    user: the slackclient.User object for the user who send the
      message to us.
    channel: the slackclient.Channel object for the channel the
      message was received on.
    match: the object returned by re.match (an _sre.SRE_Match object).
  """
  text = text.lower()
  for trigger in TRIGGERS:
    if trigger.match(text):
      msg = random.choice(TRIGGERS[trigger])
      msg = mention(user) + ': ' + msg
      channel.send_message(msg)
      return True
  else:
    # No triggers matched. Inform our caller so they can decide what to do.
    return False


def mention(user):
  """Generate a mention for the given user.

  Args:
    user: a slackclient.User object for the user to mention.
  """
  return '<@{}|{}>'.format(user.id, user.name)


def clean_text(text):
  # Remove @mentions and emoji
  text = MENTION_RE.sub('', text)
  text = EMOJI_RE.sub('', text)
  text = text.lower()
  return text.strip()


def handle_mention_message(slackclient, user, channel, text):
  """We were mentioned in a message, dispatch it to the method.

  Args:
    slackclient: the slackclient.SlackClient object for the current
      connection to Slack.
    user: the slackclient.User object for the user who send the
      message to us.
    channel: the slackclient.Channel object for the channel the
      message was received on.
    text: the raw text that was sent to us.
  """
  clean = clean_text(text)

  message_processed = False
  for order_re in ORDERS_DISPATCH:
    match = order_re.match(clean)
    if match:
      ORDERS_DISPATCH[order_re](slackclient, user, channel, match)
      message_processed = True
      break

  if trigger_check(slackclient, user, channel, clean):
    message_processed = True

  if not message_processed:
    # We were mentioned, but we don't know what to do... Say
    # something back to them.
    channel.send_message('I am sorry {}, I can\'t do that.'.format(
      mention(user)))


def handle_message(slackclient, event):
  logger = logging.getLogger('handle_message')
  logger.debug('message event: %s', event)
  channel = slackclient.server.channels.find(event['channel'])

  # If the user edits their message, we treat it as if it were a new
  # message from that person.
  if 'subtype' in event and event['subtype'] == 'message_changed':
    event = event['message']
  user = slackclient.server.users.find(event['user'])
  text = event['text']

  mentions = MENTION_RE.findall(text)
  logger.info('Mentions: %s', mentions)

  # Behaviours:
  if USER_ID in mentions:
    handle_mention_message(slackclient, user, channel, text)
  elif ':coffee:' in text:
    msg = 'Mmmm... :coffee:' + ':coffee:' * random.randint(0, 7)
    channel.send_message(msg)


def register_handlers():
  DISPATCH['message'] = [handle_message]


def main():
  logger = logging.getLogger('main')

  load_triggers('sass.txt')
  set_up_orders()
  register_handlers()
  client = SlackClient(TOKEN)
  res = client.rtm_connect()
  logger.debug('Connection result: %r', res)
  if not res:
    logger.error('Connection Failed.')
    return

  logger.info('Users: %s', client.server.users)
  logger.info('Channels: %s', client.server.channels)
  while True:
    for event in client.rtm_read():
      logger.debug('Event: %s', event)
      if 'type' in event:
        # Call all handlers for the given event type.
        for handler in DISPATCH.get(event['type'], []):
          handler(client, event)
    time.sleep(0.1)


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)

  TOKEN = app.config['SLACK_API_TOKEN']
  USER_ID = app.config['SLACK_BOT_USER_ID']
  TEAM_ID = app.config['SLACK_TEAM_ID']
  if not TOKEN or not USER_ID:
    logging.error('Missing slack token or slack user id')

  # FIXME: This is a hack... But I can't think of anything better.
  # Add a test request context so that babel will work.
  app.test_request_context().push()

  main()

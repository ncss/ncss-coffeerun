# vim: set et nosi ai ts=2 sts=2 sw=2:
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals
import re
import time
import random

from slackclient import SlackClient

from application import app, db
from application.models import Run, User, Coffee, Event, sydney_timezone_now

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
  q = Run.query.all()
  if not q:
    slackclient.rtm_send_message(channel.id, 'No open runs')
  for run in q:
    person = User.query.filter_by(id=run.person).first()
    slackclient.rtm_send_message(channel.id, 'Run {}: {} is going to {} at {}'.format(run.id, person.name, run.cafe.name, run.time))


def order_coffee(slackclient, user, channel, match):
  print(match.groupdict())
  runid = match.groupdict().get('runid', None)
  run = None
  if runid and runid.isdigit():
    run = Run.query.filter_by(id=int(runid)).first()
  if not run:
    # Pick a run
    runs = Run.query.filter_by(is_open=True).order_by('time').all()
    if len(runs) > 1:
      slackclient.rtm_send_message(channel.id, 'More than one open run, please specify by adding run=<id> on the end.')
      list_runs(slackclient, user, channel, None)
      return
    if len(runs) == 0:
      slackclient.rtm_send_message(channel.id, 'No open runs')
      return
    run = runs[0]

  # Create the coffee
  coffee = Coffee(match.group(1), 0, run.id)

  # Find the user that requested this
  dbuser = utils.get_or_create_user(user.id, TEAM_ID, user.name)
  print(dbuser)

  # Put it all together
  coffee.person = dbuser.id
  db.session.add(coffee)
  db.session.commit()

  # Write the event
  event = Event(coffee.person, "created", "coffee", coffee.id)
  event.time = sydney_timezone_now()
  db.session.add(event)
  db.session.commit()
  print(coffee)

  runuser = User.query.filter_by(id=run.person).first()

  slackclient.rtm_send_message(channel.id, 'That\'s a {} for {} (added to <@{}>\'s run.)'.format(coffee.pretty_print(), mention(user), runuser.slack_user_id))


def set_up_orders():
  ORDERS_DISPATCH[re.compile('(open|list)? ?runs')] = list_runs
  ORDERS_DISPATCH[re.compile('order(?: an?)? ([^\=]+)(?: run=(?P<runid>[0-9]+))?')] = order_coffee
  ORDERS_DISPATCH[re.compile('([^\=]+) (?:plz|please)(?: run=(?P<runid>[0-9]+))?')] = order_coffee


def load_triggers(filename):
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
  text = text.lower()
  for trigger in TRIGGERS:
    if trigger.match(text):
      msg = random.choice(TRIGGERS[trigger])
      msg = mention(user) + ': ' + msg
      slackclient.rtm_send_message(channel.id, msg)
      return


def mention(user):
  return '<@{}|{}>'.format(user.id, user.name)


def clean_text(text):
  # Remove @mentions and emoji
  text = MENTION_RE.sub('', text)
  text = EMOJI_RE.sub('', text)
  text = text.lower()
  return text.strip()


def handle_mention_message(slackclient, user, channel, text):
  clean = clean_text(text)

  for order_re in ORDERS_DISPATCH:
    match = order_re.match(clean)
    if match:
      ORDERS_DISPATCH[order_re](slackclient, user, channel, match)
      break

  trigger_check(slackclient, user, channel, clean)


def handle_message(slackclient, event):
  print('message event')
  channel = slackclient.server.channels.find(event['channel'])
  if 'subtype' in event and event['subtype'] == 'message_changed':
    event = event['message']
  user = slackclient.server.users.find(event['user'])
  text = event['text']

  mentions = MENTION_RE.findall(text)
  print(mentions)

  # Behaviours:
  if USER_ID in mentions:
    handle_mention_message(slackclient, user, channel, text)
  elif ':coffee:' in text:
    msg = 'Mmmm... :coffee:' + ':coffee:' * random.randint(0, 7)
    slackclient.rtm_send_message(channel.id, msg)


def register_handlers():
  DISPATCH['message'] = [handle_message]


def main():
  load_triggers('sass.txt')
  set_up_orders()
  register_handlers()
  client = SlackClient(TOKEN)
  res = client.rtm_connect()
  print(res)
  if res:
    print(client.server.users)
    print(client.server.channels)
    while True:
      for event in client.rtm_read():
        print(event)
        if 'type' in event:
          event_type = event['type']
          print(event_type)
          if event_type in DISPATCH:
            for handler in DISPATCH[event_type]:
              handler(client, event)
      time.sleep(0.1)
  else:
    print('Connection Failed.')


if __name__ == '__main__':
  TOKEN = app.config['SLACK_API_TOKEN']
  USER_ID = app.config['SLACK_BOT_USER_ID']
  TEAM_ID = app.config['SLACK_TEAM_ID']
  if not TOKEN or not USER_ID:
    print('Missing slack token or slack user id')
  main()

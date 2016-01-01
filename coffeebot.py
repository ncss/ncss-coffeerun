# vim: set et nosi ai ts=2 sts=2 sw=2:
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals
import re
import time
import random
import sys

from slackclient import SlackClient

from application.models import Run, User

from coffeespecs import Coffee


TOKEN = 'xoxb-16617666518-3Lh8g3yORvyyu5yzkreeAki7'  # found at https://api.slack.com/web#authentication
DEV_TOKEN = 'xoxb-17128429879-cOJ20g0lhgcwaftlt6Z6l2BI'
USER_ID = 'U0GJ5KLF8'
DEV_USER_ID = 'U0H3SCMRV'

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
    slackclient.rtm_send_message(channel.id, '{} is going to {} at {}'.format(person.name, run.cafe.name, run.time))


def set_up_orders():
  ORDERS_DISPATCH[re.compile('(open|list)? ?runs')] = list_runs


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
  return text.strip()


def handle_mention_message(slackclient, user, channel, text):
  clean = clean_text(text)
  msg = None

  for order_re in ORDERS_DISPATCH:
    match = order_re.match(clean)
    if match:
      ORDERS_DISPATCH[order_re](slackclient, user, channel, match)
      break

  c = Coffee(clean)
  if c.validate():
    msg = 'Ok, that\'s a {} for {}'.format(c, mention(user))

  if msg:
    slackclient.rtm_send_message(channel.id, msg)
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
  print(TRIGGERS)
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
  dev = len(sys.argv) > 1 and sys.argv[1] == 'dev'
  if dev:
    TOKEN = DEV_TOKEN
    USER_ID = DEV_USER_ID
  main()

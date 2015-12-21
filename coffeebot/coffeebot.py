# vim: set et nosi ai ts=2 sts=2 sw=2:
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals
import re
import time
import random

from slackclient import SlackClient

from coffeespecs import Coffee


TOKEN = "xoxb-16617666518-3Lh8g3yORvyyu5yzkreeAki7"  # found at https://api.slack.com/web#authentication
USER_ID = 'U0GJ5KLF8'

MENTION_RE = re.compile(r'<@([A-Z0-9]+)\|?[^>]*>')
EMOJI_RE = re.compile(r':[a-z]+:')

DISPATCH = {}

OPEN_QUESTIONS = {}


def mention(user):
  return '<@{}|{}>'.format(user.id, user.name)


def clean_text(text):
  # Remove @mentions and emoji
  text = MENTION_RE.sub('', text)
  text = EMOJI_RE.sub('', text)
  return text


def handle_mention_message(slackclient, user, channel, text):
  msg = 'Hi {}, would you like coffee?'.format(mention(user), channel.name)

  clean = clean_text(text)
  c = Coffee(clean)
  if c.validate():
    msg = 'Ok, that\'s a {} for {}'.format(c, mention(user))

  slackclient.rtm_send_message(channel.id, msg)


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
  main()

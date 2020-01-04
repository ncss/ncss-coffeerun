import collections
import json
import logging
import typing

from application.events import EventType
from application.models import Coffee, Run, SlackTeamAccessToken, User

import requests


logger = logging.getLogger('slack-integration')

API_URL = 'https://slack.com/api/chat.postMessage'
DEFAULT_PARAMS = {
    'as_user': False,
    'icon_emoji': ':coffee:',
    'parse': 'none',
    'username': 'coffeebot',
}


class SlackNotificationException(Exception):
    pass


class SlackDetails(collections.namedtuple('SlackDetails', ['token', 'team_id', 'notification_channel'])):
    pass


class SlackNotifier:
    def __init__(self):
        self._workspaces = {}
        for workspace in SlackTeamAccessToken.query.filter(
                SlackTeamAccessToken.wants_slack_notifications == True,  # noqa: E711. `== True` is needed for SQLAlchemy operator binding magic. `is True` does not work.
                SlackTeamAccessToken.access_token != None,  # noqa: E711. `!= None` is needed for SQLAlchemy operator binding magic. `is not None` does not work.
        ):
            slack_channel = workspace.coffee_slack_channel or '#coffee'
            details = SlackDetails(
                    workspace.access_token, workspace.team_id, slack_channel)
            self._workspaces[details.team_id] = details

    def get_params_for_workspace(self, team_id: typing.Text):
        params = dict(DEFAULT_PARAMS)
        details = self._workspaces.get(team_id)
        if not details or not details.token:
            raise SlackNotificationException(
                    'Access token for team {} is not configured.'.format(team_id))
        params['token'] = details.token
        params['channel'] = details.notification_channel
        return params

    def notify_channel(self, message: typing.Text, team_id: typing.Text):
        params = self.get_params_for_workspace(team_id)
        params['text'] = message.encode('utf-8')
        resp = requests.get(API_URL, params=params)
        content = json.loads(resp.content.decode('utf-8'))
        logger.info('Posted to channel: response:%s, content:%s', resp.status_code, content)

    def notify_channels(self, message: typing.Text):
        for team_id in self._workspaces:
            self.notify_channel(message, team_id)

    def notify_single_user(self, message: typing.Text, user: User):
        assert user.slack_team_id is not None
        params = self.get_params_for_workspace(user.slack_team_id)
        params['text'] = message.encode('utf-8')
        params['channel'] = user.slack_user_id
        resp = requests.get(API_URL, params=params)
        content = json.loads(resp.content.decode('utf-8'))
        logger.info('Posted to user %s: response:%s, content:%s', user.id, resp.status_code, content)


def process_event(event):
    '''
    Events come as dictionaries in the form {type: TYPE_ENUM, <additional type-specific info>}
    '''
    notifier = SlackNotifier()

    event_type = event['type']

    if event_type == EventType.RUN_CREATED:
        run = Run.query.get(event['run_id'])
        msg = u'<!channel> Want a coffee? {} is making a run at {} (pickup: {}).'.format(run.fetcher.get_slack_mention(), run.prettyprint(), run.pickup)
        notifier.notify_channels(msg)

    elif event_type == EventType.RUN_CLOSED:
        run = Run.query.get(event['run_id'])
        msg = u'No more coffees can be added to {}\'s run. (pickup will be at: {}).'.format(run.fetcher.get_slack_mention(), run.pickup)
        notifier.notify_channels(msg)

    elif event_type == EventType.RUN_DELIVERED:
        run = Run.query.get(event['run_id'])
        for coffee in Coffee.query.filter_by(run=run):
            try:
                msg = u'Your {} has arrived at {} (thanks to {}!).'.format(coffee.pretty_print(), run.pickup, run.fetcher.name)
            except Exception:
                pass
            else:
                notifier.notify_single_user(msg, coffee.addict)

    elif event_type == EventType.COFFEE_ADDED:
        run = Run.query.get(event['run_id'])
        coffee = Coffee.query.get(event['coffee_id'])
        msg = u'{} added a {} to your run.'.format(coffee.addict.name, coffee.pretty_print())

        notifier.notify_single_user(msg, run.fetcher)

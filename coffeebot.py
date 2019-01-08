import logging
import pprint
import random
import re
import threading
import time

from application import app, db, events, models
from application.models import Coffee, Event, Run, User, sydney_timezone_now

import coffeespecs

import flask_babel

from slackclient import SlackClient

import utils


class WrappedSlackBot:
    TOKEN = None
    USER_ID = None
    TEAM_ID = None

    MENTION_RE = re.compile(r'<@([A-Z0-9]+)\|?[^>]*>:?')
    EMOJI_RE = re.compile(r':[a-z]+:')

    def __init__(self, token, user_id, team_id):
        self.TOKEN = token
        self.USER_ID = user_id
        self.TEAM_ID = team_id

        self.DISPATCH = {}
        self.ORDERS_DISPATCH = {}
        self.TRIGGERS = {}

        # Configure the dispatcher regular expressions
        self.ORDERS_DISPATCH[re.compile(r'(?:(?:open|list) )?runs')] = self.list_runs
        self.ORDERS_DISPATCH[re.compile(r'order(?: an?)? ([^\=]+)(?: run=(?P<runid>[0-9]+))?')] = self.order_coffee
        self.ORDERS_DISPATCH[re.compile(r'([^\=]+) (?:plz|pls|please|plox)(?: run=(?P<runid>[0-9]+))?')] = self.order_coffee

        self.DISPATCH['message'] = [self.handle_message]
        self.load_triggers('sass.txt')

        self.client = SlackClient(self.TOKEN)

    def list_runs(self, slackclient, user, channel, match):
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
                        flask_babel.format_timedelta(time_to_run), run.time))

    def order_coffee(self, slackclient, user, channel, match):
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
                self.list_runs(slackclient, user, channel, match=None)
                return
            if len(runs) == 0:
                channel.send_message('No open runs')
                return
            run = runs[0]

        # Create the coffee
        c = coffeespecs.Coffee(match.group(1))
        validation_errors = list(c.validation_errors())
        if validation_errors:
            channel.send_message(
                'That coffee is not valid missing the following specs: {}. Got: {}'.format(
                    ', '.join(spec.name for spec in validation_errors),
                    c,
                )
            )
            return
        coffee = Coffee(c, 0, run.id)

        # Find the user that requested this
        dbuser = utils.get_or_create_user(user.id, self.TEAM_ID, user.name)
        logger.info('User: %s', dbuser)

        # Put it all together
        coffee.person = dbuser.id
        db.session.add(coffee)
        db.session.commit()
        events.coffee_added(run.id, coffee.id)

        # Write the event
        event = Event(coffee.person, "created", "coffee", coffee.id)
        event.time = sydney_timezone_now()
        db.session.add(event)
        db.session.commit()
        logger.info('Parsed coffee: %s', coffee)

        runuser = User.query.filter_by(id=run.person).first()
        if runuser.slack_user_id:
            mention_runner = '<@{}>'.format(runuser.slack_user_id)
        else:
            mention_runner = runuser.name
        channel.send_message(
                'That\'s a {} for {} (added to {}\'s run.)'.format(
                    coffee.pretty_print(),
                    self.mention(user),
                    mention_runner))

    def load_triggers(self, filename):
        """Parse the sass file, loading them into the TRIGGERS global.
        """
        trigger = None
        for line in open(filename):
            if not line.strip():
                continue
            if line.startswith('@@@ '):
                trigger = re.compile(line[4:].strip())
                if trigger not in self.TRIGGERS:
                    self.TRIGGERS[trigger] = []
            elif trigger:
                self.TRIGGERS[trigger].append(line.strip())

    def trigger_check(self, slackclient, user, channel, text):
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
        for trigger in self.TRIGGERS:
            if trigger.match(text):
                msg = random.choice(self.TRIGGERS[trigger])
                msg = self.mention(user) + ': ' + msg
                channel.send_message(msg)
                return True
        else:
            # No triggers matched. Inform our caller so they can decide what to do.
            return False

    def mention(self, user):
        """Generate a mention for the given user.

        Args:
            user: a slackclient.User object for the user to mention.
        """
        return '<@{}|{}>'.format(user.id, user.name)

    def clean_text(self, text):
        # Remove @mentions and emoji
        text = self.MENTION_RE.sub('', text)
        text = self.EMOJI_RE.sub('', text)
        text = text.lower()
        return text.strip()

    def handle_mention_message(self, slackclient, user, channel, text):
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
        clean = self.clean_text(text)

        message_processed = False
        for order_re in self.ORDERS_DISPATCH:
            match = order_re.match(clean)
            if match:
                self.ORDERS_DISPATCH[order_re](slackclient, user, channel, match)
                message_processed = True
                break

        if self.trigger_check(slackclient, user, channel, clean):
            message_processed = True

        if not message_processed:
            # We were mentioned, but we don't know what to do... Say
            # something back to them.
            channel.send_message('I am sorry {}, I can\'t do that.'.format(
                self.mention(user)))

    def handle_message(self, slackclient, event):
        logger = logging.getLogger('handle_message')
        logger.debug('message event: %s', event)
        channel = slackclient.server.channels.find(event['channel'])

        # If the user edits their message, we treat it as if it were a new
        # message from that person.
        if 'subtype' in event and event['subtype'] == 'message_changed':
            event = event['message']
        if 'user' not in event:
            # Ignore events from non-users (i.e. coffebot app messages)
            return
        user = slackclient.server.users.find(event['user'])
        text = event['text']

        mentions = self.MENTION_RE.findall(text)
        logger.info('Mentions: %s', mentions)

        # Behaviours:
        if self.USER_ID in mentions:
            self.handle_mention_message(slackclient, user, channel, text)
        elif ':coffee:' in text:
            msg = 'Mmmm... :coffee:' + ':coffee:' * random.randint(0, 7)
            channel.send_message(msg)

    def loop(self, client):
        logger = logging.getLogger('loop')
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
                    for handler in self.DISPATCH.get(event['type'], []):
                        handler(client, event)
            time.sleep(0.1)


def main():
    threads = []
    for slack_workspace in models.SlackTeamAccessToken.query.filter(
            models.SlackTeamAccessToken.coffee_bot_slack_access_token != None,  # noqa: E711. `!= None` is needed for SQLAlchemy operator binding magic. `is not None` does not work.
    ):
        sb = WrappedSlackBot(
                slack_workspace.coffee_bot_slack_access_token,
                slack_workspace.coffee_bot_slack_user_id,
                slack_workspace.team_id,
        )
        threads.append(
                threading.Thread(
                    target=sb.loop, args=(sb.client,)))
    # Start all threads
    for thread in threads:
        thread.start()
    # Wait for all threads to finish.
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # if not TOKEN or not USER_ID:
    #     logging.error('Missing slack token or slack user id')

    # FIXME: This is a hack... But I can't think of anything better.
    # Add a test request context so that babel will work.
    app.test_request_context().push()

    main()

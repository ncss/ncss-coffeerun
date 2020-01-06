import logging
import os
import pprint
import random
import re
import threading
import time
import typing

from application import app, db, events, models
from application.models import Cafe, Coffee, Event, Run, User, sydney_timezone_now

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
        self.ORDERS_DISPATCH[re.compile(r'(?:(?:list) )?cafes')] = self.list_cafes
        self.ORDERS_DISPATCH[re.compile(r'create run cafe=(?P<cafeid>[0-9]+) time=(?P<time>(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})) pickup=(?P<pickup>.*)')] = self.create_run
        self.ORDERS_DISPATCH[re.compile(r'order(?: an?)? ([^\=]+)(?: run=(?P<runid>[0-9]+))?')] = self.order_coffee
        self.ORDERS_DISPATCH[re.compile(r'([^\=]+) (?:plz|pls|please|plox)(?: run=(?P<runid>[0-9]+))?')] = self.order_coffee
        self.ORDERS_DISPATCH[re.compile(r'close run(?: run=(?P<runid>[0-9]+))')] = self.close_run
        self.ORDERS_DISPATCH[re.compile(r'announce run(?: run=(?P<runid>[0-9]+))?')] = self.announce_delivery

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

    def list_cafes(self, slackclient, user, channel, match):
        """Handle the 'list cafes' command.

        Args:
            slackclient: the slackclient.SlackClient object for the current
                connection to Slack.
            user: the slackclient.User object for the user who send the
                message to us.
            channel: the slackclient.Channel object for the channel the
                message was received on.
            match: the object returned by re.match (an _sre.SRE_Match object).
        """
        q = Cafe.query.all()
        if not q:
            channel.send_message('No cafes listed')
        for cafe in q:
            channel.send_message('Cafe {}: {} at {}'.format(cafe.id, cafe.name, cafe.location))

    def create_run(self, slackclient, user, channel, match):
        """Create an open run

        Args:
            slackclient: the slackclient.SlackClient object for the current
                connection to Slack.
            user: the slackclient.User object for the user who send the
                message to us.
            channel: the slackclient.Channel object for the channel the
                message was received on.
            match: the object returned by re.match (an _sre.SRE_Match object).
        """
        logger = logging.getLogger('create_run')
        logger.info('Matches: %s', pprint.pformat(match.groupdict()))
        cafeid = match.group('cafeid')
        if cafeid and cafeid.isdigit():
            cafe = Cafe.query.filter_by(id=int(cafeid)).first()
        if not cafe:
            channel.send_message('Cafe does not exist. These are the available cafes:')
            self.list_cafes(slackclient, user, channel, match=None)
            return

        pickup = match.groupdict().get('pickup', None)
        timestr = match.groupdict().get('time', None)

        # Get the person creating the run
        person = utils.get_or_create_user(user.id, self.TEAM_ID, user.name)
        logger.info('User: %s', user)

        # Assume valid? Create the run
        run = Run(timestr)
        run.person = person
        run.fetcher = person
        run.cafeid = cafeid
        run.pickup = pickup
        run.modified = sydney_timezone_now()
        run.is_open = True

        db.session.add(run)
        db.session.commit()

        # Create the event
        self.write_to_events("created", "run", run.id, run.person)

        # Notify Slack
        try:
            events.run_created(run.id)
        except Exception as e:
            logging.exception('Error while trying to send notifications.')

    def close_run(self, slackclient, user, channel, match):
        """Close a run so that no more coffees may be added.

        Args:
            slackclient: the slackclient.SlackClient object for the current
                connection to Slack.
            user: the slackclient.User object for the user who send the
                message to us.
            channel: the slackclient.Channel object for the channel the
                message was received on.
            match: the object returned by re.match (an _sre.SRE_Match object).
        """
        logger = logging.getLogger('close_run')
        logger.info('Matches: %s', pprint.pformat(match.groupdict()))

        # Find the user that requested this
        person = utils.get_or_create_user(user.id, self.TEAM_ID, user.name)
        logger.info('User: %s', dbuser)

        runid = match.groupdict().get('runid', None)
        run = None
        if runid and runid.isdigit():
            run = Run.query.filter_by(id=int(runid)).first()
        else:
            runs = Run.query.filter(is_open=True) \
                .filter(Run.person == person.id) \
                .order_by('time').all()
            if len(runs) > 1:
                channel.send_message(
                        'More than one open run, please specify by adding run=<id> on the end.')
                self.list_runs(slackclient, user, channel, match=None)
                return
            if len(runs) == 0:
                channel.send_message('No open runs')
                return
            run = runs[0]

        # Change run to closed
        run.is_open = False
        db.session.add(run)
        db.session.commit()

        # Create event
        self.write_to_events("updated", "run", run.id, run.person)

        # Notify Slack
        try:
            events.run_closed(run.id)
        except Exception as e:
            logging.exception('Error while trying to send notifications.')

    def announce_delivery(self, slackclient, user, channel, match):
        """Announce the delivery of a run.

        Args:
            slackclient: the slackclient.SlackClient object for the current
                connection to Slack.
            user: the slackclient.User object for the user who send the
                message to us.
            channel: the slackclient.Channel object for the channel the
                message was received on.
            match: the object returned by re.match (an _sre.SRE_Match object).
        """
        logger = logging.getLogger('announce_delivery')
        logger.info('Matches: %s', pprint.pformat(match.groupdict()))

        runid = match.groupdict().get('runid', None)
        run = None
        if runid and runid.isdigit():
            run = Run.query.filter_by(id=int(runid)).first()
        else:
            runs = Run.query.filter(is_open=True) \
                .filter(Run.person == person.id) \
                .order_by('time').all()
            if len(runs) > 1:
                channel.send_message(
                        'More than one open run, please specify by adding run=<id> on the end.')
                self.list_runs(slackclient, user, channel, match=None)
                return
            if len(runs) == 0:
                channel.send_message('No open runs')
                return
            run = runs[0]

        # Notify Slack
        try:
            events.run_delivered(run.id)
        except Exception as e:
            logging.exception('Error while trying to send notifications.')

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
        self.write_to_events("created", "coffee", coffee.id, coffee.person)
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
        # FIXME(tsukasa-au): This is a hack... But I can't think of anything
        # better.
        # Add a test request context so that babel will work.
        app.test_request_context().push()

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

    def write_to_events(action, objtype, objid, user=None):
        if user:
            event = Event(user.id, action, objtype, objid)
        else:
            event = Event(current_user.id, action, objtype, objid)
        event.time = sydney_timezone_now()
        db.session.add(event)
        db.session.commit()
        return event.id


def _die_on_exception_wrapper(f: typing.Callable):
    '''Wrapper that kills the current process if an exception is thrown.

    This function is used to make sure that we restart the chatbot on any
    errors. This is a temporary hack.
    '''
    def _wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            logging.exception(
                'One of the connections had an error, killing the entire '
                'process to allow heroku to restart it.')
            os.kill(os.getpid(), 9)
    return _wrapper


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
                    target=_die_on_exception_wrapper(sb.loop), args=(sb.client,)))
    # Start all threads
    for thread in threads:
        thread.start()
    # Wait for all threads to finish.
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # FIXME: This is a hack... But I can't think of anything better.
    # Add a test request context so that babel will work.
    app.test_request_context().push()

    main()

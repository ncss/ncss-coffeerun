'''
Set of event types for the purpose of notifications.
'''
__all__ = [
    'EventType',
    'coffee_added',
    'run_created', 'run_closed', 'run_delivered',
]


class EventType:
    NONE = 0
    RUN_CREATED = 1
    RUN_CLOSED = 2
    RUN_DELIVERED = 3
    COFFEE_ADDED = 4


def run_created(run_id):
    dispatch_event({'type': EventType.RUN_CREATED, 'run_id': run_id})


def run_closed(run_id):
    dispatch_event({'type': EventType.RUN_CLOSED, 'run_id': run_id})


def run_delivered(run_id):
    dispatch_event({'type': EventType.RUN_DELIVERED, 'run_id': run_id})


def coffee_added(run_id, coffee_id):
    dispatch_event({'type': EventType.COFFEE_ADDED, 'run_id': run_id, 'coffee_id': coffee_id})


def dispatch_event(payload):
    from application.slack_notifications import process_event
    process_event(payload)

"""One tariff selection rule for views, notifications and checkout."""


def separate_rates(event):
    event = dict(event)
    return (event.get('event_participation_type', event.get('participation_type')) == 'both'
            and all(event.get(key) is not None for key in ('individual_fee_amount', 'team_fee_amount')))


def tariff(event, participation_type):
    event = dict(event)
    if separate_rates(event):
        if participation_type not in {'individual', 'team'}:
            raise ValueError('参加単位を選択してください')
        return event[participation_type + '_fee_amount'], '1チーム' if participation_type == 'team' else '1人'
    # Null columns are intentional: legacy events keep their original unit.
    return event.get('fee_amount'), event.get('fee_unit') or '1人'


def amount_due(event, application):
    application = dict(application)
    amount, unit = tariff(event, application.get('participation_type'))
    if amount is None:
        return None
    return amount * (1 if unit == '1チーム' else int(application.get('participant_count') or 1))


def is_free(event):
    event = dict(event)
    if separate_rates(event):
        return event['individual_fee_amount'] == event['team_fee_amount'] == 0
    return event.get('fee_amount') == 0

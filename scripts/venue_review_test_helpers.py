"""Keep historical preservation checks strict around the sourced November closure."""
def before_november3_closure(rows, baseline):
    rows = before_november4_closure(rows, baseline)
    from record_venue_fee_review_20261103 import CLOSED, CHECKED, CLOSURE_NOTE, CLOSURE_EVIDENCE
    old = next((r for r in baseline if r['id'] == CLOSED), None)
    if old is None:
        return rows
    result = []
    for row in rows:
        if row['id'] == CLOSED and row.get('checked_at') == CHECKED and old.get('checked_at', '') < CHECKED:
            assert row['availability_status'] == 'SUSPENDED'
            assert row['availability_note'] == CLOSURE_NOTE
            assert row['sources'] == old['sources'] + [CLOSURE_EVIDENCE]
            row = dict(row, **{k: old[k] for k in ['checked_at', 'availability_status', 'availability_note', 'sources']})
        result.append(row)
    return result


def before_november4_closure(rows, baseline):
    rows = before_november6_closure(rows, baseline)
    from record_venue_fee_review_20261104 import CLOSED, CHECKED, CLOSURE_NOTE, CLOSURE_EVIDENCE
    old = next((r for r in baseline if r['id'] == CLOSED), None)
    if old is None:
        return rows
    result = []
    for row in rows:
        if row['id'] == CLOSED and row.get('checked_at') == CHECKED and old.get('checked_at', '') < CHECKED:
            assert row['availability_status'] == 'SUSPENDED'
            assert row['availability_note'] == CLOSURE_NOTE
            assert row['sources'] == old['sources'] + [CLOSURE_EVIDENCE]
            row = dict(row, **{k: old[k] for k in ['checked_at', 'availability_status', 'availability_note', 'sources']})
        result.append(row)
    return result


def before_november6_closure(rows, baseline):
    from record_venue_fee_review_20261106 import CLOSED, CHECKED, CLOSURE_NOTE, CLOSURE_EVIDENCE
    old = next((r for r in baseline if r['id'] == CLOSED), None)
    if old is None or old.get('checked_at', '') >= CHECKED:
        return rows
    result = []
    for row in rows:
        if row['id'] == CLOSED:
            assert row['checked_at'] == CHECKED
            assert row['availability_status'] == 'SUSPENDED'
            assert row['availability_note'] == CLOSURE_NOTE
            assert row['sources'] == old['sources'] + [CLOSURE_EVIDENCE]
            row = dict(row)
            for key in ['checked_at', 'availability_status', 'availability_note', 'sources']:
                if key in old:
                    row[key] = old[key]
                else:
                    row.pop(key, None)
        result.append(row)
    return result


def assert_historical_hold(test, row):
    from record_venue_fee_review_20261104 import SHINKAWA, CHECKED, reviewed_fees
    from venues.sports_catalog import has_price
    if row['id'] == SHINKAWA:
        reviewed, = [r for r in reviewed_fees() if r['id'] == SHINKAWA]
        test.assertEqual(row['fee_checked_at'], CHECKED)
        test.assertEqual(row['fee_options'], reviewed['fee_options'])
        test.assertEqual(row['fee_note'], reviewed['fee_note'])
        test.assertTrue(has_price(row))
    elif row.get('fee_checked_at') == '2026-11-07':
        from record_venue_fee_review_20261107 import reviewed_fees as later_fees
        reviewed, = [r for r in later_fees() if r['id'] == row['id']]
        test.assertEqual(row['fee_options'], reviewed['fee_options'])
        test.assertEqual(row['fee_note'], reviewed['fee_note'])
        test.assertTrue(has_price(row))
    elif row.get('fee_checked_at') == '2026-11-06':
        from record_venue_fee_review_20261106 import reviewed_fees as later_fees
        reviewed, = [r for r in later_fees() if r['id'] == row['id']]
        test.assertEqual(row['fee_options'], reviewed['fee_options'])
        test.assertEqual(row['fee_note'], reviewed['fee_note'])
        test.assertTrue(has_price(row))
    else:
        test.assertFalse(has_price(row))
        test.assertEqual(row['fee_ranges'], [])

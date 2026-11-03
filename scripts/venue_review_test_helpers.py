"""Keep historical preservation checks strict around the sourced November closure."""
def before_november3_closure(rows, baseline):
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

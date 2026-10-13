"""Revisit candidate source pages and produce a PRIVATE publication review file.

Never edits the public seed, production DB or sends mail. Sources must still
identify the same club. Ambiguous/shared contacts stay in the review report.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time

import research_circle_contacts as crawler


def review(circle, contacts, fetcher, peers):
    valid, rejected = [], []
    for contact in contacts:
        url = crawler.safe_url(contact['source_url'])
        page = fetcher.fetch(url)
        found, _ = crawler.extract_contacts(circle, page, fetcher.parsed(url), peers)
        match = next((item for item in found if item['email'].casefold() == contact['email'].casefold()), None)
        if not match:
            rejected.append({'email': contact['email'], 'url': url, 'reason': page['status'] if page['status'] != 'ok' else 'club_contact_not_confirmed'})
            continue
        try:
            email = crawler.contact_store.contact_email(match['email'])
            source = crawler.contact_store.public_url(match['source_url'], True)
        except ValueError:
            rejected.append({'email': contact['email'], 'url': url, 'reason': 'invalid_contact'})
            continue
        valid.append({'circle_id': circle['circle_id'], 'circle_name': circle['circle_name'],
                      'circle_source_url': circle['source_url'], 'email': email, 'source_url': source,
                      'purpose': '団体紹介・募集ページに掲載された連絡先（招待受入・到達は未確認）',
                      'checked_at': page['checked_at'][:10], 'evidence': match['evidence'],
                      'attribution': match['attribution']})
    return {'circle_id': circle['circle_id'], 'verified': valid, 'rejected': rejected}


def publishable(results):
    by_email = defaultdict(set)
    for row in results:
        for item in row['verified']:
            by_email[item['email'].casefold()].add(row['circle_id'])
    selected = []
    for row in results:
        for item in row['verified']:
            if len(by_email[item['email'].casefold()]) == 1:
                selected.append(item)
                break
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--research', type=Path, action='append', required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--reuse-cache', type=Path, action='append', default=[])
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    circles = {c['circle_id']: c for c in json.loads(args.inventory.read_text(encoding='utf-8'))}
    peers = defaultdict(list)
    for circle in circles.values():
        peers[circle['university_id']].append(circle['circle_name'])
    candidates = defaultdict(dict)
    for path in args.research:
        for row in json.loads(path.read_text(encoding='utf-8'))['results']:
            if row['circle_id'] in circles and row['status'] == 'email_found':
                for contact in row['contacts']:
                    candidates[row['circle_id']][(contact['email'].casefold(),contact['source_url'])] = contact
    journal = args.directory / 'review.jsonl'
    done = {}
    if journal.exists():
        for line in journal.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            done[row['circle_id']] = row
    fetcher = crawler.Fetcher(args.directory / 'pages.sqlite', reuse_caches=args.reuse_cache)
    print(json.dumps({'candidates':len(candidates),'pending':len(set(candidates)-set(done))}), flush=True)
    last = time.monotonic()
    with journal.open('a',encoding='utf-8') as out, ThreadPoolExecutor(max_workers=max(1,min(args.workers,12))) as pool:
        tasks = {pool.submit(review,circles[ident],list(contacts.values()),fetcher,peers[circles[ident]['university_id']]):ident
                 for ident,contacts in candidates.items() if ident not in done}
        for task in as_completed(tasks):
            ident = tasks[task]
            try:
                row = task.result()
            except Exception as exc:
                row = {'circle_id':ident,'verified':[],'rejected':[{'reason':type(exc).__name__}]}
            done[ident] = row
            out.write(json.dumps(row,ensure_ascii=False)+'\n')
            out.flush()
            if time.monotonic()-last > 20:
                print(json.dumps({'reviewed':len(done),'confirmed':sum(bool(r['verified']) for r in done.values())}),flush=True)
                last = time.monotonic()
    selected = publishable(list(done.values()))
    (args.directory/'candidates.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
    report = {'reviewed':len(done),'publishable':len(selected),
              'rejected_reasons':dict(Counter(i['reason'] for r in done.values() for i in r['rejected'])),
              'by_organization':dict(Counter(circles[r['circle_id']].get('organization_type','unknown') for r in selected))}
    (args.directory/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()

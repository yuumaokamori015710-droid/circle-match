"""Individually reviewed public club inboxes, separate from private research."""
from datetime import date
import json
from pathlib import Path
from circlematch_contact_research import contact_email, public_url

SEED_PATH = Path(__file__).with_name('circle_public_contacts.json')


def ensure_tables(conn):
    conn.execute('''create table if not exists circle_public_contacts (
        circle_id text primary key references circles(circle_id),
        email text not null, source_url text not null, purpose text not null,
        checked_at text not null, enabled integer not null default 1 check(enabled in (0,1)),
        contact_method text not null default 'email', contact_url text not null default '')''')
    columns = {row['name'] for row in conn.execute('pragma table_info(circle_public_contacts)')}
    if 'contact_method' not in columns:
        conn.execute("alter table circle_public_contacts add column contact_method text not null default 'email'")
    if 'contact_url' not in columns:
        conn.execute("alter table circle_public_contacts add column contact_url text not null default ''")


def import_reviewed(conn):
    """Only exact identity matches; keep suppressed records suppressed on restart."""
    entries = json.loads(SEED_PATH.read_text(encoding='utf-8'))
    seen = set()
    for item in entries:
        ident = item['circle_id']
        method = item.get('contact_method', 'email')
        if method not in {'email', 'form', 'line'}:
            raise ValueError('Invalid reviewed contact method')
        email = item.get('email', '')
        url = item.get('contact_url', '')
        if method == 'email':
            contact_email(email)
            if url:
                raise ValueError('Email contacts cannot have an external contact URL')
        elif email or not url:
            raise ValueError('Non-email contacts require a contact URL and no email')
        if url:
            public_url(url, True)
        public_url(item['source_url'], True)
        identity_source = item.get('circle_source_url', item['source_url'])
        public_url(identity_source, True)
        if ident in seen or not item['purpose']:
            raise ValueError('Invalid reviewed club contact')
        seen.add(ident)
        date.fromisoformat(item['checked_at'])
        circle = conn.execute('select circle_name,source_url from circles where circle_id=?', (ident,)).fetchone()
        if not circle or circle['circle_name'].strip() != item['circle_name'].strip() or circle['source_url'] != identity_source:
            continue
        conn.execute('''insert into circle_public_contacts(circle_id,email,source_url,purpose,checked_at,contact_method,contact_url)
            values(?,?,?,?,?,?,?) on conflict(circle_id) do update set email=excluded.email,
            source_url=excluded.source_url,purpose=excluded.purpose,checked_at=excluded.checked_at,
            contact_method=excluded.contact_method,contact_url=excluded.contact_url
            where circle_public_contacts.checked_at < excluded.checked_at''',
            (ident,email,item['source_url'],item['purpose'],item['checked_at'],method,url))


def attach(conn, circles):
    """One query per result page. Profile privacy choices override directory data."""
    if not circles:
        return circles
    ids = [row['circle_id'] for row in circles]
    contacts = {row['circle_id']: dict(row) for row in conn.execute('''
        select d.* from circle_public_contacts d where d.enabled=1
        and d.circle_id in (''' + ','.join('?' for _ in ids) + ''')
        and not exists (select 1 from circle_public_profiles p where p.circle_id=d.circle_id
          and (coalesce(p.public_contact_consent,0)<>1 or coalesce(p.is_published,0)<>1))''', ids)}
    for circle in circles:
        if circle.get('public_contact_email'):
            circle.update(contact_method='email', contact_url='', contact_source_url=circle.get('profile_url', ''),
                          contact_purpose='団体が公開した連絡先', contact_checked_at='')
        elif circle['circle_id'] in contacts:
            contact = contacts[circle['circle_id']]
            circle.update(public_contact_email=contact['email'], contact_source_url=contact['source_url'],
                          contact_purpose=contact['purpose'], contact_checked_at=contact['checked_at'],
                          contact_method=contact['contact_method'], contact_url=contact['contact_url'])
    return circles

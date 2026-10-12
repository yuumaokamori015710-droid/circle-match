"""Searchable venue facts, without inventing unknown booking or opening rules."""
import re

VENUE_TYPES = (
    ('gym', '体育館・体育室'), ('field', 'グラウンド・球技場'),
    ('court', 'テニス・屋外コート'), ('track', '陸上競技場'),
    ('meeting', 'ホール・会議室・集会室'), ('karaoke', 'カラオケ'),
    ('boardgame', 'ボードゲームカフェ'), ('golf', 'ゴルフ場'),
    ('other', 'その他・複合スポーツ施設'),
)
CHANNELS = (('web', 'Web予約'), ('phone', '電話予約'), ('counter', '窓口申込'))

# Conservative common hours, not live availability or a promise of daily opening.
# Sources are the facility's official_url, checked 2026-10-12. Weekday/season
# differences and closures remain explicit in the public note.
HOURS = {
    'tokyo-sports-011': ('10:00', '23:00', '曜日共通の時間帯。土日祝は09:00開始。予約状況により短縮・年末年始は休業の場合あり。'),
    'tokyo-sports-020': ('11:00', '21:45', 'コートの利用可能時間。施設自体の営業時間とは異なります。休業・貸切は公式案内で確認。'),
    'tokyo-sports-021': ('10:00', '20:00', '曜日共通の時間帯。火～土は23:00まで。月曜・年末年始・アトレ休館日は休館。'),
    'tokyo-venue-9b93d81ca10e': ('09:00', '21:30', '月1回の整備日・年末年始等は休館。受付は20:00まで。'),
    'tokyo-venue-ed023319a334': ('09:00', '21:30', '月1回の整備日・年末年始等は休館。受付は20:00まで。'),
    'tokyo-venue-6178e8b63baa': ('09:00', '21:30', '月1回の整備日・年末年始等は休館。受付は20:00まで。'),
    'tokyo-venue-8a96774363e5': ('09:00', '21:30', '月1回の整備日・年末年始等は休館。受付は20:00まで。'),
    'tokyo-venue-84dbc0345777': ('09:00', '21:30', '月1回の整備日・年末年始等は休館。受付は20:00まで。'),
    'tokyo-venue-19395ebfe432': ('09:00', '21:30', '月1回の整備日・年末年始等は休館。受付は20:00まで。'),
    'tokyo-venue-712511e56aa8': ('07:00', '22:15', '施設の利用可能時間。第2月曜（休日は翌日）・年末年始は休館。'),
    'tokyo-venue-055c51c0ec00': ('09:00', '21:30', '第1月曜（祝日は翌日）・年末年始は休館。窓口は21:00まで。'),
    'tokyo-jelly-ikebukuro': ('13:00', '23:00', '曜日共通の時間帯。土日は10:00開店。最終受付22:00。不定休。'),
    'tokyo-jelly-shibuya': ('13:00', '23:00', '最終受付22:00。不定休。'),
}


def minutes(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        return None
    hour, minute = map(int, value.split(':'))
    return hour * 60 + minute


def within_hours(row, start='', end=''):
    start, end = minutes(start), minutes(end)
    if start is None and end is None:
        return True
    for opening, closing in row.get('opening_windows', []):
        if start is not None and end is not None:
            finish = end + (1440 if end < start else 0)
            if opening <= start < finish <= closing:
                return True
        elif start is not None and opening <= start < closing:
            return True
        elif end is not None and opening < end <= closing:
            return True
    return False


def enrich(row):
    label = row['facility_label']
    kinds = []
    for key, pattern in (
        ('gym', r'体育館|体育室|アリーナ'), ('field', r'野球|球技場|グラウンド|運動場|運動広場|サッカー場|フットサル場'),
        ('court', r'テニス|庭球|ピックルボールコート'), ('track', r'陸上競技場|トラック'),
        ('meeting', r'会議|集会|ホール|貸室|文化センター|イベント|地域活動|区民活動'),
        ('karaoke', r'カラオケ'), ('boardgame', r'ボードゲーム'), ('golf', r'ゴルフ'),
    ):
        if re.search(pattern, label):
            kinds.append(key)
    row['venue_types'] = kinds or ['other']
    method = row['booking_method']
    channels = []
    web = r'Web|ウェブ|ネット|オンライン|予約システム|電子申請|予約ねっと|えどねっと|けやきネット|うぐいすネット|さざんかねっと'
    if re.search(web, method, re.I) and not re.search(r'空き.*のみ|照会のみ|予約不可', method):
        channels.append('web')
    if '電話' in method and not re.search(r'電話.*(?:不可|できません|受け付けません)', method):
        channels.append('phone')
    if re.search(r'窓口|フロント|来館申請|来館予約', method):
        channels.append('counter')
    row['booking_channels'] = channels
    # The absence of a registration statement is not evidence of no registration.
    text = method + ' ' + row['booking_note']
    unnecessary = re.search(r'登録(?:は|が)?不要|登録(?:は|が)?必要(?:ありません|ない)', text)
    necessary = re.search(r'登録後|登録(?:が|は)?必要(?:です|。|、|$)|登録必須|事前登録が必要', text)
    row['registration_required'] = None if unnecessary and necessary else False if unnecessary else True if necessary else None
    hours = HOURS.get(row['id'])
    row['opening_windows'] = [[minutes(hours[0]), minutes(hours[1])]] if hours else []
    row['opening_hours'] = f'{hours[0]}–{hours[1]}' if hours else ''
    row['opening_note'] = hours[2] if hours else ''
    row['opening_checked_at'] = '2026-10-12' if hours else ''
    return row

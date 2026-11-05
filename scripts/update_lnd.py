#!/usr/bin/env python3
"""Importa i calendari del girone di andata da Gare LND per l'Attività di Base."""
import html
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
BASE = 'https://gare.lnd.it/competizione/lombardia'
LEG = os.environ.get('LND_LEG', 'first').strip().lower()
if LEG not in ('first', 'second'):
    raise ValueError('LND_LEG deve essere first oppure second')
PHASE = 'Ritorno' if LEG == 'second' else 'Andata'
COMPETITIONS = {
    'esordienti-u13': {'campionato': 'E2', 'girone': 'E', 'name': 'Esordienti U13'},
    'esordienti-misti': {'campionato': 'N2', 'girone': 'A', 'name': 'Esordienti Misti'},
    'pulcini-u11': {'campionato': 'P2', 'girone': 'H', 'name': 'Pulcini U11'},
    'pulcini-u10': {'campionato': 'R2', 'girone': 'D', 'name': 'Pulcini U10'},
}
SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (compatible; AltoGardaResultsBot/1.0)',
    'Accept': 'text/html,application/xhtml+xml,application/json',
})


def get(obj, *keys):
    if isinstance(obj, dict):
        for key in keys:
            if obj.get(key) is not None:
                return obj[key]
    return None


def team_name(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(get(value, 'name', 'denomination', 'description', 'label', 'teamName') or '').strip()
    return ''


def norm(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip().upper()


def is_alto_garda(value):
    # Include la squadra principale e le denominazioni LND delle squadre collegate,
    # ad esempio "Alto Garda Sq.b".
    return norm(value).startswith('ALTO GARDA')


def parse_date(value):
    if not value:
        return None
    match = re.search(r'(20\d{2}-\d{2}-\d{2})', str(value))
    if match:
        return match.group(1)
    match = re.search(r'(\d{2})/(\d{2})/(20\d{2})', str(value))
    return f'{match.group(3)}-{match.group(2)}-{match.group(1)}' if match else None


def parse_time(value):
    match = re.search(r'(\d{1,2}:\d{2})', str(value or ''))
    return match.group(1) if match else None


def scan_matches(node, output):
    if isinstance(node, dict):
        if any(k in node for k in ('home', 'homeTeam', 'teamHome', 'localTeam')) and any(
            k in node for k in ('away', 'awayTeam', 'teamAway', 'visitorTeam')
        ):
            output.append(node)
        for value in node.values():
            scan_matches(value, output)
    elif isinstance(node, list):
        for value in node:
            scan_matches(value, output)


def page_json(response):
    try:
        return response.json()
    except ValueError:
        match = re.search(r'data-page="([^"]+)"', response.text)
        if not match:
            raise RuntimeError('Payload LND non riconosciuto')
        return json.loads(html.unescape(match.group(1)))


def current_version(url):
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    match = re.search(r'data-page="([^"]+)"', response.text)
    if match:
        try:
            return json.loads(html.unescape(match.group(1))).get('version')
        except (ValueError, AttributeError):
            pass
    return '86832c128bce74e5c6ae58b71f469bfd'


def parse_matches(payload):
    raw = []
    scan_matches(payload, raw)
    unique = {}
    for match in raw:
        home = team_name(get(match, 'home', 'homeTeam', 'teamHome', 'localTeam', 'home_name', 'homeTeamName'))
        away = team_name(get(match, 'away', 'awayTeam', 'teamAway', 'visitorTeam', 'away_name', 'awayTeamName'))
        if home or away:
            match_id = get(match, 'id', 'matchId', 'garaId')
            key = str(match_id) if match_id is not None else f'{home}|{away}|{get(match, "date", "matchDate")}'
            unique[key] = match
    return list(unique.values())


def normalize(match, round_no, slug):
    home = team_name(get(match, 'home', 'homeTeam', 'teamHome', 'localTeam', 'home_name', 'homeTeamName', 'local'))
    away = team_name(get(match, 'away', 'awayTeam', 'teamAway', 'visitorTeam', 'away_name', 'awayTeamName', 'ospite'))
    home_is_ag = is_alto_garda(home)
    away_is_ag = is_alto_garda(away)
    explicit_rest = bool(get(match, 'isRest', 'rest'))
    empty_opponent_rest = (home_is_ag and not away) or (away_is_ag and not home)

    # REGOLA GENERALE: LND restituisce anche i riposi degli avversari.
    # Una riga di riposo è nostra soltanto se nomina Alto Garda (inclusa Sq.B)
    # e non contiene un avversario. I riposi delle altre società vengono scartati.
    is_rest = (explicit_rest or empty_opponent_rest) and empty_opponent_rest
    if is_rest:
        if not (home_is_ag or away_is_ag):
            return None
    elif not (home_is_ag or away_is_ag):
        return None

    if slug == 'pulcini-u11':
        def u11_name(value):
            key = re.sub(r'[.\s_-]+', ' ', norm(value)).strip()
            if re.fullmatch(r'ALTO GARDA\s+(?:SQ\s*B|SQUADRA\s+B|B|NERA)', key):
                return 'ALTO GARDA (NERA)'
            if key in ('ALTO GARDA', 'ALTO GARDA BLU'):
                return 'ALTO GARDA (BLU)'
            return value
        home = u11_name(home)
        away = u11_name(away)

    field = get(match, 'field', 'fieldName', 'facility', 'ground', 'campo')
    address = get(match, 'fieldAddress', 'address', 'facilityAddress', 'groundAddress')
    if isinstance(field, dict):
        field = team_name(field)

    return {
        'id': get(match, 'id', 'matchId', 'garaId'),
        'giornata': round_no,
        'date': parse_date(get(match, 'date', 'matchDate', 'datetime', 'startDate', 'data', 'dateTime')),
        'time': parse_time(get(match, 'time', 'matchTime', 'hour', 'orario', 'startTime')),
        'home': home or 'ALTO GARDA',
        'away': away,
        'homeGoals': get(match, 'homeGoals', 'homeScore', 'goalsHome', 'scoreHome', 'localGoals'),
        'awayGoals': get(match, 'awayGoals', 'awayScore', 'goalsAway', 'scoreAway', 'visitorGoals'),
        'field': field,
        'fieldAddress': address,
        'isRest': is_rest,
        'isPlayed': bool(get(match, 'isPlayed', 'played', 'isFinished')),
        'resultState': get(match, 'resultState', 'status', 'state'),
        'variation': get(match, 'variation', 'change', 'variationStatus'),
    }


def fetch_round(config, round_no, version):
    params = {
        'campionato': config['campionato'], 'giornata': round_no,
        'girone': config['girone'], 'leg': LEG, 'stagione': '2026',
    }
    url = BASE + '?' + urlencode(params)
    headers = {
        'X-Inertia': 'true', 'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'text/html, application/xhtml+xml', 'Referer': BASE,
        'X-Inertia-Partial-Component': 'QuadroGare/Home',
        'X-Inertia-Partial-Data': 'matches,currentMatchday',
    }
    if version:
        headers['X-Inertia-Version'] = version
    response = SESSION.get(url, headers=headers, timeout=30)
    if response.status_code == 409:
        version = current_version(BASE + '?' + urlencode({
            'campionato': config['campionato'], 'girone': config['girone'], 'stagione': '2026'
        }))
        if version:
            headers['X-Inertia-Version'] = version
        response = SESSION.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return page_json(response)


def import_one(slug, config):
    base_url = BASE + '?' + urlencode({
        'campionato': config['campionato'], 'girone': config['girone'], 'stagione': '2026'
    })
    version = current_version(base_url)
    fixtures, seen = [], set()
    empty_rounds = 0
    for round_no in range(1, 19):
        payload = fetch_round(config, round_no, version)
        round_fixtures = []
        for match in parse_matches(payload):
            fixture = normalize(match, round_no, slug)
            if fixture is None:
                continue
            key = str(fixture['id']) if fixture['id'] is not None else str(
                (fixture['giornata'], fixture['date'], fixture['home'], fixture['away'])
            )
            if key not in seen:
                seen.add(key)
                round_fixtures.append(fixture)
        if round_fixtures:
            fixtures.extend(round_fixtures)
            empty_rounds = 0
        else:
            empty_rounds += 1
            if round_no >= 9 and empty_rounds >= 2:
                break
        time.sleep(0.25)

    if len(fixtures) < 5:
        raise RuntimeError(f'Solo {len(fixtures)} appuntamenti trovati: file precedente conservato')

    fixtures.sort(key=lambda f: (f['giornata'], f['date'] or '', f['time'] or ''))
    return {
        'source': 'Gare LND', 'competition': config['name'],
        'campionato': config['campionato'], 'girone': config['girone'],
        'season': '2026/2027', 'phase': PHASE, 'team': 'ALTO GARDA',
        'updatedAt': date.today().isoformat(), 'fixtures': fixtures,
    }


def main():
    DATA.mkdir(exist_ok=True)
    errors = []
    for slug, config in COMPETITIONS.items():
        try:
            obj = import_one(slug, config)
            output = DATA / f'{slug}.json'
            temporary = output.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(output)
            print(f"OK {config['name']}: {len(obj['fixtures'])} gare/appuntamenti")
        except Exception as exc:
            errors.append(f"{config['name']}: {exc}")
            print(f"ERRORE {config['name']}: {exc}", file=sys.stderr)
    if len(errors) == len(COMPETITIONS):
        sys.exit('Import LND fallito per tutte le squadre; nessun dato precedente è stato sovrascritto.')
    if errors:
        print('Avvisi: ' + '; '.join(errors), file=sys.stderr)


if __name__ == '__main__':
    main()

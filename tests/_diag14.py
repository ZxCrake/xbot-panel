import re
import sys
sys.path.insert(0, '.')
from curl_cffi import requests

sb = [l.strip() for l in open('sandbox/account.txt', encoding='utf-8')
      if l.strip() and not l.startswith('format')][0].split(':')
user, xpass, email, ct0, auth = sb[0], sb[1], sb[2], sb[3], sb[4]
S = requests.Session(impersonate='chrome124', headers={
    'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
    'x-csrf-token': ct0,
    'Cookie': f'auth_token={auth}',
})
BASE = 'https://x.com/i/api/1.1'

r = S.get(f'{BASE}/account/settings.json', timeout=20)
print('GET settings', r.status_code, str(r.json())[:200])

# POST form (attendu par 1.1)
r = S.post(f'{BASE}/account/settings.json',
           data={'email': email}, timeout=20)
print('POST form', r.status_code, r.text[:300])

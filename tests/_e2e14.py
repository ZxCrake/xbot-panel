import json, time, urllib.request

B = 'http://127.0.0.1:5000'


def call(ep, body=None, tok=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(B + ep, data=data,
                                 method='POST' if data else 'GET')
    if data:
        req.add_header('Content-Type', 'application/json')
    if tok:
        req.add_header('Authorization', 'Bearer ' + tok)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.getcode(), json.loads(r.read())


c, j = call('/api/login', {'username': 'pan1', 'password': 'mdp12345678'})
tok = j['token']
print('login', c, j.get('role'))

# sandbox/account.txt : ligne 1 = "format:User:pass:email:ct0:auth:2fa",
# puis 1 compte par ligne (5 ou 6 champs ; auth = index 4).
sb = [l.strip() for l in open('sandbox/account.txt', encoding='utf-8')
      if l.strip() and not l.startswith('format')][0].split(':')
user, xpass, email, auth = sb[0], sb[1], sb[2], sb[4]
print('champs lu: user=%s | pass=%s | email=%s | token=%s' % (
    bool(user), bool(xpass), bool(email), bool(auth)))

c, j = call('/api/import-accounts', {
    'fields': ['USER', 'PASS', 'AUTH_TOKEN'], 'separator': ':',
    'mode': 'replace', 'content': '%s:%s:%s' % (user, xpass, auth)}, tok)
print('import', c, j)

c, j = call('/api/file/accounts.txt', None, tok)
f = j['content'].strip().split(':')
print('sauvegarde: [0]=%s | n2=%s | [-1]=%s' % (
    f[0], bool(f[1]) if len(f) > 2 else '-', bool(f[-1])))

c, j = call('/api/file/emails.txt', {'content': '%s:gpass123' % email}, tok)
print('emails.txt', c, j)

c, j = call('/api/run', {'action_mode': 14}, tok)
print('run', c, j)

s = {}
for _ in range(80):
    time.sleep(1.5)
    c, s = call('/api/status', None, tok)
    if not s.get('running'):
        break
print('status:', json.dumps(s, ensure_ascii=False)[:900])

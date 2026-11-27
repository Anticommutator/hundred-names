"""Rebuild the site's data files from build/base.json.

base.json holds, per country, every first name Forebears lists with its estimated number of
male / female bearers (key 'a' = ungendered, used for the World page). families.txt lists the
spelling families merged in the "merge spellings" view on top of the automatic fold() rules.

Run from the repo root:  python3 build/build.py
Writes index.html, names.json, ni/*.json, quiz.json.
"""
import json, os, re, shutil, unicodedata
import numpy as np

B = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(B)
BASE = json.load(open(f'{B}/base.json'))
COUNTRIES = json.load(open(f'{B}/countries.json'))
EXCL = open(f'{B}/excluded.json').read()


# ---------- spelling families ----------
def fold(n):
    n = unicodedata.normalize('NFKD', n.lower())
    n = ''.join(ch for ch in n if not unicodedata.combining(ch) and ch.isalpha())
    for a, b in (('ph', 'f'), ('th', 't'), ('ou', 'u'), ('oo', 'u'), ('ee', 'i'), ('y', 'i')):
        n = n.replace(a, b)
    n = re.sub(r'(.)\1+', r'\1', n)
    if len(n) > 3 and n.endswith('h') and n[-2] in 'aeiou': n = n[:-1]
    return n


def load_families():
    """families.txt: one family per line, spellings separated by spaces ('_' stands for a space
    inside a name). The first spelling names the family. '!' lines list spellings split off from
    the family fold() would put them in (e.g. Stefan vs Stephen, Tam vs Tham, Fatma vs Fatima)."""
    fams, apart = [], []
    for line in open(f'{B}/families.txt'):
        line = line.split('#')[0].strip()
        if not line: continue
        ws = [w.replace('_', ' ') for w in line.lstrip('!').split()]
        (apart if line.startswith('!') else fams).append(ws)
    return fams, apart


FAMS, APART = load_families()
CUR = {}
for ws in FAMS:
    k = fold(ws[0])
    for w in ws: CUR[fold(w)] = k
SPLIT = {}  # exact spelling -> own key, overriding the fold
for ws in APART:
    for w in ws: SPLIT[w] = fold(w) + '~'  # split-off spellings that fold alike stay together


def mkey0(n):
    if n in SPLIT: return SPLIT[n]
    k = fold(n)
    return CUR.get(k, k) or n


# merges.txt: one line per name family that joins several of the families above, written as one
# spelling of each ('_' = space). Pairs were proposed by phonetic/edit-distance similarity and kept
# only when the two are the same given name AND sound nearly the same (see README).
MERGE = {}
if os.path.exists(f'{B}/merges.txt'):
    for line in open(f'{B}/merges.txt'):
        line = line.split('#')[0].strip()
        if not line: continue
        ks = [mkey0(w.replace('_', ' ')) for w in line.split()]
        for k in ks: MERGE[k] = ks[0]


def mkey(n):
    k = mkey0(n)
    return MERGE.get(k, k)


# ---------- per-country lists and metrics ----------
def metrics(rows, T2, gendered):
    R_ = [dict(n=n, m=m, f=f, t=(m + f) if gendered else a, k=mkey(n)) for n, m, f, a in rows]
    fam = {}
    for r in R_: fam.setdefault(r['k'], []).append(r)
    sm = sum(r['m'] for r in R_); sw = sum(r['f'] for r in R_)
    fs = sw / (sm + sw) if gendered else None
    P = {'t': T2, 'm': T2 * (1 - fs) if gendered else None, 'f': T2 * fs if gendered else None}
    pc = lambda v, g: round(v / P[g] * 10000) / 100

    def spell(k, g):
        rs = sorted(fam[k], key=lambda r: -r[g])
        return [[r['n'], pc(r[g], g)] for r in rs if r[g] > 0] if len(rs) > 1 else None

    res = {}; lists = {}; ranks = {}
    for mode in ('raw', 'mrg'):
        if mode == 'raw':
            G = [dict(lab=r['n'], k=r['k'], t=r['t'], m=r['m'], f=r['f']) for r in R_]
        else:
            G = []
            for k, rs in fam.items():
                rs2 = sorted(rs, key=lambda r: -r['t'])
                G.append(dict(lab=rs2[0]['n'], k=k, t=sum(r['t'] for r in rs), m=sum(r['m'] for r in rs), f=sum(r['f'] for r in rs)))
        A = sorted(G, key=lambda g: -g['t'])
        r = dict(all=sum(g['t'] for g in A[:100]) / T2, t10=sum(g['t'] for g in A[:10]) / T2, top=A[0]['lab'], topp=A[0]['t'] / T2)
        L = {}; RK = []
        gl = (('m', 'm'), ('f', 'w')) if gendered else (('t', 'a'),)
        for g, key in gl:
            srt = sorted([x for x in G if x[g] > 0], key=lambda x: -x[g])
            L[key] = []
            for i, x in enumerate(srt):
                if i < 100:
                    e = [x['lab'], pc(x[g], g), x['k']]
                    sp = spell(x['k'], g)
                    if sp: e.append(sp)
                    L[key].append(e)
                RK.append([x['k'], x['lab'], key, i + 1, pc(x[g], g), round(x[g])])
        if gendered:
            r.update(m=sum(x['m'] for x in sorted(G, key=lambda x: -x['m'])[:100]) / P['m'],
                     w=sum(x['f'] for x in sorted(G, key=lambda x: -x['f'])[:100]) / P['f'], fs=fs,
                     tm=L['m'][0][0], tw=L['w'][0][0])
        res[mode] = r; lists[mode] = L; ranks[mode] = RK
    return res, lists, ranks


rnd = lambda d: {k: (round(v * 1000) / 10 if isinstance(v, float) and k != 'fs' else round(v * 100) if k == 'fs' else v) for k, v in d.items()}
out = []; NAMES = {}; INDEX = {}
for c in COUNTRIES:
    s = c['s']; rows = BASE[s]['rows']; T2 = c['pop']
    res, lists, ranks = metrics(rows, T2, s != 'earth')
    out.append(dict(c, raw=rnd(res['raw']), mrg=rnd(res['mrg'])))
    NAMES[s] = lists
    for mode in ('raw', 'mrg'):
        for k, lab, g, rk, pct, cnt in ranks[mode]:
            ent = INDEX.setdefault(k, {'sp': {}, 'raw': [], 'mrg': []})
            if mode == 'raw' and s != 'earth': ent['sp'][lab] = ent['sp'].get(lab, 0) + cnt
            ent[mode].append([s, g, lab, rk, pct, cnt])
for ent in INDEX.values():
    ent['sp'] = sorted(ent['sp'].items(), key=lambda x: -x[1])

# ---------- name vectors, neighbours, quiz pool ----------
ISO_OF = {d['s']: d['iso'] for d in out if d['iso']}
POP = {d['s']: d['pop'] for d in out}
CS = sorted(ISO_OF); ci = {c: i for i, c in enumerate(CS)}
KEYS = []; VEC = []; N100 = []
for k, ent in INDEX.items():
    cnt = {}; best = {}
    for c, g, lab, rk, pct, n in ent['mrg']:
        if c in ci:
            cnt[c] = cnt.get(c, 0) + n; best[c] = min(best.get(c, 999), rk)
    if not cnt: continue
    v = np.zeros(len(CS), dtype=np.float32)
    for c, n in cnt.items(): v[ci[c]] = n / POP[c] * 100
    KEYS.append(k); VEC.append(v); N100.append(sum(r <= 100 for r in best.values()))
VEC = np.array(VEC); SQ = np.sqrt(VEC); U = SQ / np.linalg.norm(SQ, axis=1, keepdims=True)  # sqrt damps a single stronghold
N100 = np.array(N100)
LAB = {k: (INDEX[k]['sp'][0][0] if INDEX[k]['sp'] else k) for k in KEYS}
cand = np.where(N100 >= 1)[0]; Uc = U[cand]
for i0 in range(0, len(KEYS), 2000):
    Sim = U[i0:i0 + 2000] @ Uc.T
    for r in range(Sim.shape[0]):
        i = i0 + r; row = Sim[r]
        o = np.argpartition(-row, 7)[:7]; o = o[np.argsort(-row[o])]
        nn = []
        for j in o:
            kj = KEYS[cand[j]]
            if kj == KEYS[i]: continue
            d = float(np.sqrt(max(0.0, 2 - 2 * row[j])))
            nn.append([kj, LAB[kj], round(d, 3)])
            if len(nn) == 5: break
        INDEX[KEYS[i]]['nn'] = nn

PSH = VEC / VEC.sum(axis=1, keepdims=True); NEFF = 1 / (PSH ** 2).sum(axis=1)  # effective number of countries
ok = np.where((N100 >= 3) & (NEFF <= 20))[0]  # drop flat, everywhere-at-once names
order = ok[np.argsort(-N100[ok], kind='stable')]
pool = []
for i in order[:400]:
    k = KEYS[i]; ent = INDEX[k]
    pool.append(dict(k=k, n=LAB[k], c=int(N100[i]), sp=[x for x, _ in ent['sp'][1:9]],
                     v={ISO_OF[CS[j]]: round(float(VEC[i, j]), 3) for j in np.nonzero(VEC[i])[0] if VEC[i, j] >= 0.005}))

# ---------- write ----------
os.chdir(ROOT)
json.dump(NAMES, open('names.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(pool, open('quiz.json', 'w'), ensure_ascii=False, separators=(',', ':'))
shutil.rmtree('ni', ignore_errors=True); os.makedirs('ni')
SH = {}
for k, ent in INDEX.items():
    c = k[0] if k and k[0] in 'abcdefghijklmnopqrstuvwxyz' else '_'
    SH.setdefault(c, {})[k] = ent
for c, d in SH.items():
    json.dump(d, open(f'ni/{c}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
t = open(f'{B}/template.html').read().replace('__DATA__', json.dumps(out, ensure_ascii=False)).replace('__EXCL__', EXCL)
open('index.html', 'w').write(t)
print(len(out), 'countries;', len(INDEX), 'name keys;', len(pool), 'quiz names')

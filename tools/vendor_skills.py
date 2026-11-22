#!/usr/bin/env python3
"""Install selected pinned MIT-licensed upstream PM skills without altering text."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import yaml

ROOT=Path(__file__).resolve().parents[1]

def manifest():return yaml.safe_load((ROOT/'upstream'/'skills.yaml').read_text())

def validate(data):
    sources={x['id']:x for x in data['sources']}
    if len(sources)!=len(data['sources']):raise ValueError('duplicate upstream source id')
    ids=set()
    for skill in data['skills']:
        if skill['id'] in ids:raise ValueError('duplicate skill id')
        ids.add(skill['id'])
        if skill['source'] not in sources:raise ValueError('unknown skill source')
        path=Path(skill['path'])
        if path.is_absolute() or '..' in path.parts or path.name!='SKILL.md':raise ValueError('unsafe skill path')
    for s in sources.values():
        if s['license']!='MIT' or len(s['commit'])!=40 or not all(x in '0123456789abcdef' for x in s['commit']):
            raise ValueError('unverified source license or commit pin')
    return sources

def download(url):
    with urlopen(url,timeout=20) as f:return f.read()

def install(data):
    sources=validate(data)
    lock={'sources':{},'skills':{}}
    for source in sources.values():
        repo,sha=source['repository'],source['commit']
        origin=f'https://raw.githubusercontent.com/{repo}/{sha}'
        license_file=download(origin+'/'+source['license_path'])
        if not license_file.startswith(b'MIT License'):
            raise ValueError(f'Unexpected license content for {repo}')
        dest=ROOT/'vendor'/source['id'];dest.mkdir(parents=True,exist_ok=True)
        (dest/'LICENSE').write_bytes(license_file)
        lock['sources'][source['id']]={'repository':repo,'commit':sha,'license_sha256':hashlib.sha256(license_file).hexdigest()}
    for skill in data['skills']:
        source=sources[skill['source']]
        origin=f"https://raw.githubusercontent.com/{source['repository']}/{source['commit']}/{skill['path']}"
        blob=download(origin)
        if not blob.startswith(b'---') or b'name:' not in blob:raise ValueError('Unexpected SKILL.md format: '+skill['id'])
        path=ROOT/'vendor'/source['id']/skill['id']/'SKILL.md'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
        lock['skills'][skill['id']]={'upstream_path':skill['path'],'sha256':hashlib.sha256(blob).hexdigest()}
    (ROOT/'vendor'/'LOCK.json').write_text(json.dumps(lock,indent=2)+'\n')
    print(f"Installed {len(data['skills'])} skills from pinned upstream commits")

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('check','install'))
    args=p.parse_args();data=manifest();validate(data)
    if args.action=='check':print(f"PASS: {len(data['skills'])} pinned upstream skill references")
    else:install(data)

if __name__=='__main__':main()

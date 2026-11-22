#!/usr/bin/env python3
"""Scaffold durable business planning workspace without creating invented knowledge."""
import argparse
import shutil
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--name',required=True)
    p.add_argument('--output',default='./work')
    p.add_argument('--platform',default='unspecified')
    a=p.parse_args()
    if not a.name or not all(c.isalnum() and c.isascii() or c in '-_' for c in a.name):
        p.error('name must contain ASCII letters, numbers, underscore or hyphen')
    target=Path(a.output).resolve()/a.name
    if target.exists():p.error('workspace already exists: '+str(target))
    for group in ('facts','questions','hypotheses','experiments','decisions','sources','segments','requirements','issues'):
        (target/'knowledge'/group).mkdir(parents=True,exist_ok=True)
    for folder in ('documents','state','investigations','history'):
        (target/folder).mkdir(exist_ok=True)
    for name in ('workflow','checkpoint','project'):
        src=ROOT/'templates'/'project'/f'{name}.yaml'
        dest=target/('state' if name!='project' else '')/f'{name}.yaml'
        shutil.copy2(src,dest)
    project=target/'project.yaml'
    data=yaml.safe_load(project.read_text())
    data.update(project=a.name,platform=a.platform)
    project.write_text(yaml.safe_dump(data,sort_keys=False))
    for f in (ROOT/'templates').glob('*.md'):
        shutil.copy2(f,target/'documents'/f.name)
    from reconciler import reconcile
    reconcile(target)
    print(target)

if __name__=='__main__':main()

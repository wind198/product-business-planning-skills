#!/usr/bin/env python3
"""Offline checks for templates and schema contract documents."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]

def main():
    schemas=list((ROOT/'schemas').glob('*.schema.json'))
    for p in schemas:Draft202012Validator.check_schema(json.loads(p.read_text()))
    templates=list((ROOT/'templates').glob('*.md'))
    if len(templates)!=9:raise ValueError(f'Expected nine document templates, found {len(templates)}')
    for t in templates:
        if not t.read_text().startswith('# '):raise ValueError(f'Missing title: {t}')
    for wf in (ROOT/'workflows').glob('*.md'):
        if not wf.read_text().startswith('# '):raise ValueError(f'Missing workflow heading: {wf}')
    print(f'PASS: {len(schemas)} schemas, {len(templates)} artifact templates')

if __name__=='__main__':main()

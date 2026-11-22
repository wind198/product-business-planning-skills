#!/usr/bin/env python3
"""Schema-validated, exact-key persistent facts with explicit user override history."""
import argparse
import json
import re
from datetime import datetime,timezone
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
KEY=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')

def read(path):
    data=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError(f'{path}: expected a mapping')
    return data

def validate_record(record,kind):
    schema=json.loads((ROOT/'schemas'/f'{kind}.schema.json').read_text())
    Draft202012Validator(schema).validate(record)

def facts(workspace):
    result=[]
    for path in sorted((workspace/'knowledge'/'facts').glob('*.yaml')):
        obj=read(path);validate_record(obj,'fact');result.append((path,obj))
    return result

def scope_for(project,market,release):
    return {'project':project,'market':market,'release':release}

def resolve(workspace,key,scope):
    if not KEY.fullmatch(key):raise ValueError('invalid key')
    matches=[]
    for path,fact in facts(workspace):
        sc=fact['scope']
        if fact['key']!=key or sc['project']!=scope['project'] or fact['status']=='superseded':continue
        if any(sc.get(k) not in (None,scope[k]) for k in ('market','release')):continue
        matches.append((path,fact))
    if not matches:return {'found':False,'key':key}
    # Project-wide facts apply broadly; explicitly scoped facts win.
    score=lambda pair:sum(pair[1]['scope'].get(k) is not None for k in ('market','release'))
    max_score=max(map(score,matches))
    matches=[m for m in matches if score(m)==max_score]
    if len(matches)!=1:raise ValueError('ambiguous facts with same key/scope: manual review required')
    path,fact=matches[0]
    return {'found':True,'file':str(path),'fact':fact}

def write(workspace,obj,path,action):
    validate_record(obj,'fact')
    path.write_text(yaml.safe_dump(obj,sort_keys=False,allow_unicode=True),encoding='utf-8')
    event={'at':datetime.now(timezone.utc).isoformat(),'action':action,'fact_id':obj['id'],'key':obj['key'],'revision':obj['revision'],'source_ref':obj['source']['ref'],'affected_ids':obj.get('affects',[])}
    with (workspace/'history'/'events.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')

def put(workspace,args,project):
    if not KEY.fullmatch(args.key):raise ValueError('invalid canonical key')
    target=scope_for(project,args.market,args.release)
    matches=[(p,f) for p,f in facts(workspace) if f['key']==args.key and f['scope']==target and f['status']!='superseded']
    if len(matches)>1:raise ValueError('duplicate records for the same scope')
    source={'type':'user' if args.status=='confirmed' else 'agent','ref':args.source_ref}
    if matches:
        path,obj=matches[0]
        if obj['value']==args.value:
            print(json.dumps({'unchanged':True,'fact_id':obj['id']}));return
        if not args.override or args.status!='confirmed':
            raise ValueError('different value already recorded; user correction requires --override --status confirmed')
        obj['history'].append({'revision':obj['revision'],'value':obj['value'],'source':obj['source']})
        obj.update(value=args.value,status='confirmed',revision=obj['revision']+1,source=source)
        action='explicit_user_override'
    else:
        used=[int(f['id'].split('-')[1]) for _,f in facts(workspace)]
        newid='FACT-%03d'%(max(used,default=0)+1)
        obj={'id':newid,'key':args.key,'value':args.value,'status':args.status,
             'scope':target,'revision':1,'source':source,'history':[]}
        path=workspace/'knowledge'/'facts'/f'{newid}.yaml'
        action='created'
    write(workspace,obj,path,action)
    print(json.dumps({'action':action,'fact':obj,'review_required':obj.get('affects',[])},indent=2))

def validate_workspace(workspace):
    identities=set();count=0
    for _,fact in facts(workspace):
        identity=(fact['key'],json.dumps(fact['scope'],sort_keys=True))
        if identity in identities and fact['status']!='superseded':raise ValueError(f'duplicate fact scope: {identity}')
        if fact['status']!='superseded':identities.add(identity)
        count+=1
    for group,kind in [('questions','question'),('hypotheses','hypothesis'),('experiments','experiment'),('decisions','decision')]:
        for path in (workspace/'knowledge'/group).glob('*.yaml'):
            validate_record(read(path),kind);count+=1
    validate_record(read(workspace/'state'/'workflow.yaml'),'workflow')
    print(f'PASS: {count} YAML records and workflow are structurally valid')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--workspace',type=Path,required=True)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('status');sub.add_parser('validate')
    r=sub.add_parser('resolve');r.add_argument('key')
    put_parser=sub.add_parser('put')
    put_parser.add_argument('--key',required=True);put_parser.add_argument('--value',required=True)
    put_parser.add_argument('--source-ref',required=True)
    put_parser.add_argument('--status',choices=('confirmed','proposed','hypothesis','observed'),required=True)
    put_parser.add_argument('--override',action='store_true')
    for x in (r,put_parser):
        x.add_argument('--market');x.add_argument('--release');x.add_argument('--project')
    args=p.parse_args()
    w=args.workspace.resolve()
    if not (w/'project.yaml').is_file():p.error('invalid workspace: run new_project.py first')
    project=getattr(args,'project',None) or read(w/'project.yaml')['project']
    if args.command=='status':
        print(json.dumps({'workflow':read(w/'state'/'workflow.yaml'),'checkpoint':read(w/'state'/'checkpoint.yaml')},indent=2))
    elif args.command=='validate':validate_workspace(w)
    elif args.command=='resolve':print(json.dumps(resolve(w,args.key,scope_for(project,args.market,args.release)),indent=2))
    else:put(w,args,project)

if __name__=='__main__':main()

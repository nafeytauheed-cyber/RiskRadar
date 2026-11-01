"""Explicit local administrative CLI. Never outputs API secrets."""
import argparse
import hashlib
import os
from psycopg.types.json import Jsonb
from ml.artifact import load
from ml.causal import digest
from .db import connect, migrate
from .service import audit


def register(path):
    a=load(path); key=digest(a)
    with connect() as c:
        c.execute('INSERT INTO model_versions(model_id,artifact) VALUES (%s,%s) ON CONFLICT DO NOTHING',(key,Jsonb(a)))
    return key


def promote(tenant,model_id):
    with connect() as c:
        row=c.execute('SELECT artifact FROM model_versions WHERE model_id=%s',(model_id,)).fetchone()
        if not row: raise ValueError('unknown model')
        from ml.artifact import validate
        validate(row['artifact'],model_id)
        previous=c.execute('SELECT active_model FROM tenants WHERE tenant_id=%s FOR UPDATE',(tenant,)).fetchone()
        if not previous: raise ValueError('unknown tenant')
        c.execute('UPDATE tenants SET active_model=%s WHERE tenant_id=%s',(model_id,tenant))
        audit(c,tenant,'admin-cli','model.promote',{'previous':previous['active_model'],'next':model_id})


def bootstrap(tenant,equipment,lifecycle,key):
    if len(key)<32: raise ValueError('API key must have at least 32 characters')
    with connect() as c:
        c.execute('INSERT INTO tenants(tenant_id) VALUES (%s) ON CONFLICT DO NOTHING',(tenant,))
        c.execute('INSERT INTO equipment(tenant_id,equipment_id,lifecycle_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(tenant,equipment,lifecycle))
        c.execute("INSERT INTO api_keys(key_hash,tenant_id,role) VALUES (%s,%s,'admin') ON CONFLICT DO NOTHING",(hashlib.sha256(key.encode()).hexdigest(),tenant))
        audit(c,tenant,'admin-cli','bootstrap',{'equipment_id':equipment})

if __name__=='__main__':
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('migrate')
    b=sub.add_parser('bootstrap'); b.add_argument('--tenant',required=True); b.add_argument('--equipment',required=True); b.add_argument('--lifecycle',default='original')
    r=sub.add_parser('register'); r.add_argument('path')
    t=sub.add_parser('promote'); t.add_argument('--tenant',required=True); t.add_argument('--model',required=True)
    args=p.parse_args()
    if args.command=='migrate': migrate()
    elif args.command=='bootstrap': bootstrap(args.tenant,args.equipment,args.lifecycle,os.environ['RISKRADAR_API_KEY'])
    elif args.command=='register': print(register(args.path))
    else: promote(args.tenant,args.model)

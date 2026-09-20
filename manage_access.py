"""Owner-only local administration. No public admin HTTP endpoint."""
import argparse
import json
import os
import sqlite3
from access_store import AccessStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=os.getenv('ACCESS_DB','data/access.sqlite3'))
    commands = parser.add_subparsers(dest='command',required=True)
    add = commands.add_parser('add');add.add_argument('name');add.add_argument('--limit',type=int,default=600)
    revoke = commands.add_parser('revoke');revoke.add_argument('name')
    commands.add_parser('list')
    args = parser.parse_args()
    store = AccessStore(args.db)
    try:
        if args.command=='add':
            code = store.add(args.name,args.limit)
            print('Código nuevo (se muestra solo ahora; entrégalo en privado):')
            print(code)
        elif args.command=='revoke':
            print('Acceso revocado.' if store.revoke(args.name) else 'No existe ese usuario.')
        else: print(json.dumps(store.report(),ensure_ascii=False,indent=2))
        return 0
    except (ValueError,sqlite3.IntegrityError):
        print('Nombre duplicado o datos inválidos. Usa un nombre nuevo para emitir otro código.')
        return 1


if __name__=='__main__': raise SystemExit(main())

"""Reassemble the reviewed desktop ZIP during a Render build, verify SHA256."""
import hashlib
import json
from pathlib import Path

def assemble(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    manifest=root/'client-manifest.json'
    if not manifest.is_file():
        print('No desktop package included; portal will show administrator instructions.')
        return None
    spec=json.loads(manifest.read_text(encoding='utf-8'))
    paths=[]
    for i,name in enumerate(spec['parts'],1):
        if name!=f'client.part{i:02}':raise ValueError('Unexpected client part name')
        paths.append(root/name)
    output=root/'downloads';output.mkdir(exist_ok=True)
    temporary=output/'StudyPilotC.tmp'
    digest=hashlib.sha256()
    with temporary.open('wb') as target:
        for path in paths:
            with path.open('rb') as source:
                while chunk:=source.read(1024*1024):target.write(chunk);digest.update(chunk)
    if digest.hexdigest()!=spec['sha256']:raise ValueError('Desktop archive verification failed')
    destination=output/'StudyPilotC.zip';temporary.replace(destination)
    print('Desktop package verified and ready to download.')
    return destination

if __name__=='__main__':assemble()

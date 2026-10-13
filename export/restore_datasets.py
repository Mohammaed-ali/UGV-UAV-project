#!/usr/bin/env python3
"""Restore exported dataset archive parts, or verify every archive member hash."""
import argparse, csv, hashlib, json, subprocess, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', help='Restore/verify one dataset directory; default: all')
    p.add_argument('--verify-only', action='store_true', help='Verify compressed archives and every member without writing datasets')
    p.add_argument('--overwrite', action='store_true', help='Replace existing dataset files after verification')
    args = p.parse_args()
    rows = list(csv.DictReader((ROOT / 'export/file-inventory.tsv').open(), delimiter='\t'))
    groups = {}
    for row in rows:
        if row['disposition'] != 'archived':
            continue
        member = Path(row['archive_member'])
        if args.dataset and (len(member.parts) < 2 or member.parts[1] != args.dataset):
            continue
        groups.setdefault(row['export_path'], {})[row['archive_member']] = row
    manifest = {a['path']: a for a in json.loads((ROOT / 'export/archives.json').read_text())}
    count = 0
    for relative, expected in sorted(groups.items()):
        archive = ROOT / relative
        with archive.open('rb') as f:
            if digest(f) != manifest[relative]['sha256']:
                raise RuntimeError('Archive checksum mismatch or Git LFS pointer: ' + relative)
        process = subprocess.Popen(['zstd', '-d', '--quiet', '-c', str(archive)], stdout=subprocess.PIPE)
        seen = set()
        with tarfile.open(fileobj=process.stdout, mode='r|') as tf:
            for member in tf:
                row = expected.get(member.name)
                if row is None:
                    raise RuntimeError('Unexpected archive member: ' + member.name)
                seen.add(member.name)
                path = Path(member.name)
                target = ROOT / path
                if path.is_absolute() or '..' in path.parts or not target.resolve().is_relative_to(ROOT):
                    raise RuntimeError('Unsafe archive member: ' + member.name)
                if member.isfile():
                    stream = tf.extractfile(member)
                    if args.verify_only:
                        actual = digest(stream)
                    else:
                        if target.exists() and not args.overwrite:
                            with target.open('rb') as f:
                                if digest(f) != row['sha256']:
                                    raise RuntimeError('Existing file differs; use --overwrite: ' + member.name)
                            actual = digest(stream)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            temp = target.with_name(target.name + '.export-partial')
                            h = hashlib.sha256()
                            with temp.open('wb') as f:
                                for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                                    h.update(block); f.write(block)
                            actual = h.hexdigest()
                            if actual == row['sha256']:
                                temp.chmod(member.mode); temp.replace(target)
                            else:
                                temp.unlink(missing_ok=True)
                    if actual != row['sha256']:
                        raise RuntimeError('Member checksum mismatch: ' + member.name)
                elif member.issym():
                    if hashlib.sha256(member.linkname.encode()).hexdigest() != row['sha256']:
                        raise RuntimeError('Symlink checksum mismatch: ' + member.name)
                    if not args.verify_only:
                        link = (target.parent / member.linkname).resolve()
                        if not link.is_relative_to(ROOT):
                            raise RuntimeError('Unsafe symlink target: ' + member.name)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if target.exists() or target.is_symlink():
                            if not args.overwrite and target.is_symlink() and str(target.readlink()) == member.linkname:
                                continue
                            if not args.overwrite:
                                raise RuntimeError('Existing symlink differs: ' + member.name)
                            target.unlink()
                        target.symlink_to(member.linkname)
                else:
                    raise RuntimeError('Unsupported archive member type: ' + member.name)
                count += 1
        process.stdout.close()
        if process.wait() or seen != set(expected):
            raise RuntimeError('Incomplete archive: ' + relative)
        print(('VERIFIED' if args.verify_only else 'RESTORED'), relative, len(seen), flush=True)
    if not groups:
        raise SystemExit('No matching dataset archives found')
    print('PASS:', count, 'dataset files verified')

if __name__ == '__main__':
    main()

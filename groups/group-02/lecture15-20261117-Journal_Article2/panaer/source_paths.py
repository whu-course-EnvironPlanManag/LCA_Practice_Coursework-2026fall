"""Locate original course data independently of checkout depth and working directory."""
from pathlib import Path, PurePosixPath
import argparse
import json

COURSE = Path('starter_materials') / 'lecture15-20261117-Journal_Article2' / 'source_data'

class CourseSources:
    def __init__(self, submission, source_data=None, legacy_sources=None):
        self.submission = Path(submission).resolve()
        records = json.loads((self.submission/'data/source_index.json').read_text(encoding='utf-8-sig'))
        extra = json.loads((self.submission/'data/production_2022_source.json').read_text(encoding='utf-8-sig'))
        records.append({'local':'production_2022.csv', 'path':extra['path']})
        self.paths = {}
        for row in records:
            if '/source_data/' in row['path']:
                self.paths[row['local']] = Path(*PurePosixPath(row['path'].split('/source_data/',1)[1]).parts)
        self.legacy = Path(legacy_sources).expanduser().resolve() if legacy_sources else None
        if self.legacy:
            if not self.legacy.is_dir(): raise FileNotFoundError(f'Legacy sources missing: {self.legacy}')
            self.root = self.legacy
        elif source_data:
            self.root = Path(source_data).expanduser().resolve()
            if not self.root.is_dir(): raise FileNotFoundError(f'--source-data directory missing: {self.root}')
        else:
            self.root = next((p/COURSE for p in self.submission.parents if (p/COURSE).is_dir()), None)
            if self.root is None:
                raise FileNotFoundError('Cannot find course source_data above this script. Place the submission inside the course checkout, or pass --source-data PATH. For the previous numbered download cache only, pass --legacy-sources PATH. No files were generated.')

    def file(self, key):
        path = self.root/key if self.legacy else self.root/self.paths[key]
        if not path.is_file(): raise FileNotFoundError(f'Missing original course input: {path}')
        return path

    def require(self, keys):
        for key in keys: self.file(key)

def configure(script, keys):
    parser = argparse.ArgumentParser(description='Rebuild cleaned inputs from original course materials')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--source-data', type=Path, help='Course source_data directory; otherwise auto-discover checkout')
    group.add_argument('--legacy-sources', type=Path, help='Explicit opt-in to previous numbered local download cache')
    parser.add_argument('--output-dir', type=Path, help='Alternative cleaned-data output directory')
    args = parser.parse_args()
    base = Path(script).resolve().parent
    sources = CourseSources(base, args.source_data, args.legacy_sources)
    sources.require(keys)  # Fail before creating or overwriting cleaned files.
    output = args.output_dir.resolve() if args.output_dir else base/'data'
    output.mkdir(parents=True, exist_ok=True)
    print('Original data:', sources.root)
    print('Cleaned output:', output)
    return sources, output

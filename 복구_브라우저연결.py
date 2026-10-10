#!/usr/bin/env python3
"""Fix the stale browser runtime executable path without changing other settings.

Usage: python3 복구_브라우저연결.py --check
       python3 복구_브라우저연결.py --apply
Requires Python 3.11+. This script does not stop apps or change browser data.
"""
from pathlib import Path
import argparse
import copy
import datetime
import json
import os
import re
import shutil
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent
TARGET = Path('/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex')
CONFIGS = [
    Path('/Users/yaco/.codex/config.toml'),
    Path('/Users/yaco/Library/Application Support/orca/codex-accounts/6c70115b-9de0-437f-9d8b-45161a3299f2/home/config.toml'),
]
OLD = '/Applications/ChatGPT.app/Contents/Resources/codex'


def prepare(raw):
    before = tomllib.loads(raw)
    current = before['mcp_servers']['node_repl']['env']['CODEX_CLI_PATH']
    if current == str(TARGET):
        return raw, False
    if current != OLD:
        raise ValueError(f'예상과 다른 실행 경로입니다. 자동 수정하지 않습니다: {current}')
    match = re.search(r'(?m)^\[mcp_servers\.node_repl\.env\][ \t]*\r?$', raw)
    if not match:
        raise ValueError('대상 환경 설정 표를 찾지 못했습니다.')
    next_table = re.search(r'(?m)^\[', raw[match.end():])
    end = match.end() + next_table.start() if next_table else len(raw)
    section = raw[match.end():end]
    updated, count = re.subn(
        r'(?m)^(CODEX_CLI_PATH[ \t]*=[ \t]*)[\"\'][^\"\'\r\n]*[\"\']([ \t]*\r?)$',
        lambda m: m.group(1) + json.dumps(str(TARGET)) + m.group(2), section,
    )
    if count != 1:
        raise ValueError(f'대상 경로 항목 수가 예상과 다릅니다: {count}')
    result = raw[:match.end()] + updated + raw[end:]
    expected = copy.deepcopy(before)
    expected['mcp_servers']['node_repl']['env']['CODEX_CLI_PATH'] = str(TARGET)
    if tomllib.loads(result) != expected:
        raise ValueError('다른 설정이 변경되어 수정을 중단합니다.')
    return result, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='백업 후 실제 수정')
    parser.add_argument('--check', action='store_true', help='수정 예정 내용만 확인 (기본값)')
    args = parser.parse_args()
    if args.apply and args.check:
        parser.error('--apply와 --check 중 하나만 사용하세요.')
    if not TARGET.is_file() or not os.access(TARGET, os.X_OK):
        raise SystemExit(f'실제 실행 파일을 찾지 못했습니다: {TARGET}')
    pending = []
    for path in CONFIGS:
        raw = path.read_text(encoding='utf-8')
        updated, changed = prepare(raw)
        pending.append((path, raw, updated, changed))
        print(('수정 필요: ' if changed else '이미 정상: ') + str(path))
    print('올바른 실행 경로: ' + str(TARGET))
    if not args.apply:
        print('검사만 완료했습니다. 실제 수정은 --apply로 실행하세요.')
        return
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backups = ROOT / '.build' / 'browser-recovery' / ('config-backup-' + stamp)
    backups.mkdir(parents=True, exist_ok=False, mode=0o700)
    written = []
    try:
        for index, (path, raw, updated, changed) in enumerate(pending, 1):
            if not changed:
                continue
            backup = backups / f'config-{index}.toml'
            shutil.copy2(path, backup)
            os.chmod(backup, 0o600)
            fd, temp_name = tempfile.mkstemp(prefix='.browser-repair-', dir=path.parent)
            temp_path = Path(temp_name)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    stream.write(updated)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temp_path, path.stat().st_mode & 0o777)
                os.replace(temp_path, path)
            finally:
                temp_path.unlink(missing_ok=True)
            written.append((path, backup))
            actual = tomllib.loads(path.read_text(encoding='utf-8'))
            assert actual['mcp_servers']['node_repl']['env']['CODEX_CLI_PATH'] == str(TARGET)
            print('수정 완료: ' + str(path))
    except Exception:
        for path, backup in reversed(written):
            shutil.copy2(backup, path)
        raise
    print('백업 위치: ' + str(backups))
    print('Orca를 완전히 종료했다 다시 열어 연결 도구에 새 설정을 적용하세요.')


if __name__ == '__main__':
    main()

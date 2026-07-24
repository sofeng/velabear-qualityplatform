import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pymysql


SUPPORTED_CODE_EXTENSIONS = {
    '.py',
    '.js',
    '.jsx',
    '.ts',
    '.tsx',
    '.vue',
    '.java',
    '.go',
    '.php',
    '.rb',
    '.cs',
    '.c',
    '.cc',
    '.cpp',
    '.cxx',
    '.h',
    '.hpp',
    '.rs',
    '.sql',
}

DEFAULT_EXCLUDED_DIRS = {
    '.git',
    '.hg',
    '.svn',
    '.idea',
    '.vscode',
    'node_modules',
    'dist',
    'build',
    'target',
    '.next',
    '.nuxt',
    '.venv',
    'venv',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.docker-data',
    '.bundle_stage',
    '.release_out',
    '.cache',
    '.turbo',
    'coverage',
    'media',
    'static',
    'logs',
    'tmp',
    'temp',
}

LANGUAGE_BY_SUFFIX = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.vue': 'Vue',
    '.java': 'Java',
    '.go': 'Go',
    '.php': 'PHP',
    '.rb': 'Ruby',
    '.cs': 'C#',
    '.c': 'C',
    '.cc': 'C++',
    '.cpp': 'C++',
    '.cxx': 'C++',
    '.h': 'C/C++ Header',
    '.hpp': 'C++ Header',
    '.rs': 'Rust',
    '.sql': 'SQL',
}

READ_TABLE_PATTERN = re.compile(
    r'\b(?:from|join)\s+[`"\[]?([A-Za-z_][A-Za-z0-9_.$-]*)[`"\]]?',
    re.IGNORECASE,
)
WRITE_TABLE_PATTERN = re.compile(
    r'\b(?:insert\s+into|update|delete\s+from|truncate\s+table|merge\s+into)\s+[`"\[]?([A-Za-z_][A-Za-z0-9_.$-]*)[`"\]]?',
    re.IGNORECASE,
)
TABLE_NAME_STOPWORDS = {
    'db',
    'database',
    'schema',
    'table',
    'tables',
    'model',
    'models',
    'query',
    'record',
    'records',
}
FIELD_REF_PATTERN = re.compile(
    r'\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b'
)
API_LITERAL_PATTERN = re.compile(r'["\'`](/(?:api/)?[A-Za-z0-9_./{}?=&:%-]+/?)["\'`]')
API_PREFIXES = (
    'ai-development',
    'ai-products',
    'ai-rd-platform',
    'assistant',
    'auth',
    'core',
    'defects',
    'deployments',
    'executions',
    'knowledge',
    'projects',
    'quality-analysis',
    'requirement-analysis',
    'reviews',
    'testcases',
    'testsuites',
    'ui-automation',
    'users',
    'versions',
    'workflow',
)
GENERIC_CALL_PATTERN = re.compile(r'\b([A-Za-z_$][A-Za-z0-9_.$]*)\s*\(')


@dataclass
class CodeScanOptions:
    include_patterns: list = field(default_factory=list)
    exclude_patterns: list = field(default_factory=list)
    max_files: int = 5000
    max_symbols: int = 50000
    max_file_bytes: int = 768 * 1024
    enable_ctags: bool = True
    enable_semgrep: bool = True


def build_code_scan_options(config):
    return CodeScanOptions(
        include_patterns=list(getattr(config, 'include_patterns', None) or []),
        exclude_patterns=list(getattr(config, 'exclude_patterns', None) or []),
        max_files=safe_int(os.environ.get('TESTHUB_ASSET_SCAN_MAX_FILES'), 5000),
        max_symbols=safe_int(os.environ.get('TESTHUB_ASSET_SCAN_MAX_SYMBOLS'), 50000),
        max_file_bytes=safe_int(os.environ.get('TESTHUB_ASSET_SCAN_MAX_FILE_BYTES'), 768 * 1024),
        enable_ctags=parse_bool(os.environ.get('TESTHUB_ASSET_SCAN_ENABLE_CTAGS'), True),
        enable_semgrep=parse_bool(os.environ.get('TESTHUB_ASSET_SCAN_ENABLE_SEMGREP'), True),
    )


def scan_code_assets(repository_root, config):
    root = Path(repository_root).resolve()
    options = build_code_scan_options(config)
    code_root = (root / (getattr(config, 'code_root', '') or '.')).resolve()
    result = {
        'tool_status': inspect_toolchain(),
        'files': [],
        'symbols': [],
        'imports': [],
        'calls': [],
        'api_references': [],
        'table_references': [],
        'field_references': [],
        'semantic_findings': [],
        'summary': {},
        'warnings': [],
    }
    if not code_root.exists():
        result['warnings'].append(f'code root not found: {code_root}')
        result['summary'] = build_code_summary(result)
        return result

    files = discover_code_files(root, code_root, options)
    if len(files) >= options.max_files:
        result['warnings'].append(f'code file scan was limited to {options.max_files} files')

    ctags_symbols_by_file = {}
    if options.enable_ctags:
        ctags_symbols_by_file, ctags_warning = run_ctags(root, files, result['tool_status'])
        if ctags_warning:
            result['warnings'].append(ctags_warning)

    symbol_count = 0
    symbol_name_index = defaultdict(list)
    for file_path in files:
        rel_path = to_rel(root, file_path)
        text = read_text(file_path, max_bytes=options.max_file_bytes)
        if not text:
            continue
        language = infer_code_language(file_path)
        file_info = {
            'path': rel_path,
            'language': language,
            'size': safe_file_size(file_path),
            'line_count': text.count('\n') + 1,
            'api_refs': extract_api_references(text),
            'table_refs': extract_table_references(text),
            'field_refs': extract_field_references(text),
            'imports': extract_imports(text, language),
        }
        symbols = ctags_symbols_by_file.get(rel_path) or extract_lightweight_symbols(rel_path, text, language)
        normalized_symbols = []
        for symbol in symbols:
            if symbol_count >= options.max_symbols:
                result['warnings'].append(f'symbol scan was limited to {options.max_symbols} symbols')
                break
            normalized = normalize_symbol(rel_path, language, symbol)
            normalized_symbols.append(normalized)
            result['symbols'].append(normalized)
            symbol_name_index[normalized['name']].append(normalized)
            symbol_count += 1
        file_info['symbol_count'] = len(normalized_symbols)
        result['files'].append(file_info)
        for item in file_info['imports']:
            result['imports'].append({'file': rel_path, **item})
        for item in file_info['api_refs']:
            result['api_references'].append({'file': rel_path, **item})
        for item in file_info['table_refs']:
            result['table_references'].append({'file': rel_path, **item})
        for item in file_info['field_refs']:
            result['field_references'].append({'file': rel_path, **item})
        result['calls'].extend(extract_call_references(rel_path, text, language))

    resolve_call_targets(result['calls'], symbol_name_index)
    if options.enable_semgrep:
        semgrep_payload, warning = run_semgrep(root, code_root, result['tool_status'])
        result['semantic_findings'] = semgrep_payload
        if warning:
            result['warnings'].append(warning)
    result['summary'] = build_code_summary(result)
    return result


def scan_database_assets(config, schema_config):
    result = {
        'tool_status': inspect_toolchain(),
        'source': 'disabled',
        'database': None,
        'tables': [],
        'fields': [],
        'indexes': [],
        'foreign_keys': [],
        'summary': {},
        'warnings': [],
    }
    if not schema_config:
        result['summary'] = build_database_summary(result)
        return result

    schemacrawler_payload, warning = run_schemacrawler(config, schema_config, result['tool_status'])
    if schemacrawler_payload:
        result.update(schemacrawler_payload)
        result['source'] = 'schemacrawler'
    else:
        if warning:
            result['warnings'].append(warning)
        information_schema_payload = scan_mysql_information_schema(config, schema_config)
        result.update(information_schema_payload)
        result['source'] = 'information_schema'
    result['summary'] = build_database_summary(result)
    return result


def inspect_toolchain():
    ctags_path = shutil.which(os.environ.get('CTAGS_COMMAND') or 'ctags')
    semgrep_path = shutil.which(os.environ.get('SEMGREP_COMMAND') or 'semgrep')
    schemacrawler_command = os.environ.get('SCHEMACRAWLER_COMMAND') or ''
    schemacrawler_jar = os.environ.get('SCHEMACRAWLER_JAR') or ''
    java_path = shutil.which(os.environ.get('JAVA_COMMAND') or 'java')
    return {
        'ctags': {
            'available': bool(ctags_path),
            'path': ctags_path or '',
            'version': get_command_version([ctags_path, '--version']) if ctags_path else '',
            'mode': 'universal-ctags-json' if ctags_path else 'internal-symbol-parser',
        },
        'semgrep': {
            'available': bool(semgrep_path),
            'path': semgrep_path or '',
            'version': get_command_version([semgrep_path, '--version']) if semgrep_path else '',
            'mode': 'semgrep-json' if semgrep_path else 'internal-reference-parser',
        },
        'schemacrawler': {
            'available': bool(schemacrawler_command or (schemacrawler_jar and java_path)),
            'path': schemacrawler_command or schemacrawler_jar,
            'version': '',
            'mode': 'schemacrawler-json' if schemacrawler_command or schemacrawler_jar else 'information-schema',
        },
        'java': {
            'available': bool(java_path),
            'path': java_path or '',
            'version': get_command_version([java_path, '-version'], stderr=True) if java_path else '',
        },
        'internal': {
            'available': True,
            'mode': 'regex-parser',
        },
    }


def discover_code_files(root, code_root, options):
    files = []
    for current_dir, dirnames, filenames in os.walk(code_root):
        current_path = Path(current_dir)
        dirnames[:] = [
            dirname
            for dirname in sorted(dirnames)
            if dirname not in DEFAULT_EXCLUDED_DIRS
            and not is_path_excluded(to_rel(root, current_path / dirname), options.exclude_patterns)
        ]
        for filename in sorted(filenames):
            if len(files) >= options.max_files:
                return files
            path = current_path / filename
            if is_generated_code_file(path):
                continue
            if path.suffix.lower() not in SUPPORTED_CODE_EXTENSIONS:
                continue
            rel_path = to_rel(root, path)
            if is_path_excluded(rel_path, options.exclude_patterns):
                continue
            if not is_path_included(rel_path, options.include_patterns):
                continue
            files.append(path)
    return files


def is_generated_code_file(path):
    name = Path(path).name.lower()
    if name.endswith(('.min.js', '.min.css')):
        return True
    if name in {'angular.js', 'angular.min.js', 'jquery.js', 'jquery.min.js'}:
        return True
    return False


def run_ctags(root, files, tool_status):
    if not tool_status.get('ctags', {}).get('available') or not files:
        return {}, ''
    command = [
        tool_status['ctags']['path'],
        '--output-format=json',
        '--fields=+nKSt',
        '--extras=+q',
        '-f',
        '-',
        *[str(path) for path in files],
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=safe_int(os.environ.get('TESTHUB_CTAGS_TIMEOUT'), 120),
        )
    except Exception as exc:
        return {}, f'ctags execution failed: {exc}'
    if completed.returncode != 0:
        return {}, f'ctags returned {completed.returncode}: {(completed.stderr or completed.stdout)[:500]}'
    by_file = defaultdict(list)
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        rel_path = to_rel(root, item.get('path') or item.get('input') or '')
        name = item.get('name') or ''
        if not rel_path or not name:
            continue
        kind = normalize_ctags_kind(item.get('kind') or item.get('kindName') or '')
        if kind not in {'class', 'function', 'method'}:
            continue
        by_file[rel_path].append({
            'type': kind,
            'name': name,
            'line': safe_int(item.get('line'), 0),
            'scope': item.get('scope') or '',
            'signature': item.get('signature') or '',
            'tool': 'ctags',
        })
    return dict(by_file), ''


def run_semgrep(root, code_root, tool_status):
    if not tool_status.get('semgrep', {}).get('available'):
        return [], ''
    command = [
        tool_status['semgrep']['path'],
        'scan',
        '--config',
        os.environ.get('TESTHUB_SEMGREP_CONFIG') or 'auto',
        '--json',
        '--metrics',
        'off',
        '--disable-version-check',
        '--timeout',
        str(safe_int(os.environ.get('TESTHUB_SEMGREP_RULE_TIMEOUT'), 15)),
        str(code_root),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=safe_int(os.environ.get('TESTHUB_SEMGREP_TIMEOUT'), 180),
        )
    except Exception as exc:
        return [], f'semgrep execution failed: {exc}'
    if completed.returncode not in {0, 1}:
        return [], f'semgrep returned {completed.returncode}: {(completed.stderr or completed.stdout)[:500]}'
    try:
        payload = json.loads(completed.stdout or '{}')
    except Exception as exc:
        return [], f'semgrep json parse failed: {exc}'
    findings = []
    for item in payload.get('results') or []:
        findings.append({
            'file': to_rel(root, item.get('path') or ''),
            'line': (item.get('start') or {}).get('line'),
            'rule_id': item.get('check_id') or '',
            'message': ((item.get('extra') or {}).get('message') or '')[:500],
            'severity': ((item.get('extra') or {}).get('severity') or '').lower(),
            'metadata': (item.get('extra') or {}).get('metadata') or {},
        })
    return findings[:1000], ''


def run_schemacrawler(config, schema_config, tool_status):
    command_text = os.environ.get('SCHEMACRAWLER_COMMAND') or ''
    jar_path = os.environ.get('SCHEMACRAWLER_JAR') or ''
    java_path = tool_status.get('java', {}).get('path') or shutil.which('java')
    if not command_text and not (jar_path and java_path):
        return None, 'SchemaCrawler is not configured; falling back to information_schema.'
    with tempfile.TemporaryDirectory(prefix='testhub-schemacrawler-') as temp_dir:
        output_file = Path(temp_dir) / 'schema.json'
        if command_text:
            command = [
                *split_command(command_text),
                '--server=mysql',
                f'--host={schema_config["host"]}',
                f'--port={schema_config["port"] or "3306"}',
                f'--database={schema_config["name"]}',
                f'--schemas={schema_config.get("schema") or schema_config["name"]}',
                f'--user={schema_config["user"]}',
                f'--password={schema_config["password"]}',
                '--info-level=standard',
                '--command=schema',
                '--output-format=json',
                f'--output-file={output_file}',
            ]
        else:
            command = [
                java_path,
                '-jar',
                jar_path,
                '--server=mysql',
                f'--host={schema_config["host"]}',
                f'--port={schema_config["port"] or "3306"}',
                f'--database={schema_config["name"]}',
                f'--schemas={schema_config.get("schema") or schema_config["name"]}',
                f'--user={schema_config["user"]}',
                f'--password={schema_config["password"]}',
                '--info-level=standard',
                '--command=schema',
                '--output-format=json',
                f'--output-file={output_file}',
            ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=safe_int(os.environ.get('TESTHUB_SCHEMACRAWLER_TIMEOUT'), 240),
            )
        except Exception as exc:
            return None, f'SchemaCrawler execution failed: {exc}'
        if completed.returncode != 0 or not output_file.exists():
            return None, f'SchemaCrawler returned {completed.returncode}: {(completed.stderr or completed.stdout)[:500]}'
        try:
            payload = json.loads(output_file.read_text(encoding='utf-8', errors='ignore'))
        except Exception as exc:
            return None, f'SchemaCrawler json parse failed: {exc}'
    return normalize_schemacrawler_payload(payload, schema_config), ''


def scan_mysql_information_schema(config, schema_config):
    schema_name = schema_config.get('schema') or schema_config['name']
    payload = {
        'database': {
            'engine': schema_config['engine'],
            'name': schema_config['name'],
            'schema': schema_name,
            'source_ref': schema_name,
        },
        'tables': [],
        'fields': [],
        'indexes': [],
        'foreign_keys': [],
    }
    connection = pymysql.connect(
        host=schema_config['host'],
        port=int(schema_config['port'] or 3306),
        user=schema_config['user'],
        password=schema_config['password'],
        database=schema_config['name'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=8,
        read_timeout=60,
        write_timeout=60,
    )
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_NAME, TABLE_COMMENT, TABLE_ROWS, TABLE_TYPE, ENGINE
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
                """,
                [schema_name],
            )
            table_rows = cursor.fetchall()
            table_names = [
                row['TABLE_NAME']
                for row in table_rows
                if is_name_allowed_by_patterns(
                    row.get('TABLE_NAME'),
                    getattr(config, 'database_include_patterns', None),
                    getattr(config, 'database_exclude_patterns', None),
                )
            ]
            if not table_names:
                return payload
            placeholders = ','.join(['%s'] * len(table_names))
            cursor.execute(
                f"""
                SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, DATA_TYPE, IS_NULLABLE,
                       COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT, ORDINAL_POSITION
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """,
                [schema_name, *table_names],
            )
            column_rows = cursor.fetchall()
            cursor.execute(
                f"""
                SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, COLUMN_NAME, SEQ_IN_INDEX, INDEX_TYPE
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})
                ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
                """,
                [schema_name, *table_names],
            )
            index_rows = cursor.fetchall()
            cursor.execute(
                f"""
                SELECT kcu.CONSTRAINT_NAME,
                       kcu.TABLE_NAME,
                       kcu.COLUMN_NAME,
                       kcu.REFERENCED_TABLE_NAME,
                       kcu.REFERENCED_COLUMN_NAME,
                       rc.UPDATE_RULE,
                       rc.DELETE_RULE
                FROM information_schema.KEY_COLUMN_USAGE kcu
                LEFT JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
                 AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                WHERE kcu.TABLE_SCHEMA = %s
                  AND kcu.TABLE_NAME IN ({placeholders})
                  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
                """,
                [schema_name, *table_names],
            )
            fk_rows = cursor.fetchall()
    table_by_name = {row['TABLE_NAME']: row for row in table_rows}
    for table_name in table_names:
        row = table_by_name.get(table_name) or {}
        payload['tables'].append({
            'name': table_name,
            'schema': schema_name,
            'comment': row.get('TABLE_COMMENT') or '',
            'row_estimate': row.get('TABLE_ROWS') or 0,
            'table_type': row.get('TABLE_TYPE') or '',
            'engine': row.get('ENGINE') or '',
        })
    for row in column_rows:
        payload['fields'].append({
            'table': row['TABLE_NAME'],
            'name': row['COLUMN_NAME'],
            'column_type': row.get('COLUMN_TYPE') or '',
            'data_type': row.get('DATA_TYPE') or '',
            'nullable': row.get('IS_NULLABLE') or '',
            'column_key': row.get('COLUMN_KEY') or '',
            'default': row.get('COLUMN_DEFAULT'),
            'extra': row.get('EXTRA') or '',
            'comment': row.get('COLUMN_COMMENT') or '',
            'ordinal': row.get('ORDINAL_POSITION') or 0,
        })
    index_map = defaultdict(lambda: {'columns': []})
    for row in index_rows:
        key = (row['TABLE_NAME'], row['INDEX_NAME'])
        item = index_map[key]
        item.update({
            'table': row['TABLE_NAME'],
            'name': row['INDEX_NAME'],
            'unique': not bool(row.get('NON_UNIQUE')),
            'index_type': row.get('INDEX_TYPE') or '',
        })
        item['columns'].append(row['COLUMN_NAME'])
    payload['indexes'] = list(index_map.values())
    for row in fk_rows:
        payload['foreign_keys'].append({
            'name': row.get('CONSTRAINT_NAME') or '',
            'table': row.get('TABLE_NAME') or '',
            'column': row.get('COLUMN_NAME') or '',
            'referenced_table': row.get('REFERENCED_TABLE_NAME') or '',
            'referenced_column': row.get('REFERENCED_COLUMN_NAME') or '',
            'update_rule': row.get('UPDATE_RULE') or '',
            'delete_rule': row.get('DELETE_RULE') or '',
        })
    return payload


def normalize_schemacrawler_payload(payload, schema_config):
    # SchemaCrawler JSON shape may vary by version; normalize the common catalog/schema/table
    # structure and let information_schema remain the guaranteed fallback.
    normalized = {
        'database': {
            'engine': schema_config['engine'],
            'name': schema_config['name'],
            'schema': schema_config.get('schema') or schema_config['name'],
            'source_ref': schema_config.get('schema') or schema_config['name'],
        },
        'tables': [],
        'fields': [],
        'indexes': [],
        'foreign_keys': [],
    }
    tables = []
    for catalog in payload.get('catalogs') or payload.get('schemas') or []:
        schemas = catalog.get('schemas') if isinstance(catalog, dict) else []
        if schemas is None:
            schemas = [catalog]
        for schema in schemas:
            if not isinstance(schema, dict):
                continue
            tables.extend(schema.get('tables') or [])
    if not tables and isinstance(payload.get('tables'), list):
        tables = payload['tables']
    for table in tables:
        table_name = table.get('name') or table.get('fullName') or ''
        if not table_name:
            continue
        table_name = table_name.split('.')[-1]
        normalized['tables'].append({
            'name': table_name,
            'schema': normalized['database']['schema'],
            'comment': table.get('remarks') or table.get('comment') or '',
            'row_estimate': table.get('rowCount') or 0,
            'table_type': table.get('tableType') or table.get('type') or '',
            'engine': '',
        })
        for column in table.get('columns') or []:
            normalized['fields'].append({
                'table': table_name,
                'name': column.get('name') or '',
                'column_type': column.get('columnDataType') or column.get('type') or '',
                'data_type': column.get('type') or '',
                'nullable': str(column.get('nullable', '')),
                'column_key': 'PRI' if column.get('partOfPrimaryKey') else '',
                'default': column.get('defaultValue'),
                'extra': '',
                'comment': column.get('remarks') or '',
                'ordinal': column.get('ordinalPosition') or 0,
            })
        for index in table.get('indexes') or []:
            normalized['indexes'].append({
                'table': table_name,
                'name': index.get('name') or '',
                'unique': bool(index.get('unique')),
                'index_type': index.get('type') or '',
                'columns': [
                    col.get('name') if isinstance(col, dict) else str(col)
                    for col in index.get('columns') or []
                ],
            })
    return normalized


def extract_lightweight_symbols(rel_path, text, language, max_symbols_per_file=120):
    patterns = []
    if language == 'Python':
        patterns = [
            ('class', r'^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b'),
            ('function', r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('),
        ]
    elif language in {'JavaScript', 'TypeScript', 'Vue'}:
        patterns = [
            ('class', r'\bclass\s+([A-Za-z_$][A-Za-z0-9_$]*)\b'),
            ('function', r'\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\('),
            ('function', r'\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'),
            ('function', r'\bconst\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:computed|ref|reactive|watch|onMounted)\b'),
        ]
    elif language == 'Java':
        patterns = [
            ('class', r'\b(?:class|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b'),
            ('method', r'\b(?:public|private|protected|static|final|\s)+[\w<>\[\], ?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('),
        ]
    elif language == 'Go':
        patterns = [('function', r'\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(')]
    elif language == 'PHP':
        patterns = [
            ('class', r'\b(?:class|interface|trait)\s+([A-Za-z_][A-Za-z0-9_]*)\b'),
            ('function', r'\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('),
        ]
    elif language == 'SQL':
        patterns = [('function', r'\b(?:CREATE|ALTER)\s+(?:PROCEDURE|FUNCTION|VIEW)\s+([A-Za-z_][A-Za-z0-9_.]*)\b')]
    symbols = []
    seen = set()
    for symbol_type, pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            name = match.group(1)
            if not name:
                continue
            identity = (symbol_type, name, match.start())
            if identity in seen:
                continue
            seen.add(identity)
            symbols.append({
                'type': symbol_type,
                'name': name,
                'line': text.count('\n', 0, match.start()) + 1,
                'file': rel_path,
                'tool': 'internal',
            })
            if len(symbols) >= max_symbols_per_file:
                return symbols
    return symbols


def extract_imports(text, language):
    imports = []
    if language == 'Python':
        for match in re.finditer(r'^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.,\s]+))', text, re.MULTILINE):
            module = match.group(1) or match.group(2) or ''
            for item in module.split(','):
                name = item.strip().split()[0] if item.strip() else ''
                if name:
                    imports.append({'module': name, 'line': text.count('\n', 0, match.start()) + 1})
    elif language in {'JavaScript', 'TypeScript', 'Vue'}:
        for match in re.finditer(r'\bfrom\s+["\']([^"\']+)["\']|\brequire\(\s*["\']([^"\']+)["\']\s*\)', text):
            module = match.group(1) or match.group(2) or ''
            if module:
                imports.append({'module': module, 'line': text.count('\n', 0, match.start()) + 1})
    elif language == 'Java':
        for match in re.finditer(r'^\s*import\s+([A-Za-z0-9_.*]+)\s*;', text, re.MULTILINE):
            imports.append({'module': match.group(1), 'line': text.count('\n', 0, match.start()) + 1})
    elif language == 'Go':
        for match in re.finditer(r'^\s*import\s+(?:\(\s*)?["`]([^"`]+)["`]', text, re.MULTILINE):
            imports.append({'module': match.group(1), 'line': text.count('\n', 0, match.start()) + 1})
    return imports[:200]


def extract_api_references(text):
    refs = []
    seen = set()
    for match in API_LITERAL_PATTERN.finditer(text):
        value = normalize_api_ref(match.group(1))
        if value and value not in seen:
            seen.add(value)
            refs.append({'api_path': value, 'line': text.count('\n', 0, match.start()) + 1})
    return refs[:200]


def extract_table_references(text):
    refs = []
    seen = set()
    for mode, pattern in [('reads', READ_TABLE_PATTERN), ('writes', WRITE_TABLE_PATTERN)]:
        for match in pattern.finditer(text):
            table = normalize_table_name(match.group(1))
            if not table:
                continue
            identity = (mode, table)
            if identity in seen:
                continue
            seen.add(identity)
            refs.append({'table': table, 'mode': mode, 'line': text.count('\n', 0, match.start()) + 1})
    return refs[:300]


def extract_field_references(text):
    refs = []
    seen = set()
    for match in FIELD_REF_PATTERN.finditer(text):
        table_alias, field = match.groups()
        if table_alias in {'this', 'self', 'console', 'window', 'document', 'Math', 'Date'}:
            continue
        identity = (table_alias, field)
        if identity in seen:
            continue
        seen.add(identity)
        refs.append({
            'table_or_alias': table_alias,
            'field': field,
            'line': text.count('\n', 0, match.start()) + 1,
        })
    return refs[:300]


def extract_call_references(rel_path, text, language):
    calls = []
    for match in GENERIC_CALL_PATTERN.finditer(text):
        name = match.group(1)
        if not name or name in {'if', 'for', 'while', 'switch', 'catch', 'function', 'return'}:
            continue
        simple_name = name.split('.')[-1]
        calls.append({
            'file': rel_path,
            'callee': simple_name,
            'raw': name,
            'line': text.count('\n', 0, match.start()) + 1,
            'language': language,
            'confidence': 'name-match',
        })
    return calls[:1000]


def resolve_call_targets(calls, symbol_name_index):
    for call in calls:
        candidates = symbol_name_index.get(call.get('callee') or '') or []
        if candidates:
            call['target_key'] = candidates[0]['key']
            call['target_file'] = candidates[0]['file']


def normalize_symbol(rel_path, language, symbol):
    object_type = symbol.get('type') or normalize_ctags_kind(symbol.get('kind') or '')
    name = str(symbol.get('name') or '').strip()
    line = safe_int(symbol.get('line'), 0)
    scope = str(symbol.get('scope') or '').strip()
    key = f'{object_type}:{rel_path}:{scope + "." if scope else ""}{name}:{line or ""}'
    return {
        'key': key,
        'type': object_type,
        'name': name,
        'file': rel_path,
        'line': line,
        'scope': scope,
        'signature': symbol.get('signature') or '',
        'language': language,
        'tool': symbol.get('tool') or 'internal',
    }


def build_code_summary(result):
    language_counts = Counter(item['language'] for item in result.get('files') or [])
    return {
        'file_count': len(result.get('files') or []),
        'symbol_count': len(result.get('symbols') or []),
        'import_count': len(result.get('imports') or []),
        'call_count': len(result.get('calls') or []),
        'api_reference_count': len(result.get('api_references') or []),
        'table_reference_count': len(result.get('table_references') or []),
        'field_reference_count': len(result.get('field_references') or []),
        'semantic_finding_count': len(result.get('semantic_findings') or []),
        'language_counts': dict(language_counts),
    }


def build_database_summary(result):
    return {
        'database': (result.get('database') or {}).get('name') or '',
        'schema': (result.get('database') or {}).get('schema') or '',
        'source': result.get('source') or '',
        'table_count': len(result.get('tables') or []),
        'field_count': len(result.get('fields') or []),
        'index_count': len(result.get('indexes') or []),
        'foreign_key_count': len(result.get('foreign_keys') or []),
    }


def infer_code_language(path):
    return LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower(), Path(path).suffix.lower().lstrip('.').upper() or 'Text')


def normalize_ctags_kind(kind):
    value = str(kind or '').strip().lower()
    if value in {'class', 'interface', 'enum', 'struct', 'trait'}:
        return 'class'
    if value in {'method', 'member'}:
        return 'method'
    if value in {'function', 'func', 'procedure', 'subroutine'}:
        return 'function'
    return value


def normalize_api_ref(value):
    text = str(value or '').strip()
    if not text.startswith('/'):
        return ''
    text = text.split('#')[0]
    if text.startswith('/api/'):
        pass
    else:
        first_segment = text.strip('/').split('/', 1)[0]
        if first_segment not in API_PREFIXES:
            return ''
        text = f'/api{text}'
    return text if text.endswith('/') else f'{text}/'


def normalize_table_name(value):
    text = str(value or '').strip().strip('`"[]')
    if not text:
        return ''
    text = text.split('.')[-1].strip('`"[]')
    if not text or text.lower() in TABLE_NAME_STOPWORDS:
        return ''
    if len(text) < 3:
        return ''
    return text.lower()


def is_path_included(rel_path, include_patterns=None):
    patterns = [str(item or '').strip() for item in include_patterns or [] if str(item or '').strip()]
    if not patterns:
        return True
    return any(match_path_pattern(rel_path, pattern) for pattern in patterns)


def is_path_excluded(rel_path, exclude_patterns=None):
    return any(match_path_pattern(rel_path, str(pattern or '').strip()) for pattern in exclude_patterns or [])


def match_path_pattern(path, pattern):
    if not pattern:
        return False
    normalized = str(path or '').replace('\\', '/')
    normalized_pattern = pattern.replace('\\', '/').strip()
    if normalized_pattern in normalized:
        return True
    regex = '^' + re.escape(normalized_pattern).replace('\\*', '.*') + '$'
    return re.search(regex, normalized, re.IGNORECASE) is not None


def is_name_allowed_by_patterns(name, include_patterns=None, exclude_patterns=None):
    normalized = str(name or '').strip()
    if not normalized:
        return False
    include = [compile_name_pattern(item) for item in include_patterns or [] if str(item or '').strip()]
    exclude = [compile_name_pattern(item) for item in exclude_patterns or [] if str(item or '').strip()]
    if include and not any(pattern.search(normalized) for pattern in include):
        return False
    if exclude and any(pattern.search(normalized) for pattern in exclude):
        return False
    return True


def compile_name_pattern(value):
    text = str(value or '').strip()
    return re.compile('^' + re.escape(text).replace('\\*', '.*') + '$', re.IGNORECASE)


def to_rel(root, path):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace('\\', '/')
    except Exception:
        return str(path or '').replace('\\', '/')


def read_text(path, max_bytes):
    try:
        raw = Path(path).read_bytes()[:max_bytes]
        return raw.decode('utf-8', errors='ignore')
    except Exception:
        return ''


def safe_file_size(path):
    try:
        return Path(path).stat().st_size
    except Exception:
        return 0


def safe_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def parse_bool(value, default=False):
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    return default


def get_command_version(command, stderr=False):
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5)
        output = completed.stderr if stderr else completed.stdout
        return (output or completed.stdout or completed.stderr or '').splitlines()[0][:200]
    except Exception:
        return ''


def split_command(command):
    return [part for part in re.split(r'\s+', str(command or '').strip()) if part]

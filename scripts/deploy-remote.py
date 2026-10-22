"""Static blog deployment transaction; compatible with the host's Python 3.6."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote
import uuid

BASE = Path('/etc/www/hiwz')
MAIN = Path('/etc/nginx/nginx.conf')
SITE = Path('/etc/nginx/conf.d/hiwz.conf')
OLD = Path('/etc/www/hi-note')
REDIRECTS = {
    '/about.html': '/posts/java-basics/',
    '/article.html': '/posts/spring-basics/',
    '/tutirial.html': '/posts/spring-mvc-annotations/',
    '/archive.html': '/posts/mybatis-basics/',
}
LEGACY_SERVERS = [r'''
server {
    listen 443 ssl;
    server_name _;
    ssl_certificate /root/ssl/hiwz.net/fullchain.pem;
    ssl_certificate_key /root/ssl/hiwz.net/key.pem;
    ssl_session_timeout 5m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:HIGH:!aNULL:!MD5:!RC4:!DHE;
    ssl_prefer_server_ciphers on;
    error_page 404 /404.html;
    location = /404.html {}
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {}
    location ~ ^/(.git|LICENSE|README.md) { return 404; }
    location / { root /etc/www/hi-note; index index.html index.htm; }
}
''', 'server { listen 80; server_name _; return 301 https://$host$request_uri; }']
TOKEN = re.compile(r'''\#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[{};]|[^\s{};\#]+''')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def tokens(text):
    return [match for match in TOKEN.finditer(text) if not match.group().startswith('#')]


def remove_legacy_servers(text):
    """Only remove the two inspected server blocks; reject configuration drift."""
    stack, header, spans = [], [], []
    for token in tokens(text):
        value = token.group()
        if value == '{':
            require(bool(header), 'Nginx 块语法不受支持')
            stack.append((header, header[0].start()))
            header = []
        elif value == '}':
            require(bool(stack), 'Nginx 括号不匹配')
            block, start = stack.pop()
            if [part.group() for part in block] == ['server'] and stack and stack[-1][0][0].group() == 'http':
                spans.append((start, token.end()))
            header = []
        elif value == ';':
            header = []
        else:
            header.append(token)
    require(not stack, 'Nginx 括号不匹配')
    actual = sorted(tuple(t.group() for t in tokens(text[a:b])) for a, b in spans)
    expected = sorted(tuple(t.group() for t in tokens(s)) for s in LEGACY_SERVERS)
    require(actual == expected, 'Nginx 站点配置与已检查版本不同，停止自动接入，请先重新核对配置')
    require('include /etc/nginx/conf.d/*.conf;' in text, '缺少 conf.d 的 include')
    for start, end in reversed(spans):
        text = text[:start] + text[end:]
    return text


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def write(path, data, mode=0o644):
    if isinstance(data, str):
        data = data.encode('utf-8')
    fd, name = tempfile.mkstemp(prefix='.deploy-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(name, mode)
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save_json(path, data):
    write(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n', 0o600)


def point_to(target):
    current = BASE / 'current'
    require(not current.exists() or current.is_symlink(), 'current 必须是软链接')
    if target is None:
        if current.is_symlink():
            current.unlink()
        return
    temporary = BASE / ('.current-' + uuid.uuid4().hex)
    try:
        temporary.symlink_to(target)
        os.replace(str(temporary), str(current))
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def command(*args):
    subprocess.check_call(args)


def preflight(mode):
    require(os.geteuid() == 0, '当前脚本需要通过 root 的 SSH 连接部署')
    for tool in ('nginx', 'systemctl', 'curl', 'tar', 'sha256sum'):
        require(shutil.which(tool), '服务器缺少命令：' + tool)
    require(not BASE.is_symlink(), '部署根目录不能是软链接')
    if (BASE / 'pending.json').exists():
        print('检测到未完成的切换，将在取得部署锁后先恢复。', flush=True)
        return
    state = read_json(BASE / 'state.json')
    if mode == 'init':
        require(state is None and not (BASE / 'current').is_symlink(), '已接入部署，请使用 npm run deploy')
        require(not list(SITE.parent.glob('*.conf')), 'conf.d 已存在站点配置，需要先核对，停止自动接入')
        remove_legacy_servers(MAIN.read_text(encoding='utf-8'))
        require((OLD / 'index.html').is_file(), '旧站首页不存在')
    else:
        require(state is not None, '尚未接入，请首次使用 npm run deploy -- --init')
        require((BASE / 'current').is_symlink(), '缺少 current 软链接')
        require(os.readlink(str(BASE / 'current')) == state['current'], 'current 与发布记录不一致')
        require(SITE.is_file() and digest(SITE.read_bytes()) == state['site_hash'], '站点 Nginx 配置已改变，请先核对')
        require(digest(MAIN.read_bytes()) == state['main_hash'], '主 Nginx 配置已改变，请先核对')
    command('nginx', '-t')


def snapshot(identifier, change_config, state):
    backup = BASE / 'backups' / identifier
    if change_config:
        backup.mkdir(parents=True)
        shutil.copy2(str(MAIN), str(backup / 'nginx.conf'))
        if SITE.exists():
            shutil.copy2(str(SITE), str(backup / 'site.conf'))
    journal = {
        'backup': str(backup), 'change_config': change_config,
        'site_existed': SITE.exists(), 'state': state,
        'current': os.readlink(str(BASE / 'current')) if (BASE / 'current').is_symlink() else None,
    }
    save_json(BASE / 'pending.json', journal)
    return journal


def restore(journal):
    point_to(journal['current'])
    if journal['change_config']:
        backup = Path(journal['backup'])
        write(MAIN, (backup / 'nginx.conf').read_bytes(), (backup / 'nginx.conf').stat().st_mode & 0o777)
        if journal['site_existed']:
            write(SITE, (backup / 'site.conf').read_bytes())
        elif SITE.exists():
            SITE.unlink()
        command('nginx', '-t')
        command('systemctl', 'reload', 'nginx')
    if journal['state'] is None:
        if (BASE / 'state.json').exists():
            (BASE / 'state.json').unlink()
    else:
        save_json(BASE / 'state.json', journal['state'])
    (BASE / 'pending.json').unlink()


def prepare_release(source, identifier):
    required = ['index.html', '404.html', 'about/index.html', 'rss.xml', 'sitemap.xml', 'search-index.json']
    for name in required:
        require((source / name).is_file(), '缺少构建产物：' + name)
    for path in source.rglob('*'):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()), '构建产物包含非普通文件：' + str(path))
    release = BASE / 'releases' / identifier
    release.parent.mkdir(exist_ok=True)
    shutil.copytree(str(source), str(release))
    for path in [release] + list(release.rglob('*')):
        os.chmod(str(path), 0o755 if path.is_dir() else 0o644)
    write(release / 'deployment-version.txt', identifier + '\n')
    shared = BASE / 'shared' / '_astro'
    shared.mkdir(parents=True, exist_ok=True)
    for asset in (release / '_astro').rglob('*'):
        if asset.is_file():
            target = shared / asset.relative_to(release / '_astro')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                require(target.read_bytes() == asset.read_bytes(), '相同资源路径内容不同：' + str(target))
            else:
                write(target, asset.read_bytes())
    return release


def fetch(url, origin=True):
    with tempfile.TemporaryDirectory(prefix='hiwz-check-') as temporary:
        body = Path(temporary) / 'body'
        headers = Path(temporary) / 'headers'
        args = ['curl', '--silent', '--show-error', '--connect-timeout', '5', '--max-time', '15',
                '--noproxy', '*', '--output', str(body), '--dump-header', str(headers), '--write-out', '%{http_code}']
        if origin:
            for domain in ('hiwz.net', 'www.hiwz.net'):
                for port in (80, 443):
                    args += ['--resolve', '{}:{}:127.0.0.1'.format(domain, port)]
        status = subprocess.check_output(args + [url]).decode('ascii')
        fields = {}
        for line in headers.read_text(encoding='iso-8859-1').splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                fields[key.lower()] = value.strip()
        return int(status), fields, body.read_bytes()


def verify(release, legacy=False):
    domain = 'https://www.hiwz.net'
    if legacy:
        for path in ('/index.html', '/about.html'):
            status, _, body = fetch(domain + path)
            require(status == 200 and body == (OLD / path[1:]).read_bytes(), '旧站回退验收失败：' + path)
        return
    # Compare served content, not just HTTP 200, to catch wrong roots or error-page fallbacks.
    for file in sorted(release.rglob('*')):
        if not file.is_file():
            continue
        path = '/' + file.relative_to(release).as_posix()
        if path in REDIRECTS or path == '/404.html':
            continue
        if path.endswith('/index.html'):
            path = path[:-10]
        status, headers, body = fetch(domain + quote(path))
        require(status == 200 and body == file.read_bytes(), '页面或资源验收失败：' + path)
        if path.startswith('/_astro/'):
            require('immutable' in headers.get('cache-control', ''), '哈希资源缓存配置不正确')
    for old, new in REDIRECTS.items():
        status, headers, _ = fetch(domain + old)
        require(status == 301 and headers.get('location') == domain + new, '旧地址跳转错误：' + old)
    status, _, body = fetch(domain + '/__hiwz_missing_' + uuid.uuid4().hex)
    require(status == 404 and body == (release / '404.html').read_bytes(), '404 页面或状态码错误')
    for prefix in ('http://hiwz.net', 'http://www.hiwz.net', 'https://hiwz.net'):
        path = '/about/?deploy-check=1'
        status, headers, _ = fetch(prefix + path)
        require(status == 301 and headers.get('location') == domain + path, '域名或 HTTPS 跳转错误：' + prefix)
    for path in ('/index.html', '/deployment-version.txt'):
        status, _, body = fetch(domain + path, origin=False)
        require(status == 200 and body == (release / path[1:]).read_bytes(), '公网域名验收失败：' + path)


def interrupted(signum, frame):
    raise RuntimeError('收到中断信号 {}'.format(signum))


def verify_with_retry(release, legacy):
    # Reload gracefully retires old workers; allow their connections to drain.
    for attempt in range(3):
        try:
            verify(release, legacy)
            return
        except (RuntimeError, subprocess.CalledProcessError):
            if attempt == 2:
                raise
            time.sleep(1)


def publish(mode, identifier):
    require(re.fullmatch(r'[A-Za-z0-9-]{10,80}', identifier), '版本标识不合法')
    os.umask(0o022)
    BASE.mkdir(mode=0o755, parents=True, exist_ok=True)
    with (BASE / '.deploy.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('另一个部署正在进行，请稍后再试')
        pending = read_json(BASE / 'pending.json')
        if pending:
            restore(pending)
            raise RuntimeError('已恢复上次中断前的版本；请重新运行发布命令')
        preflight(mode)
        state = read_json(BASE / 'state.json')
        legacy = mode == 'rollback' and state['previous'] is None
        change_config = mode == 'init' or legacy
        candidate = None
        if mode == 'init':
            candidate = remove_legacy_servers(MAIN.read_text(encoding='utf-8'))
        elif not legacy:
            require(SITE.read_bytes() == Path('scripts/nginx-site.conf').read_bytes(), '本地 Nginx 模板已改变，需单独审查配置变更')
        if mode == 'rollback':
            release = OLD if legacy else BASE / state['previous']
            require(release.is_dir(), '上一版本目录不存在')
        else:
            release = prepare_release(Path('dist'), identifier)
        journal = snapshot(identifier, change_config, state)
        for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            signal.signal(signum, interrupted)
        try:
            if legacy:
                original = Path(state['initial_backup']) / 'nginx.conf'
                write(MAIN, original.read_bytes(), original.stat().st_mode & 0o777)
                SITE.unlink()
                point_to(None)
            else:
                point_to(str(release.relative_to(BASE)))
                if mode == 'init':
                    write(SITE, Path('scripts/nginx-site.conf').read_bytes())
                    write(MAIN, candidate, MAIN.stat().st_mode & 0o777)
            if change_config:
                command('nginx', '-t')
                command('systemctl', 'reload', 'nginx')
            verify_with_retry(release, legacy)
            if legacy:
                (BASE / 'state.json').unlink()
            else:
                save_json(BASE / 'state.json', {
                    'current': str(release.relative_to(BASE)),
                    'previous': state['current'] if state else None,
                    'initial_backup': state['initial_backup'] if state else journal['backup'],
                    'main_hash': digest(MAIN.read_bytes()), 'site_hash': digest(SITE.read_bytes()),
                })
            (BASE / 'pending.json').unlink()
            print('验收通过，当前站点：' + str(release), flush=True)
        except BaseException:
            # Ignore repeated disconnect signals while restoring the recorded state.
            for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
                signal.signal(signum, signal.SIG_IGN)
            print('发布验收未完成，正在恢复原版本……', flush=True)
            restore(journal)
            print('已恢复原版本。', flush=True)
            raise


if __name__ == '__main__':
    try:
        if len(sys.argv) == 3 and sys.argv[1] == '--preflight':
            require(sys.argv[2] in ('init', 'deploy', 'rollback'), '模式不合法')
            preflight(sys.argv[2])
        else:
            require(len(sys.argv) == 3 and sys.argv[1] in ('init', 'deploy', 'rollback'), '参数不正确')
            publish(sys.argv[1], sys.argv[2])
    except Exception as error:
        print('部署失败：' + str(error), file=sys.stderr)
        sys.exit(1)

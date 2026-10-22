import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash, randomBytes } from 'node:crypto';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const host = 'root@hiwz.net';
const site = 'https://www.hiwz.net';
const sshOptions = ['-4', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
  '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3'];
const flags = new Set(process.argv.slice(2));
const allowed = ['--init', '--dry-run', '--rollback', '--help'];
const quote = (value) => `'${value.replaceAll("'", "'\\''")}'`;

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, stdio: 'inherit', ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} 执行失败（${result.status ?? result.signal}）`);
}

function main() {
  if ([...flags].some((flag) => !allowed.includes(flag)) || (flags.has('--init') && flags.has('--rollback'))) {
    throw new Error('参数不正确；运行 npm run deploy -- --help 查看用法。');
  }
  if (flags.has('--help')) {
    console.log(`npm run deploy                   检查、构建并发布\n\
npm run deploy -- --dry-run       本地完整检查，不连接服务器\n\
npm run deploy -- --init          首次发布，同时备份并接入 Nginx\n\
npm run deploy -- --rollback      切回上一个版本\n\n\
服务器：${host}\n网站：${site}\n目录：/etc/www/hiwz\n\
首次接入保留旧站 /etc/www/hi-note；所有命令均使用现有 SSH 密钥。`);
    return;
  }

  const rollback = flags.has('--rollback');
  const mode = rollback ? 'rollback' : flags.has('--init') ? 'init' : 'deploy';
  console.log(`目标：${host} /etc/www/hiwz；网站：${site}；模式：${mode}`);
  if (!rollback) {
    const env = { ...process.env, SITE_URL: site };
    run('npm', ['run', 'check'], { env });
    run('npm', ['run', 'build'], { env });
    run('npm', ['test'], { env });
    // Server code must also compile with Python 3.6, the version on the current host.
    run('python3', ['-c', "import ast; ast.parse(open('scripts/deploy-remote.py', encoding='utf-8').read(), feature_version=(3, 6))"]);
  }
  if (flags.has('--dry-run')) {
    console.log(`本地验证完成。正式执行将${rollback ? '回退到上一版本' : '上传 dist/、切换版本并验收'}${mode === 'init' ? '，并备份、调整 Nginx' : ''}。未连接或修改服务器。`);
    return;
  }

  const id = new Date().toISOString().replace(/[-:.]/g, '') + '-' + randomBytes(4).toString('hex');
  const temp = mkdtempSync(join(tmpdir(), 'hiwz-deploy-'));
  const archive = join(temp, 'bundle.tar.gz');
  const remoteArchive = `/tmp/hiwz-deploy-${id}.tar.gz`;
  try {
    // Refuse a wrong mode or changed Nginx configuration before uploading anything.
    run('ssh', [...sshOptions, host, `PYTHONIOENCODING=utf-8 python3 - --preflight ${mode}`], {
      input: readFileSync(join(root, 'scripts/deploy-remote.py')),
      stdio: ['pipe', 'inherit', 'inherit'],
    });
    run('tar', ['-czf', archive, '--exclude=.DS_Store', '--exclude=._*',
      'scripts/deploy-remote.py', 'scripts/nginx-site.conf', ...(rollback ? [] : ['dist'])], {
      env: { ...process.env, COPYFILE_DISABLE: '1' },
    });
    const checksum = createHash('sha256').update(readFileSync(archive)).digest('hex');
    run('scp', [...sshOptions, archive, `${host}:${remoteArchive}`]);
    const shell = `set -eu
archive=${quote(remoteArchive)}
work=$(mktemp -d /tmp/hiwz-publish.XXXXXXXX)
trap 'rm -rf "$work"; rm -f "$archive"' EXIT
printf '%s  %s\\n' ${quote(checksum)} "$archive" | sha256sum -c -
tar -xzf "$archive" -C "$work"
cd "$work"
PYTHONIOENCODING=utf-8 python3 scripts/deploy-remote.py ${mode} ${quote(id)}
`;
    run('ssh', [...sshOptions, host, 'bash -s'], { input: shell, stdio: ['pipe', 'inherit', 'inherit'] });
    console.log(`完成：${site}`);
  } finally {
    rmSync(temp, { recursive: true, force: true });
    // Also remove a partial SCP upload when the transfer or remote command failed.
    spawnSync('ssh', [...sshOptions, host, `rm -f -- ${quote(remoteArchive)}`], { stdio: 'ignore', timeout: 20000 });
  }
}

try { main(); } catch (error) {
  console.error(`\n部署未完成：${error.message}`);
  console.error('如 SSH 中断，不能仅凭本地退出状态判断发布结果；再次执行时服务器会检查并恢复未完成的切换。');
  process.exitCode = 1;
}

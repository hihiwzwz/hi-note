"""Exercise deployment against temporary directories, never the real server."""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('deploy_remote', ROOT / 'scripts/deploy-remote.py')
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for key, path in {'BASE': 'www/hiwz', 'MAIN': 'nginx/nginx.conf',
                          'SITE': 'nginx/conf.d/hiwz.conf', 'OLD': 'www/hi-note'}.items():
            self.enter_patch(patch.object(deploy, key, self.root / path))
        deploy.SITE.parent.mkdir(parents=True)
        deploy.OLD.mkdir(parents=True)
        (deploy.OLD / 'index.html').write_text('old home')
        (deploy.OLD / 'about.html').write_text('old java')
        self.original = 'events {}\nhttp {\ninclude /etc/nginx/conf.d/*.conf;\n' + '\n'.join(deploy.LEGACY_SERVERS) + '\n}'
        deploy.MAIN.write_text(self.original)
        (self.root / 'scripts').mkdir()
        shutil.copyfile(str(ROOT / 'scripts/nginx-site.conf'), str(self.root / 'scripts/nginx-site.conf'))
        self.dist = self.root / 'dist'
        for name in ('index.html', '404.html', 'about/index.html', 'rss.xml', 'sitemap.xml',
                     'search-index.json', '_astro/test.abc.css'):
            file = self.dist / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('content ' + name)
        previous_cwd = os.getcwd()
        os.chdir(str(self.root))
        self.addCleanup(os.chdir, previous_cwd)
        self.enter_patch(patch.object(deploy.os, 'geteuid', return_value=0))
        self.enter_patch(patch.object(deploy.shutil, 'which', return_value='/usr/bin/tool'))
        self.enter_patch(patch.object(deploy.signal, 'signal'))
        self.enter_patch(patch.object(deploy.time, 'sleep'))
        self.commands = self.enter_patch(patch.object(deploy, 'command'))
        self.verify = self.enter_patch(patch.object(deploy, 'verify'))

    def enter_patch(self, context):
        result = context.start()
        self.addCleanup(context.stop)
        return result

    def test_config_preserves_global_directives_and_rejects_drift(self):
        candidate = deploy.remove_legacy_servers(self.original.replace('http {', 'http { # comment\n sendfile on;'))
        self.assertIn('sendfile on;', candidate)
        self.assertIn('include /etc/nginx/conf.d/*.conf;', candidate)
        self.assertNotIn('server {', candidate)
        with self.assertRaisesRegex(RuntimeError, '不同'):
            deploy.remove_legacy_servers(self.original.replace('index.htm', 'another.htm'))

    def test_successful_publish_and_rollback(self):
        deploy.publish('init', 'release-000001')
        backup = deploy.BASE / 'backups' / 'release-000001' / 'nginx.conf'
        self.assertEqual(backup.read_text(), self.original)
        self.assertEqual(os.readlink(str(deploy.BASE / 'current')), 'releases/release-000001')
        self.assertEqual((deploy.OLD / 'index.html').read_text(), 'old home')
        (self.dist / 'index.html').write_text('new home')
        (self.dist / '_astro/test.def.css').write_text('new style')
        deploy.publish('deploy', 'release-000002')
        self.assertEqual(sorted(p.name for p in (deploy.BASE / 'backups').iterdir()), ['release-000001'])
        deploy.publish('rollback', 'rollback-000003')
        self.assertEqual(sorted(p.name for p in (deploy.BASE / 'backups').iterdir()), ['release-000001'])
        self.assertEqual(backup.read_text(), self.original)
        self.assertEqual((deploy.BASE / 'current/index.html').read_text(), 'content index.html')
        self.assertTrue((deploy.BASE / 'shared/_astro/test.def.css').is_file())
        self.assertEqual(deploy.read_json(deploy.BASE / 'state.json')['previous'], 'releases/release-000002')
        self.assertFalse((deploy.BASE / 'pending.json').exists())

    def test_first_release_can_return_to_legacy_site(self):
        deploy.publish('init', 'release-000001')
        active_main = deploy.MAIN.read_bytes()
        active_site = deploy.SITE.read_bytes()
        deploy.publish('rollback', 'rollback-000002')
        backup = deploy.BASE / 'backups' / 'rollback-000002'
        self.assertEqual((backup / 'nginx.conf').read_bytes(), active_main)
        self.assertEqual((backup / 'site.conf').read_bytes(), active_site)
        self.assertEqual(deploy.MAIN.read_text(), self.original)
        self.assertFalse(deploy.SITE.exists())
        self.assertFalse((deploy.BASE / 'current').is_symlink())
        self.assertFalse((deploy.BASE / 'state.json').exists())

    def test_failed_initial_check_restores_original_nginx(self):
        self.verify.side_effect = RuntimeError('simulated failed HTTP check')
        with self.assertRaisesRegex(RuntimeError, 'HTTP'):
            deploy.publish('init', 'release-000001')
        self.assertEqual(deploy.MAIN.read_text(), self.original)
        self.assertFalse(deploy.SITE.exists())
        self.assertFalse((deploy.BASE / 'current').is_symlink())
        self.assertFalse((deploy.BASE / 'state.json').exists())
        self.assertFalse((deploy.BASE / 'pending.json').exists())

    def test_failed_update_restores_previous_release(self):
        deploy.publish('init', 'release-000001')
        state = (deploy.BASE / 'state.json').read_bytes()
        self.verify.side_effect = RuntimeError('simulated failed HTTP check')
        with self.assertRaisesRegex(RuntimeError, 'HTTP'):
            deploy.publish('deploy', 'release-000002')
        self.assertEqual((deploy.BASE / 'state.json').read_bytes(), state)
        self.assertEqual(os.readlink(str(deploy.BASE / 'current')), 'releases/release-000001')

    def test_nginx_reload_failure_restores_configuration(self):
        reloads = []

        def fail_first_reload(*args):
            if args == ('systemctl', 'reload', 'nginx'):
                reloads.append(args)
                if len(reloads) == 1:
                    raise RuntimeError('simulated reload failure')

        self.commands.side_effect = fail_first_reload
        with self.assertRaisesRegex(RuntimeError, 'reload failure'):
            deploy.publish('init', 'release-000001')
        self.assertEqual(len(reloads), 2)
        self.assertEqual(deploy.MAIN.read_text(), self.original)
        self.assertFalse(deploy.SITE.exists())
        self.assertFalse((deploy.BASE / 'pending.json').exists())

    def test_failed_restore_keeps_recovery_journal(self):
        self.verify.side_effect = RuntimeError('simulated HTTP failure')
        reloads = []

        def fail_restore_reload(*args):
            if args == ('systemctl', 'reload', 'nginx'):
                reloads.append(args)
                if len(reloads) > 1:
                    raise RuntimeError('simulated recovery failure')

        self.commands.side_effect = fail_restore_reload
        with self.assertRaisesRegex(RuntimeError, 'recovery failure'):
            deploy.publish('init', 'release-000001')
        self.assertTrue((deploy.BASE / 'pending.json').exists())
        self.commands.side_effect = None
        with self.assertRaisesRegex(RuntimeError, '已恢复上次中断'):
            deploy.publish('init', 'release-000002')
        self.assertEqual(deploy.MAIN.read_text(), self.original)
        self.assertFalse((deploy.BASE / 'pending.json').exists())

    def test_interrupted_transaction_recovers_before_another_deploy(self):
        deploy.publish('init', 'release-000001')
        state = deploy.read_json(deploy.BASE / 'state.json')
        deploy.snapshot('interrupted-000002', False, state)
        deploy.point_to('releases/missing')
        with self.assertRaisesRegex(RuntimeError, '已恢复上次中断'):
            deploy.publish('deploy', 'release-000003')
        self.assertEqual(os.readlink(str(deploy.BASE / 'current')), state['current'])
        self.assertFalse((deploy.BASE / 'pending.json').exists())

    def test_symlink_and_asset_collision_are_rejected(self):
        deploy.BASE.mkdir(parents=True)
        (self.dist / 'unsafe').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(RuntimeError, '非普通文件'):
            deploy.prepare_release(self.dist, 'release-000001')
        (self.dist / 'unsafe').unlink()
        deploy.prepare_release(self.dist, 'release-000002')
        (self.dist / '_astro/test.abc.css').write_text('changed without a new hash')
        with self.assertRaisesRegex(RuntimeError, '内容不同'):
            deploy.prepare_release(self.dist, 'release-000003')

    def test_concurrent_publish_is_rejected(self):
        deploy.BASE.mkdir(parents=True)
        with (deploy.BASE / '.deploy.lock').open('a') as lock:
            deploy.fcntl.flock(lock, deploy.fcntl.LOCK_EX | deploy.fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, '另一个部署'):
                deploy.publish('init', 'release-000001')


if __name__ == '__main__':
    unittest.main()

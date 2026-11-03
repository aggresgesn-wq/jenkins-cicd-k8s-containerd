import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which('bash') or os.environ.get('BASH_EXE')


@unittest.skipUnless(BASH, 'Bash is required')
class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'bin').mkdir()
        (self.root / 'backups').mkdir()
        docs = list(yaml.safe_load_all((ROOT / 'deploy/k8s/mysql-backup-cronjob.yaml').read_text(encoding='utf-8')))
        container = docs[1]['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]
        (self.root / 'backup.sh').write_text(container['command'][2], encoding='utf-8', newline='\n')
        fake = self.root / 'bin/mysqldump'
        fake.write_text('#!/bin/sh\nprintf "CREATE TABLE example (id INT);\\n"\nexit "${DUMP_RC:-0}"\n', newline='\n')
        fake.chmod(0o755)

    def run_backup(self, **env):
        return subprocess.run([BASH, '-c', 'export PATH="$PWD/bin:$PATH"; export BACKUP_DIR="$PWD/backups"; bash backup.sh'],
                              cwd=self.root, env={**os.environ, 'MYSQL_ROOT_PASSWORD': 'test-only', **env},
                              capture_output=True, text=True, encoding='utf-8')

    def test_success_publishes_valid_archive_and_checksum(self):
        result = self.run_backup()
        self.assertEqual(result.returncode, 0, result.stderr)
        archive, = (self.root / 'backups').glob('*.sql.gz')
        self.assertIn(b'CREATE TABLE', gzip.decompress(archive.read_bytes()))
        checksum = Path(str(archive) + '.sha256').read_text().split()[0]
        self.assertEqual(checksum, hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertFalse(list((self.root / 'backups').glob('*.partial')))

    def test_failed_dump_cannot_publish_backup(self):
        self.assertNotEqual(self.run_backup(DUMP_RC='2').returncode, 0)
        self.assertEqual(list((self.root / 'backups').iterdir()), [])

    def test_failed_compression_cannot_publish_backup(self):
        fake = self.root / 'bin/gzip'
        fake.write_text('#!/bin/sh\nexit 3\n', newline='\n')
        fake.chmod(0o755)
        self.assertNotEqual(self.run_backup().returncode, 0)
        self.assertEqual(list((self.root / 'backups').iterdir()), [])


class ManifestPolicyTests(unittest.TestCase):
    def test_staging_capacity_and_maintenance_policy(self):
        doc = yaml.safe_load((ROOT / 'deploy/k8s/overlays/staging/kustomization.yaml').read_text(encoding='utf-8'))
        self.assertFalse(any(path.endswith('/hpa.yaml') for path in doc['resources']))
        self.assertEqual(doc['resources'], ['../../base'])
        deletion = next(p for p in doc['patches'] if p['target']['kind'] == 'HorizontalPodAutoscaler')
        self.assertEqual(yaml.safe_load(deletion['patch'])['$patch'], 'delete')
        self.assertEqual(doc['replicas'][0]['count'], 1)
        patch = next(p for p in doc['patches'] if p['target']['kind'] == 'PodDisruptionBudget')
        self.assertEqual(yaml.safe_load(patch['patch'])[0]['value'], 0)

    def test_release_cannot_create_pods_or_exec_or_read_secrets(self):
        docs = yaml.safe_load_all((ROOT / 'deploy/k8s/jenkins-release-rbac.yaml').read_text(encoding='utf-8'))
        roles = [d for d in docs if d['kind'] == 'Role']
        self.assertEqual({r['metadata']['namespace'] for r in roles}, {'webapp', 'webapp-staging'})
        for role in roles:
            for rule in role['rules']:
                self.assertNotIn('*', rule['verbs'])
                self.assertFalse({'secrets', 'pods/exec', '*'} & set(rule['resources']))
                if 'pods' in rule['resources']:
                    self.assertLessEqual(set(rule['verbs']), {'get', 'list', 'watch'})


if __name__ == '__main__':
    unittest.main()

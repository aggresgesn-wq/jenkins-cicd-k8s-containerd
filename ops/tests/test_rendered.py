import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
KUBECTL = os.environ.get('KUBECTL') or shutil.which('kubectl')


@unittest.skipUnless(KUBECTL, 'kubectl needed for real Kustomize rendering')
class RenderTests(unittest.TestCase):
    def render(self, environment):
        result = subprocess.run([KUBECTL, 'kustomize', str(ROOT / 'deploy/k8s/overlays' / environment)],
                                check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
        docs = list(yaml.safe_load_all(result.stdout))
        namespace = 'webapp-staging' if environment == 'staging' else 'webapp'
        self.assertFalse(any(d['kind'] == 'Namespace' for d in docs))
        self.assertTrue(all(d['metadata']['namespace'] == namespace for d in docs))
        return {d['kind']: d for d in docs}

    def test_staging_is_single_replica_without_autoscaler(self):
        resources = self.render('staging')
        self.assertNotIn('HorizontalPodAutoscaler', resources)
        self.assertEqual(resources['Deployment']['spec']['replicas'], 1)
        self.assertEqual(resources['PodDisruptionBudget']['spec']['minAvailable'], 0)

    def test_production_retains_availability_policy(self):
        resources = self.render('production')
        self.assertEqual(resources['Deployment']['spec']['replicas'], 2)
        self.assertEqual(resources['HorizontalPodAutoscaler']['spec']['minReplicas'], 2)
        self.assertEqual(resources['PodDisruptionBudget']['spec']['minAvailable'], 1)

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class FrameworkTest(unittest.TestCase):
    def run_py(self,tool,*args,success=True):
        result=subprocess.run([sys.executable,str(ROOT/'tools'/tool),*map(str,args)],capture_output=True,text=True)
        if success and result.returncode:self.fail(result.stderr+result.stdout)
        return result

    def test_contracts(self):
        self.run_py('vendor_skills.py','check')
        self.run_py('validate_framework.py')

    def test_scaffold_and_answer_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_py('new_project.py','--name','mvp','--output',tmp)
            ws=Path(tmp)/'mvp'
            base=['--workspace',ws]
            cmd=['put','--key','product.primary_problem','--value','Pain A','--status','confirmed','--source-ref','session-001']
            self.run_py('knowledge.py',*base,*cmd)
            self.run_py('knowledge.py',*base,*cmd)
            found=json.loads(self.run_py('knowledge.py',*base,'resolve','product.primary_problem').stdout)
            self.assertTrue(found['found'])
            self.assertEqual('Pain A',found['fact']['value'])
            self.assertEqual(1,found['fact']['revision'])
            denied=self.run_py('knowledge.py',*base,'put','--key','product.primary_problem','--value','Pain B','--status','confirmed','--source-ref','session-002',success=False)
            self.assertNotEqual(0,denied.returncode)
            self.run_py('knowledge.py',*base,'put','--key','product.primary_problem','--value','Pain B','--status','confirmed','--source-ref','session-002','--override')
            found=json.loads(self.run_py('knowledge.py',*base,'resolve','product.primary_problem').stdout)
            self.assertEqual(2,found['fact']['revision'])
            self.assertEqual('Pain A',found['fact']['history'][0]['value'])
            self.run_py('knowledge.py',*base,'validate')
            self.assertEqual(9,len(list((ws/'documents').glob('*.md'))))

    def test_no_cross_market_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_py('new_project.py','--name','startup','--output',tmp)
            ws=Path(tmp)/'startup';base=['--workspace',ws]
            self.run_py('knowledge.py',*base,'put','--key','pricing.currency','--value','USD','--market','US','--source-ref','research-001','--status','proposed')
            self.assertFalse(json.loads(self.run_py('knowledge.py',*base,'resolve','pricing.currency','--market','VN').stdout)['found'])
            self.assertTrue(json.loads(self.run_py('knowledge.py',*base,'resolve','pricing.currency','--market','US').stdout)['found'])

if __name__=='__main__':unittest.main()

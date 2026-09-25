import tempfile, unittest
from pathlib import Path
from src.repository import Repository
from src.service import Service
from src.rules import STATES, TRANSITION_ROLES
class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Repository(str(Path(self.tmp.name)/"test.db")); self.service=Service(self.repo)
    def tearDown(self): self.repo.close(); self.tmp.cleanup()
    def test_complete_workflow_and_audit(self):
        item=self.service.create_item({"title":"workflow item","description":"complete business flow","severity":'serious',"quantity":12,"threshold":6,"external_ref":"WF-1"},"creator",'reporter')
        self.assertEqual(item["status"],STATES[0])
        record=self.service.add_record(item["id"],{"kind":"action","detail":"install guard rail","external_ref":"EV-1"},"recorder",'investigator')
        self.assertEqual(record["status"],"pending_acceptance")
        acceptance=self.service.accept_record(item["id"],record["id"],{"note":"verified on site","owner":"zhangsan","acceptance_no":"ACC-WF-1"},"safety",'safety_manager')
        self.assertEqual(acceptance["valid"],1)
        current=self.service.get_item(item["id"],"viewer")
        for target in STATES[1:]:
            current=self.service.transition(current["id"],target,current["version"],"reviewer",TRANSITION_ROLES[target][0])
        self.assertEqual(current["status"],STATES[-1])
        records=self.service.list_records(current["id"],"viewer")
        self.assertEqual(records[0]["status"],"accepted"); self.assertEqual(records[0]["owner"],"zhangsan")
        forms=self.service.list_acceptances(current["id"],record["id"],"viewer")
        self.assertEqual(len(forms),1); self.assertEqual(forms[0]["acceptance_no"],"ACC-WF-1")
        events=self.service.audit("viewer",current["id"]); self.assertGreaterEqual(len(events),len(STATES)+2); self.assertTrue(self.repo.verify_audit_chain())
if __name__=="__main__": unittest.main()

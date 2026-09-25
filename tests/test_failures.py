import tempfile, unittest
from pathlib import Path
from src.domain import ConflictError, PermissionDenied, ValidationError
from src.repository import Repository
from src.service import Service
from src.rules import STATES, TRANSITION_ROLES
class FailureTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Repository(str(Path(self.tmp.name)/"test.db")); self.service=Service(self.repo)
        self.item=self.service.create_item({"title":"failure item","description":"failure scenarios","severity":'serious',"quantity":5,"threshold":10,"external_ref":"FAIL-1"},"creator",'reporter')
    def tearDown(self): self.repo.close(); self.tmp.cleanup()
    def _advance(self,item,targets):
        current=item
        for target in targets: current=self.service.transition(current["id"],target,current["version"],"reviewer",TRANSITION_ROLES[target][0])
        return current
    def test_permission_version_duplicate_and_invariant(self):
        with self.assertRaises(PermissionDenied): self.service.transition(self.item["id"],STATES[1],1,"attacker","viewer")
        with self.assertRaises(ConflictError): self.service.transition(self.item["id"],STATES[1],99,"reviewer",TRANSITION_ROLES[STATES[1]][0])
        payload={"kind":"action","detail":"same reference","external_ref":"DUP-1"}
        self.service.add_record(self.item["id"],payload,"recorder",'investigator')
        with self.assertRaises(ConflictError): self.service.add_record(self.item["id"],payload,"recorder",'investigator')
    def test_direct_close_rejected_and_unaccepted_blocked(self):
        with self.assertRaises(ValidationError): self.service.add_record(self.item["id"],{"kind":"action","detail":"self closed","status":"closed"},"recorder",'investigator')
        record=self.service.add_record(self.item["id"],{"kind":"action","detail":"pending measure"},"recorder",'investigator')
        self.assertEqual(record["status"],"pending_acceptance")
        current=self._advance(self.item,STATES[1:3])
        with self.assertRaises(ConflictError): self.service.transition(current["id"],"verification",current["version"],"reviewer",TRANSITION_ROLES["verification"][0])
        with self.assertRaises(PermissionDenied): self.service.accept_record(self.item["id"],record["id"],{"note":"n","owner":"o","acceptance_no":"ACC-F-1"},"recorder",'investigator')
        self.service.accept_record(self.item["id"],record["id"],{"note":"checked","owner":"owner1","acceptance_no":"ACC-F-1"},"safety",'safety_manager')
        with self.assertRaises(ConflictError): self.service.accept_record(self.item["id"],record["id"],{"note":"again","owner":"owner1","acceptance_no":"ACC-F-2"},"safety",'safety_manager')
    def test_duplicate_acceptance_no_and_reacceptance_after_edit(self):
        first=self.service.add_record(self.item["id"],{"kind":"action","detail":"first measure"},"recorder",'investigator')
        second=self.service.add_record(self.item["id"],{"kind":"action","detail":"second measure"},"recorder",'investigator')
        self.service.accept_record(self.item["id"],first["id"],{"note":"ok","owner":"owner1","acceptance_no":"ACC-D-1"},"safety",'safety_manager')
        with self.assertRaises(ConflictError): self.service.accept_record(self.item["id"],second["id"],{"note":"ok","owner":"owner2","acceptance_no":"ACC-D-1"},"safety",'safety_manager')
        self.service.accept_record(self.item["id"],second["id"],{"note":"ok","owner":"owner2","acceptance_no":"ACC-D-2"},"safety",'safety_manager')
        current=self._advance(self.item,STATES[1:4])
        updated=self.service.update_record(self.item["id"],first["id"],{"owner":"owner9"},"editor",'investigator')
        self.assertEqual(updated["status"],"pending_acceptance"); self.assertEqual(updated["owner"],"owner9")
        forms=self.service.list_acceptances(self.item["id"],first["id"],"viewer")
        self.assertEqual(len(forms),1); self.assertEqual(forms[0]["valid"],0); self.assertIsNotNone(forms[0]["invalidated_at"])
        with self.assertRaises(ConflictError): self.service.transition(current["id"],"closed",current["version"],"reviewer",TRANSITION_ROLES["closed"][0])
        self.service.accept_record(self.item["id"],first["id"],{"note":"re-checked","owner":"owner9","acceptance_no":"ACC-D-3"},"safety",'safety_manager')
        forms=self.service.list_acceptances(self.item["id"],first["id"],"viewer")
        self.assertEqual(len(forms),2); self.assertEqual(forms[0]["valid"],0); self.assertEqual(forms[1]["valid"],1)
        current=self.service.get_item(self.item["id"],"viewer")
        current=self.service.transition(current["id"],"closed",current["version"],"reviewer",TRANSITION_ROLES["closed"][0])
        self.assertEqual(current["status"],"closed")
        with self.assertRaises(ConflictError): self.service.update_record(self.item["id"],first["id"],{"detail":"too late"},"editor",'investigator')
if __name__=="__main__": unittest.main()

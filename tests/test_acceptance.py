import tempfile, unittest
from pathlib import Path
from src.domain import ConflictError, PermissionDenied, ValidationError
from src.repository import Repository
from src.service import Service
from src.rules import STATES, TRANSITION_ROLES
class AcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Repository(str(Path(self.tmp.name)/"test.db")); self.service=Service(self.repo)
        self.item=self.service.create_item({"title":"acceptance item","description":"acceptance scenarios","severity":'serious',"quantity":5,"threshold":10,"external_ref":"ACC-1"},"creator",'reporter')
    def tearDown(self): self.repo.close(); self.tmp.cleanup()
    def _record(self,ref="ACC-R1"):
        return self.service.add_record(self.item["id"],{"kind":"action","detail":"fix guard","external_ref":ref},"recorder",'investigator')
    def test_registration_stays_pending_acceptance(self):
        record=self._record()
        self.assertEqual(record["status"],"pending_acceptance")
        for bad in ("open","closed","accepted"):
            with self.assertRaises(ValidationError): self.service.add_record(self.item["id"],{"kind":"action","detail":"x","status":bad},"recorder",'investigator')
    def test_acceptance_requires_safety_manager_and_unique_number(self):
        record=self._record()
        with self.assertRaises(PermissionDenied): self.service.accept_record(self.item["id"],record["id"],{"note":"ok","owner":"a","acceptance_no":"AC-1"},"recorder",'investigator')
        acceptance=self.service.accept_record(self.item["id"],record["id"],{"note":"现场复查合格","owner":"张三","acceptance_no":"AC-1"},"safety",'safety_manager')
        self.assertEqual(acceptance["status"],"active"); self.assertEqual(acceptance["created_by"],"safety")
        self.assertEqual(self.service.list_records(self.item["id"],"viewer")[0]["status"],"accepted")
        other=self._record("ACC-R2")
        with self.assertRaises(ConflictError): self.service.accept_record(self.item["id"],other["id"],{"note":"ok","owner":"b","acceptance_no":"AC-1"},"safety",'safety_manager')
        with self.assertRaises(ConflictError): self.service.accept_record(self.item["id"],record["id"],{"note":"again","owner":"a","acceptance_no":"AC-2"},"safety",'safety_manager')
    def test_edit_after_acceptance_reopens_and_keeps_history(self):
        record=self._record()
        self.service.accept_record(self.item["id"],record["id"],{"note":"ok","owner":"张三","acceptance_no":"AC-1"},"safety",'safety_manager')
        updated=self.service.update_record(self.item["id"],record["id"],{"owner":"李四"},"editor",'safety_manager')
        self.assertEqual(updated["status"],"pending_acceptance")
        history=self.service.list_acceptances(self.item["id"],record["id"],"viewer")
        self.assertEqual(len(history),1); self.assertEqual(history[0]["status"],"voided"); self.assertIsNotNone(history[0]["voided_at"])
        with self.assertRaises(ConflictError): self.service.accept_record(self.item["id"],record["id"],{"note":"re","owner":"李四","acceptance_no":"AC-1"},"safety",'safety_manager')
        self.service.accept_record(self.item["id"],record["id"],{"note":"re","owner":"李四","acceptance_no":"AC-2"},"safety",'safety_manager')
        self.assertEqual(len(self.service.list_acceptances(self.item["id"],record["id"],"viewer")),2)
        unchanged=self.service.update_record(self.item["id"],record["id"],{"owner":"李四"},"editor",'investigator')
        self.assertEqual(unchanged["status"],"accepted")
    def test_verification_and_close_confirm_each_measure(self):
        first=self._record(); second=self._record("ACC-R2")
        current=self.service.get_item(self.item["id"],"viewer")
        for target in STATES[1:3]: current=self.service.transition(current["id"],target,current["version"],"reviewer",TRANSITION_ROLES[target][0])
        with self.assertRaises(ConflictError) as ctx: self.service.transition(current["id"],STATES[3],current["version"],"reviewer",TRANSITION_ROLES[STATES[3]][0])
        message=str(ctx.exception); self.assertIn(f"#{first['id']}",message); self.assertIn(f"#{second['id']}",message)
        self.service.accept_record(self.item["id"],first["id"],{"note":"ok","owner":"a","acceptance_no":"AC-1"},"safety",'safety_manager')
        with self.assertRaises(ConflictError): self.service.transition(current["id"],STATES[3],current["version"],"reviewer",TRANSITION_ROLES[STATES[3]][0])
        self.assertTrue(self.repo.verify_audit_chain())
if __name__=="__main__": unittest.main()

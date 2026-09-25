import unittest
from src import rules
from src.domain import ConflictError, ValidationError
class RulesTest(unittest.TestCase):
    def test_priority_deadline_and_escalation(self):
        low=rules.priority_score(rules.SEVERITIES[0],1,10,0); high=rules.priority_score(rules.SEVERITIES[-1],30,10,3)
        self.assertGreater(high,low); self.assertLessEqual(rules.response_deadline_hours(rules.SEVERITIES[-1],30,10),rules.response_deadline_hours(rules.SEVERITIES[0],1,10))
        self.assertTrue(rules.escalation_required(rules.SEVERITIES[-1],1,10)); self.assertTrue(rules.escalation_required(rules.SEVERITIES[0],10,10))
    def test_transition_guards(self):
        self.assertTrue(rules.can_transition(rules.STATES[0],rules.STATES[1]))
        with self.assertRaises(ConflictError): rules.validate_transition(rules.STATES[0],rules.STATES[-1])
        with self.assertRaises(ValidationError): rules.priority_score("not-a-severity",1,1)
    def test_acceptance_gates(self):
        self.assertEqual(rules.completion_blockers("verification",0),[]); self.assertEqual(rules.completion_blockers("closed",0),[])
        self.assertTrue(rules.completion_blockers("verification",2)); self.assertTrue(rules.completion_blockers("closed",1))
        self.assertEqual(rules.completion_blockers("investigating",3),[])
        self.assertTrue(rules.requires_reacceptance(["owner"])); self.assertTrue(rules.requires_reacceptance(["detail"]))
        self.assertFalse(rules.requires_reacceptance(["kind"])); self.assertFalse(rules.requires_reacceptance([]))
        with self.assertRaises(ConflictError): rules.ensure_not_terminal("closed")
if __name__=="__main__": unittest.main()

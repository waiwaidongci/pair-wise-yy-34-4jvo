from __future__ import annotations

from typing import Any, Dict, Optional

from .domain import (ConflictError, ValidationError, ensure_role,
                     normalize_severity, require_number, require_text)
from .repository import Repository
from .rules import (ACCEPT_ROLES, AUDIT_ROLES, CREATE_ROLES, ENTITY,
                    RECORD_ROLES, RECORD_STATES, TITLE, VIEW_ROLES,
                    acceptance_blockers, escalation_required, priority_score,
                    response_deadline_hours, role_for_transition,
                    validate_transition)


class Service:
    def __init__(self, repository: Repository):
        self.repository = repository

    def _view(self, role: str) -> None:
        ensure_role(role, VIEW_ROLES)

    def create_item(self, payload: Dict[str, Any], actor: str, role: str) -> Dict[str, Any]:
        ensure_role(role, CREATE_ROLES)
        actor = require_text(actor, "actor", 100)
        title = require_text(payload.get("title"), "title", 200)
        description = require_text(payload.get("description"), "description")
        severity = normalize_severity(payload.get("severity"))
        quantity = require_number(payload.get("quantity", 0), "quantity")
        threshold = require_number(payload.get("threshold", 1), "threshold", 0.000001)
        external_ref = payload.get("external_ref")
        if external_ref is not None:
            external_ref = require_text(external_ref, "external_ref", 100)
        item = self.repository.create_item(title, description, severity, quantity,
                                           threshold, external_ref, actor)
        self.repository.append_audit("create", ENTITY, item["id"], actor, {
            "title": title, "severity": severity, "quantity": quantity,
            "priority": priority_score(severity, quantity, threshold),
        })
        return self.enrich(item)

    def add_record(self, item_id: int, payload: Dict[str, Any], actor: str,
                   role: str) -> Dict[str, Any]:
        ensure_role(role, RECORD_ROLES)
        actor = require_text(actor, "actor", 100)
        kind = require_text(payload.get("kind"), "kind", 100)
        detail = require_text(payload.get("detail"), "detail")
        status = payload.get("status")
        if status is not None and status != RECORD_STATES[0]:
            raise ValidationError("措施登记后必须先处于待验收")
        owner = payload.get("owner")
        if owner is not None:
            owner = require_text(owner, "owner", 100)
        external_ref = payload.get("external_ref")
        if external_ref is not None:
            external_ref = require_text(external_ref, "external_ref", 100)
        record = self.repository.add_record(item_id, kind, detail, owner,
                                            external_ref, actor)
        self.repository.append_audit("record", ENTITY, item_id, actor, {
            "record_id": record["id"], "kind": kind, "status": record["status"],
        })
        return record

    def accept_record(self, item_id: int, record_id: int, payload: Dict[str, Any],
                      actor: str, role: str) -> Dict[str, Any]:
        ensure_role(role, ACCEPT_ROLES)
        actor = require_text(actor, "actor", 100)
        note = require_text(payload.get("note"), "note")
        owner = require_text(payload.get("owner"), "owner", 100)
        acceptance_no = require_text(payload.get("acceptance_no"), "acceptance_no", 100)
        record = self.repository.get_record(item_id, record_id)
        if record["status"] == RECORD_STATES[1]:
            raise ConflictError("该措施已验收通过")
        acceptance = self.repository.create_acceptance(record_id, acceptance_no,
                                                       note, owner, actor)
        self.repository.append_audit("accept", ENTITY, item_id, actor, {
            "record_id": record_id, "acceptance_no": acceptance_no, "owner": owner,
        })
        return acceptance

    def update_record(self, item_id: int, record_id: int, payload: Dict[str, Any],
                      actor: str, role: str) -> Dict[str, Any]:
        ensure_role(role, RECORD_ROLES)
        actor = require_text(actor, "actor", 100)
        record = self.repository.get_record(item_id, record_id)
        fields: Dict[str, Any] = {}
        if "detail" in payload:
            fields["detail"] = require_text(payload.get("detail"), "detail")
        if "owner" in payload:
            owner = payload.get("owner")
            fields["owner"] = None if owner is None else require_text(owner, "owner", 100)
        if not fields:
            raise ValidationError("没有可更新的字段")
        changed = any(record[name] != value for name, value in fields.items())
        voided_id = None
        if changed and record["status"] == RECORD_STATES[1]:
            record, voided_id = self.repository.reopen_record(record_id, fields)
        else:
            record = self.repository.update_record(record_id, fields)
        self.repository.append_audit("record_update", ENTITY, item_id, actor, {
            "record_id": record_id, "fields": sorted(fields),
            "acceptance_voided": voided_id is not None,
        })
        return record

    def list_acceptances(self, item_id: int, record_id: int, role: str) -> list:
        self._view(role)
        self.repository.get_record(item_id, record_id)
        return self.repository.list_acceptances(record_id)

    def transition(self, item_id: int, target: str, expected_version: int,
                   actor: str, role: str) -> Dict[str, Any]:
        actor = require_text(actor, "actor", 100)
        item = self.repository.get_item(item_id)
        validate_transition(item["status"], target)
        ensure_role(role, role_for_transition(target))
        if not isinstance(expected_version, int) or expected_version < 1:
            raise ValueError("expected_version必须是正整数")
        blockers = acceptance_blockers(target, self.repository.unaccepted_records(item_id))
        if blockers:
            raise ConflictError("；".join(blockers))
        updated = self.repository.transition_item(item_id, target, expected_version, actor)
        self.repository.append_audit("transition", ENTITY, item_id, actor, {
            "from": item["status"], "to": target,
            "escalation_required": escalation_required(
                item["severity"], item["quantity"], item["threshold"]),
        })
        return self.enrich(updated)

    def get_item(self, item_id: int, role: str) -> Dict[str, Any]:
        self._view(role)
        return self.enrich(self.repository.get_item(item_id))

    def list_items(self, role: str, status: Optional[str] = None) -> list:
        self._view(role)
        return [self.enrich(item) for item in self.repository.list_items(status)]

    def list_records(self, item_id: int, role: str) -> list:
        self._view(role)
        return self.repository.list_records(item_id)

    def audit(self, role: str, item_id: Optional[int] = None) -> list:
        ensure_role(role, AUDIT_ROLES)
        return self.repository.list_audit(item_id)

    @staticmethod
    def enrich(item: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(item)
        result["priority"] = priority_score(
            item["severity"], item["quantity"], item["threshold"])
        result["deadline_hours"] = response_deadline_hours(
            item["severity"], item["quantity"], item["threshold"])
        result["escalation_required"] = escalation_required(
            item["severity"], item["quantity"], item["threshold"])
        return result

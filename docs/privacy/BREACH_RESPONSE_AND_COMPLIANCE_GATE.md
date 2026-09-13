# Privacy breach response and compliance gate

1. Contain: revoke affected sessions/keys, isolate services, preserve logs and
   immutable audit evidence, and prohibit ad-hoc database cleanup.
2. Assess: record discovery time, likely occurrence time, affected tenants/data
   classes, access path, safeguards, recipients, and continuing risk.
3. Notify: the privacy/legal owner determines regulator, patient, partner, and
   insurer notifications and deadlines for the applicable jurisdiction.
4. Recover: rotate secrets, restore clean services, validate `/ready`, run the
   API/security suites, and monitor for recurrence.
5. Learn: document root cause, corrective controls, owners, deadlines, and proof
   of completion without copying PHI into issue trackers.

Production release is blocked until the privacy owner signs the versioned
retention policy, breach procedure, data inventory, subprocessors, cross-border
transfers, patient notices, consent language, and data-subject workflow. Code
tests cannot substitute for this legal/regulatory decision.

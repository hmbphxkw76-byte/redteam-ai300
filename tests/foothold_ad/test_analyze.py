#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判据层：Kerberos / ADCS / 目录复制 / 域信任 / 路径与八步折叠。"""
import unittest

from tools.foothold_ad.analyze import (
    adcs_risks, asrep_roastable, assess, dcsync_principals, kerberoastable,
    path_to_domain_admin, trust_risks, unconstrained,
)
from tools.foothold_ad.artifact import Ace, Directory, DirectoryUser, Template, Trust
from tools.foothold_ad.model import (
    ABSENT, AUTH_REQUIRED, BLOCKED, EXPOSED_NO_AUTH, EXPLOITED, UNDETERMINED,
)


def user(name, **kwargs):
    kwargs.setdefault("domain", "megacorpone.ai")
    return DirectoryUser(name=name, **kwargs)


class KerberosTest(unittest.TestCase):
    def test_kerberoastable_hits_unknown_and_skips(self):
        directory = Directory("megacorpone.ai", users=(
            user("svc-sql", enabled=True, spn=("MSSQLSvc/db:1433",)),
            user("ghost", enabled=None, spn=("HTTP/web",)),
            user("off", enabled=False, spn=("HTTP/off",)),
            user("krbtgt", enabled=True, spn=("kadmin/changepw",)),
            user("plain", enabled=True),
        ))
        hits, unknown = kerberoastable(directory)
        self.assertEqual([f.subject for f in hits], ["svc-sql@megacorpone.ai"])
        self.assertEqual(len(unknown), 1)
        self.assertIn("ghost", unknown[0])

    def test_asrep_preauth_unknown_not_guessed(self):
        directory = Directory("corp", users=(
            user("jdoe", preauth_required=False),
            user("mystery", preauth_required=None),
            user("krbtgt", preauth_required=False),
        ))
        hits, unknown = asrep_roastable(directory)
        self.assertEqual([f.kind for f in hits], ["asrep"])
        self.assertEqual(len(unknown), 1)

    def test_unconstrained_users_and_computers(self):
        directory = Directory("corp", users=(user("ops", delegation="unconstrained"),),
                              computers=("WS01",))
        findings = unconstrained(directory)
        self.assertEqual(len(findings), 2)
        self.assertEqual({f.kind for f in findings},
                         {"unconstrained-delegation", "unconstrained-delegation-candidate"})


class AdcsTest(unittest.TestCase):
    def test_esc1_esc8_and_undetermined(self):
        templates = (
            Template("ESC1Tpl", True, ("Client Authentication",), ("Domain Users",), False, True, False, False),
            Template("NoApprovalKnown", True, ("1.3.6.1.5.5.7.3.2",), ("Authenticated Users",), None, None),
            Template("NoEku", True, (), ("Domain Users",), False, None, False, None),
            Template("Strong", False, ("Client Authentication",), ("Domain Admins",), True, False),
        )
        hits, unknown = adcs_risks(templates)
        self.assertIn("esc1", [f.kind for f in hits])
        self.assertIn("esc8", [f.kind for f in hits])
        self.assertTrue(any("签发要求字段缺失" in item for item in unknown))
        self.assertTrue(any("EKU 或注册权字段缺失" in item for item in unknown))
        self.assertFalse(any("Strong" in item for item in unknown))

    def test_eku_oid_and_enroll_prefix(self):
        hits, _ = adcs_risks((Template("OidTpl", True, ("smart card logon",), ("everyone",), False, False, False, False),))
        self.assertEqual(hits[0].kind, "esc1")


class DcsyncTest(unittest.TestCase):
    def test_full_partial_and_machine_skip(self):
        aces = (
            Ace("svc-sql", "DS-Replication-Get-Changes-All", "DC=corp"),
            Ace("helpdesk", "DS-Replication-Get-Changes", "DC=corp"),
            Ace("DC01$", "DS-Replication-Get-Changes-All", "DC=corp"),
            Ace("alice", "GenericAll", "DC=corp"),
        )
        full, partial, notes = dcsync_principals(aces)
        self.assertEqual([f.subject for f in full], ["svc-sql"])
        self.assertEqual([f.subject for f in partial], ["helpdesk"])
        self.assertTrue(any("机器账户" in note for note in notes))


class TrustTest(unittest.TestCase):
    def test_sid_filtering_and_direction(self):
        trusts = (
            Trust("dmz", "dev", "bidirectional", False),
            Trust("root", "ext", "", None),
        )
        directory = Directory("megacorpone.ai", users=(
            user("alice", domain="dev.megacorpone.ai", member_of=("Domain Admins",)),
            user("bob", member_of=("Domain Users",)),
        ))
        hits, cross, unknown = trust_risks(trusts, directory)
        kinds = {f.kind for f in hits}
        self.assertEqual(kinds, {"trust-sid-filtering-off", "trust-bidirectional"})
        self.assertEqual([f.subject for f in cross], ["alice@dev.megacorpone.ai"])
        self.assertTrue(any("方向缺失" in item for item in unknown))
        self.assertTrue(any("SID 过滤字段缺失" in item for item in unknown))

    def test_enterprise_admin_pattern(self):
        directory = Directory("corp", users=(user("ent", member_of=("Enterprise Admins",)),))
        _, cross, _ = trust_risks((), directory)
        self.assertEqual(len(cross), 1)


class PathTest(unittest.TestCase):
    def test_bfs_reaches_domain_admins(self):
        directory = Directory("corp", users=(
            user("alice", member_of=("Helpdesk",)),
            user("bob", member_of=("Domain Admins",)),
        ), aces=(Ace("Helpdesk", "GenericAll", "bob"),))
        self.assertEqual(path_to_domain_admin(directory, ("alice",)),
                         ("alice", "Helpdesk", "bob", "Domain Admins"))

    def test_no_path_returns_empty(self):
        directory = Directory("corp", users=(user("alice", member_of=("Domain Users",)),))
        self.assertEqual(path_to_domain_admin(directory, ("alice",)), ())


class AssessTest(unittest.TestCase):
    def _directory(self):
        return Directory(
            "megacorpone.ai",
            users=(
                user("svc-sql", enabled=True, spn=("MSSQLSvc/db:1433",)),
                user("alice", domain="dev.megacorpone.ai", member_of=("Domain Admins",)),
            ),
            aces=(Ace("svc-sql", "DS-Replication-Get-Changes-All", "DC=megacorpone,DC=ai"),),
        )

    def test_without_directory_all_dependent_steps_undetermined(self):
        results = assess()
        for step in ("ad-01", "ad-02", "ad-05", "ad-06"):
            self.assertEqual(results[step].verdict, UNDETERMINED)
        self.assertEqual(results["ad-07"].verdict, UNDETERMINED)
        self.assertEqual(results["ad-08"].verdict, UNDETERMINED)

    def test_full_chain(self):
        results = assess(
            directory=self._directory(),
            templates=(Template("ESC1", True, ("Client Authentication",), ("Domain Users",), False, True, False, False),),
            trusts=(Trust("dmz.megacorpone.ai", "dev.megacorpone.ai", "bidirectional", False),),
            owned=("svc-sql",),
            tickets=({"account": "svc-sql", "enctype": "rc4"},),
            proof={"value": "flag{dc}", "panel": "flag{dc}"},
        )
        self.assertEqual(results["ad-01"].verdict, EXPLOITED)
        self.assertEqual(results["ad-02"].verdict, EXPLOITED)
        self.assertEqual(results["ad-03"].verdict, EXPLOITED)
        self.assertEqual(results["ad-04"].verdict, EXPLOITED)
        self.assertEqual(results["ad-05"].verdict, EXPLOITED)
        self.assertEqual(results["ad-06"].verdict, EXPLOITED)
        self.assertEqual(results["ad-07"].verdict, EXPLOITED)
        self.assertEqual(results["ad-08"].verdict, EXPLOITED)

    def test_empty_and_partial_inputs(self):
        results = assess(directory=Directory("corp"), templates=(), trusts=(), tickets=())
        self.assertEqual(results["ad-01"].verdict, ABSENT)
        self.assertEqual(results["ad-02"].verdict, ABSENT)
        self.assertEqual(results["ad-05"].verdict, ABSENT)
        self.assertEqual(results["ad-06"].verdict, ABSENT)
        self.assertEqual(results["ad-03"].verdict, AUTH_REQUIRED)
        self.assertEqual(results["ad-04"].verdict, UNDETERMINED)
        self.assertEqual(results["ad-08"].verdict, UNDETERMINED)

    def test_domain_missing_without_trusts_is_undetermined(self):
        results = assess(directory=Directory(""))
        self.assertEqual(results["ad-01"].verdict, UNDETERMINED)

    def test_unknown_fields_propagate_undetermined(self):
        directory = Directory("corp", users=(user("ghost", enabled=None, spn=("HTTP/web",),
                                                  preauth_required=None),))
        results = assess(directory=directory, templates=(Template("T", False, (), (), True, None),))
        self.assertEqual(results["ad-02"].verdict, UNDETERMINED)
        self.assertEqual(results["ad-04"].verdict, UNDETERMINED)

    def test_esc8_only_is_exposed(self):
        results = assess(directory=Directory("corp"),
                        templates=(Template("Relay", False, (), (), True, True, None, False),))
        self.assertEqual(results["ad-04"].verdict, EXPOSED_NO_AUTH)

    def test_partial_dcsync_is_exposed(self):
        directory = Directory("corp", aces=(Ace("helpdesk", "DS-Replication-Get-Changes", "DC=corp"),))
        self.assertEqual(assess(directory=directory)["ad-05"].verdict, EXPOSED_NO_AUTH)

    def test_trust_risk_without_cross_domain_is_exposed(self):
        results = assess(directory=Directory("corp"),
                        trusts=(Trust("a", "b", "bidirectional", True),))
        self.assertEqual(results["ad-06"].verdict, EXPOSED_NO_AUTH)

    def test_proof_mismatch_blocks(self):
        results = assess(directory=Directory("corp"),
                         proof={"value": "flag{a}", "panel": "flag{b}"})
        self.assertEqual(results["ad-07"].verdict, BLOCKED)

    def test_strong_templates_are_absent(self):
        results = assess(directory=Directory("corp"),
                        templates=(Template("T", False, ("Client Authentication",), ("Domain Admins",), True, False),))
        self.assertEqual(results["ad-04"].verdict, ABSENT)


if __name__ == "__main__":
    unittest.main()

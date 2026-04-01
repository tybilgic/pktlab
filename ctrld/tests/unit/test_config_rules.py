"""Unit tests for standalone rules parsing and semantic validation."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from pktlab_ctrld.config.rules import load_rules_config, parse_rules_config_text
from pktlab_ctrld.config.validation import validate_ruleset
from pktlab_ctrld.error import ConfigParseError, ValidationError

VALID_RULES_YAML = """
version: 3
default_action:
  type: drop
entries:
  - id: 10
    priority: 10
    match:
      proto: udp
      dst_port: 53
    action:
      type: forward
      port: dtap1
"""

INVALID_RULES_YAML = """
version: 1
default_action:
  type: forward
  port: dtap9
entries:
  - id: 7
    priority: 1
    match:
      proto: icmp
      dst_port: 53
    action:
      type: mirror
      port: dtap9
  - id: 7
    priority: 2
    match:
      src_ip: 999.1.1.1
    action:
      type: count
"""


class RulesConfigTests(unittest.TestCase):
    """Keep standalone rules parsing and validation deterministic."""

    def test_parse_and_validate_standalone_rules(self) -> None:
        ruleset = parse_rules_config_text(VALID_RULES_YAML, source="inline-rules")

        validated = validate_ruleset(ruleset, allowed_port_names={"dtap0", "dtap1"})

        self.assertEqual(validated.ruleset.version, 3)
        self.assertEqual(validated.allowed_port_names, frozenset({"dtap0", "dtap1"}))

    def test_load_rules_config_from_disk(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pktlab-rules-") as tmpdir:
            config_path = pathlib.Path(tmpdir) / "rules.yaml"
            config_path.write_text(VALID_RULES_YAML, encoding="utf-8")

            ruleset = load_rules_config(config_path)

        self.assertEqual(ruleset.entries[0].action.port, "dtap1")

    def test_parser_reports_shape_errors(self) -> None:
        with self.assertRaises(ConfigParseError):
            parse_rules_config_text("entries: [", source="broken-rules-yaml")

        with self.assertRaises(ConfigParseError) as context:
            parse_rules_config_text("- not-a-mapping", source="broken-rules-root")

        self.assertEqual(context.exception.context["root_type"], "list")

    def test_validation_reports_structured_rule_issues(self) -> None:
        ruleset = parse_rules_config_text(INVALID_RULES_YAML, source="invalid-rules")

        with self.assertRaises(ValidationError) as context:
            validate_ruleset(ruleset, allowed_port_names={"dtap0", "dtap1"})

        self.assertEqual(context.exception.code.value, "RULE_VALIDATION_ERROR")
        issues = list(context.exception.issues)
        issue_codes = {issue["code"] for issue in issues}
        issue_paths = {issue["path"] for issue in issues}
        self.assertIn("unknown_port", issue_codes)
        self.assertIn("duplicate_rule_id", issue_codes)
        self.assertIn("icmp_port_match", issue_codes)
        self.assertIn("invalid_ipv4_address", issue_codes)
        self.assertIn("rules.default_action.port", issue_paths)


if __name__ == "__main__":
    unittest.main()

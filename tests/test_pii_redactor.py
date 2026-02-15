"""Tests for the PII redaction module."""

from llm_guardrails.pii_redactor import PIIRedactor


class TestEmailRedaction:
    def test_single_email(self):
        redactor = PIIRedactor()
        text = "Contact me at alice@example.com for details."
        redacted, mapping = redactor.redact(text)

        assert "alice@example.com" not in redacted
        assert "<<EMAIL_1>>" in redacted
        assert mapping["<<EMAIL_1>>"] == "alice@example.com"

    def test_multiple_emails(self):
        redactor = PIIRedactor()
        text = "Send to alice@example.com or bob@corp.io please."
        redacted, mapping = redactor.redact(text)

        assert "alice@example.com" not in redacted
        assert "bob@corp.io" not in redacted
        assert len([k for k in mapping if "EMAIL" in k]) == 2


class TestPhoneRedaction:
    def test_us_phone_dashes(self):
        redactor = PIIRedactor()
        text = "Call me at 555-123-4567."
        redacted, mapping = redactor.redact(text)

        assert "555-123-4567" not in redacted
        assert any("PHONE" in k for k in mapping)

    def test_us_phone_parens(self):
        redactor = PIIRedactor()
        text = "My number is (555) 123-4567."
        redacted, mapping = redactor.redact(text)

        assert "(555) 123-4567" not in redacted


class TestSSNRedaction:
    def test_ssn_format(self):
        redactor = PIIRedactor()
        text = "My SSN is 123-45-6789."
        redacted, mapping = redactor.redact(text)

        assert "123-45-6789" not in redacted
        assert any("SSN" in k for k in mapping)


class TestCreditCardRedaction:
    def test_credit_card_spaces(self):
        redactor = PIIRedactor()
        text = "Card: 4111 1111 1111 1111."
        redacted, mapping = redactor.redact(text)

        assert "4111 1111 1111 1111" not in redacted
        assert any("CREDIT_CARD" in k for k in mapping)


class TestIPAddressRedaction:
    def test_ipv4(self):
        redactor = PIIRedactor()
        text = "Server at 192.168.1.100 is down."
        redacted, mapping = redactor.redact(text)

        assert "192.168.1.100" not in redacted
        assert any("IP_ADDRESS" in k for k in mapping)


class TestRoundTrip:
    def test_redact_then_restore(self):
        redactor = PIIRedactor()
        original = (
            "Email alice@example.com, call 555-123-4567, "
            "SSN 123-45-6789."
        )
        redacted, mapping = redactor.redact(original)

        # Nothing from the original PII should survive redaction.
        assert "alice@example.com" not in redacted
        assert "555-123-4567" not in redacted
        assert "123-45-6789" not in redacted

        restored = redactor.restore(redacted, mapping)
        assert restored == original

    def test_no_pii_passthrough(self):
        redactor = PIIRedactor()
        text = "Hello, world!"
        redacted, mapping = redactor.redact(text)

        assert redacted == text
        assert mapping == {}

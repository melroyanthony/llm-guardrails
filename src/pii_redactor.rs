use std::collections::{HashMap, HashSet};

use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;

struct PiiPattern {
    label: &'static str,
    regex: Regex,
}

static PII_PATTERNS: Lazy<Vec<PiiPattern>> = Lazy::new(|| {
    vec![
        PiiPattern {
            label: "SSN",
            regex: Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").unwrap(),
        },
        PiiPattern {
            label: "CREDIT_CARD",
            regex: Regex::new(r"\b(?:\d[ -]*?){13,19}\b").unwrap(),
        },
        PiiPattern {
            label: "EMAIL",
            regex: Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b").unwrap(),
        },
        PiiPattern {
            label: "PHONE",
            regex: Regex::new(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b").unwrap(),
        },
        PiiPattern {
            label: "IP_ADDRESS",
            regex: Regex::new(
                r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
            )
            .unwrap(),
        },
        PiiPattern {
            label: "DATE_OF_BIRTH",
            regex: Regex::new(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b").unwrap(),
        },
        PiiPattern {
            label: "NAME",
            // Conservative heuristic: two+ capitalised words (min 2 chars each).
            // The Python version uses lookbehind which the Rust regex crate does not support.
            regex: Regex::new(r"\b[A-Z][a-z]{1,}\s[A-Z][a-z]{1,}\b").unwrap(),
        },
    ]
});

static NAME_CONTEXT: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"(?i)\b(?:name|named|patient|mr|mrs|ms|miss|dr)\b").unwrap());

static DOB_CONTEXT: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"(?i)\b(?:born|birth|dob|d\.o\.b)\b").unwrap());

fn normalised_labels(labels: Option<&[String]>) -> Option<HashSet<String>> {
    labels.map(|items| {
        items
            .iter()
            .map(|label| label.trim().to_ascii_uppercase())
            .filter(|label| !label.is_empty())
            .collect()
    })
}

fn entity_enabled(
    label: &str,
    allow: &Option<HashSet<String>>,
    deny: &Option<HashSet<String>>,
) -> bool {
    if deny.as_ref().is_some_and(|set| set.contains(label)) {
        return false;
    }
    match allow {
        Some(set) => set.contains(label),
        None => true,
    }
}

fn digits_of(value: &str) -> Vec<u8> {
    value
        .chars()
        .filter(|ch| ch.is_ascii_digit())
        .map(|ch| ch as u8 - b'0')
        .collect()
}

fn luhn_valid(value: &str) -> bool {
    let digits = digits_of(value);
    if !(13..=19).contains(&digits.len()) {
        return false;
    }
    let mut sum = 0;
    for (index, digit) in digits.iter().rev().enumerate() {
        let mut value = *digit;
        if index % 2 == 1 {
            value *= 2;
            if value > 9 {
                value -= 9;
            }
        }
        sum += value;
    }
    sum % 10 == 0
}

fn ssn_valid(value: &str) -> bool {
    let mut parts = value.split('-');
    let Some(area) = parts.next() else {
        return false;
    };
    let Some(group) = parts.next() else {
        return false;
    };
    let Some(serial) = parts.next() else {
        return false;
    };
    if parts.next().is_some() {
        return false;
    }
    if area == "000" || area == "666" || area.starts_with('9') || group == "00" || serial == "0000"
    {
        return false;
    }
    true
}

fn slice_window(text: &str, start: usize, end: usize) -> &str {
    let mut from = start;
    while from < end && !text.is_char_boundary(from) {
        from += 1;
    }
    let mut to = end.min(text.len());
    while to > from && !text.is_char_boundary(to) {
        to -= 1;
    }
    &text[from..to]
}

fn has_context(text: &str, start: usize, end: usize, pattern: &Regex) -> bool {
    let before = slice_window(text, start.saturating_sub(80), start);
    let after = slice_window(text, end, end.saturating_add(24));
    pattern.is_match(before) || pattern.is_match(after)
}

fn match_accepted(label: &str, matched: &str, text: &str, start: usize, end: usize) -> bool {
    match label {
        "CREDIT_CARD" => luhn_valid(matched),
        "SSN" => ssn_valid(matched),
        "NAME" => has_context(text, start, end, &NAME_CONTEXT),
        "DATE_OF_BIRTH" => has_context(text, start, end, &DOB_CONTEXT),
        _ => true,
    }
}

fn redact_text(
    text: &str,
    allow_entities: Option<&[String]>,
    deny_entities: Option<&[String]>,
) -> (String, HashMap<String, String>) {
    let allow = normalised_labels(allow_entities);
    let deny = normalised_labels(deny_entities);
    let mut result = text.to_string();
    let mut mapping = HashMap::new();
    let mut counters: HashMap<&str, usize> = HashMap::new();

    for pattern in PII_PATTERNS.iter() {
        if !entity_enabled(pattern.label, &allow, &deny) {
            continue;
        }
        // Collect all matches in the current (already-modified) text.
        let current = result.clone();
        let matches: Vec<_> = pattern
            .regex
            .find_iter(&current)
            .filter(|found| {
                let matched = found.as_str();
                if matched.starts_with("<<") && matched.ends_with(">>") {
                    return false;
                }
                match_accepted(pattern.label, matched, &current, found.start(), found.end())
            })
            .map(|found| (found.start(), found.end(), found.as_str().to_string()))
            .collect();

        // Assign counter values in forward (left-to-right) order.
        let mut replacements: Vec<(usize, usize, String, String)> = Vec::new();
        for (start, end, original) in &matches {
            let count = counters.entry(pattern.label).or_insert(0);
            *count += 1;
            let placeholder = format!("<<{}_{}>>", pattern.label, count);
            replacements.push((*start, *end, placeholder, original.clone()));
        }

        // Apply replacements in reverse order so that earlier offsets stay valid.
        for (start, end, placeholder, original) in replacements.into_iter().rev() {
            mapping.insert(placeholder.clone(), original);
            result = format!("{}{}{}", &result[..start], placeholder, &result[end..]);
        }
    }

    (result, mapping)
}

/// Redact PII from text, returning (redacted_text, {placeholder: original}).
///
/// `allow_entities`, when set, limits detection to those labels. `deny_entities`
/// always skips those labels. Names and dates of birth also need a nearby
/// context word, and card numbers must pass the Luhn check.
#[pyfunction]
#[pyo3(signature = (text, allow_entities=None, deny_entities=None))]
pub fn pii_redact(
    text: &str,
    allow_entities: Option<Vec<String>>,
    deny_entities: Option<Vec<String>>,
) -> (String, HashMap<String, String>) {
    redact_text(text, allow_entities.as_deref(), deny_entities.as_deref())
}

/// Restore original PII values from a mapping produced by `pii_redact`.
#[pyfunction]
pub fn pii_restore(text: &str, mapping: HashMap<String, String>) -> String {
    let mut result = text.to_string();
    for (placeholder, original) in &mapping {
        result = result.replace(placeholder.as_str(), original.as_str());
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    fn redact(text: &str) -> (String, HashMap<String, String>) {
        redact_text(text, None, None)
    }

    #[test]
    fn test_email_redaction() {
        let (redacted, mapping) = redact("Contact alice@example.com for info.");
        assert!(!redacted.contains("alice@example.com"));
        assert!(redacted.contains("<<EMAIL_1>>"));
        assert_eq!(mapping["<<EMAIL_1>>"], "alice@example.com");
    }

    #[test]
    fn test_ssn_redaction() {
        let (redacted, mapping) = redact("SSN: 123-45-6789.");
        assert!(!redacted.contains("123-45-6789"));
        assert!(mapping.values().any(|v| v == "123-45-6789"));
    }

    #[test]
    fn test_round_trip() {
        let original = "Email alice@example.com, call 555-123-4567, SSN 123-45-6789.";
        let (redacted, mapping) = redact(original);
        let restored = pii_restore(&redacted, mapping);
        assert_eq!(restored, original);
    }

    #[test]
    fn test_no_pii() {
        let (redacted, mapping) = redact("Hello, world!");
        assert_eq!(redacted, "Hello, world!");
        assert!(mapping.is_empty());
    }

    #[test]
    fn test_credit_card_rejects_failed_luhn() {
        let text = "Order 1234-5678-9012-3456 is ready.";
        let (redacted, mapping) = redact(text);
        assert_eq!(redacted, text);
        assert!(!mapping.keys().any(|key| key.contains("CREDIT_CARD")));

        let plain = "Ref 1234567890123456.";
        let (redacted, mapping) = redact(plain);
        assert!(!mapping.keys().any(|key| key.contains("CREDIT_CARD")));
        assert!(!redacted.contains("<<CREDIT_CARD_"));
    }

    #[test]
    fn test_ssn_rejects_invalid_ranges() {
        for text in [
            "SSN 000-12-3456",
            "SSN 666-12-3456",
            "SSN 900-12-3456",
            "SSN 123-00-6789",
            "SSN 123-45-0000",
        ] {
            let (redacted, mapping) = redact(text);
            assert_eq!(redacted, text, "{text}");
            assert!(!mapping.keys().any(|key| key.contains("SSN")), "{text}");
        }
    }

    #[test]
    fn test_name_ignores_place_and_greeting() {
        for text in ["I live in New York.", "Hello World is a sample."] {
            let (redacted, mapping) = redact(text);
            assert_eq!(redacted, text, "{text}");
            assert!(!mapping.keys().any(|key| key.contains("NAME")), "{text}");
        }
    }

    #[test]
    fn test_name_with_context_is_redacted() {
        let (redacted, mapping) = redact("My name is Jane Doe.");
        assert!(!redacted.contains("Jane Doe"));
        assert_eq!(mapping["<<NAME_1>>"], "Jane Doe");
    }

    #[test]
    fn test_dob_without_context_is_kept() {
        let text = "The meeting is on 04/15/1990.";
        let (redacted, mapping) = redact(text);
        assert_eq!(redacted, text);
        assert!(!mapping.keys().any(|key| key.contains("DATE_OF_BIRTH")));
    }

    #[test]
    fn test_dob_with_context_is_redacted() {
        let (redacted, mapping) = redact("DOB: 04/15/1990.");
        assert!(!redacted.contains("04/15/1990"));
        assert_eq!(mapping["<<DATE_OF_BIRTH_1>>"], "04/15/1990");
    }

    #[test]
    fn test_allow_entities_limits_detection() {
        let allow = vec!["EMAIL".to_string()];
        let (redacted, mapping) = redact_text(
            "Email alice@example.com, SSN 123-45-6789.",
            Some(&allow),
            None,
        );
        assert!(!redacted.contains("alice@example.com"));
        assert!(redacted.contains("123-45-6789"));
        assert_eq!(mapping["<<EMAIL_1>>"], "alice@example.com");
        assert!(!mapping.keys().any(|key| key.contains("SSN")));
    }

    #[test]
    fn test_deny_entities_skips_a_label() {
        let deny = vec!["email".to_string()];
        let text = "Email alice@example.com today.";
        let (redacted, mapping) = redact_text(text, None, Some(&deny));
        assert_eq!(redacted, text);
        assert!(mapping.is_empty());
    }
}

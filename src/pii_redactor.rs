use std::collections::HashMap;

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

/// Redact PII from text, returning (redacted_text, {placeholder: original}).
#[pyfunction]
pub fn pii_redact(text: &str) -> (String, HashMap<String, String>) {
    let mut result = text.to_string();
    let mut mapping = HashMap::new();
    let mut counters: HashMap<&str, usize> = HashMap::new();

    for pattern in PII_PATTERNS.iter() {
        // Collect all matches in the current (already-modified) text.
        let current = result.clone();
        let matches: Vec<_> = pattern
            .regex
            .find_iter(&current)
            .filter(|m| {
                let s = m.as_str();
                !(s.starts_with("<<") && s.ends_with(">>"))
            })
            .map(|m| (m.start(), m.end(), m.as_str().to_string()))
            .collect();

        // Assign counter values in forward (left-to-right) order.
        let mut replacements: Vec<(usize, usize, String, String)> = Vec::new();
        for (start, end, original) in &matches {
            let count = counters.entry(pattern.label).or_insert(0);
            *count += 1;
            let placeholder = format!("<<{}_{}>>"  , pattern.label, count);
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

    #[test]
    fn test_email_redaction() {
        let (redacted, mapping) = pii_redact("Contact alice@example.com for info.");
        assert!(!redacted.contains("alice@example.com"));
        assert!(redacted.contains("<<EMAIL_1>>"));
        assert_eq!(mapping["<<EMAIL_1>>"], "alice@example.com");
    }

    #[test]
    fn test_ssn_redaction() {
        let (redacted, mapping) = pii_redact("SSN: 123-45-6789.");
        assert!(!redacted.contains("123-45-6789"));
        assert!(mapping.values().any(|v| v == "123-45-6789"));
    }

    #[test]
    fn test_round_trip() {
        let original = "Email alice@example.com, call 555-123-4567, SSN 123-45-6789.";
        let (redacted, mapping) = pii_redact(original);
        let restored = pii_restore(&redacted, mapping);
        assert_eq!(restored, original);
    }

    #[test]
    fn test_no_pii() {
        let (redacted, mapping) = pii_redact("Hello, world!");
        assert_eq!(redacted, "Hello, world!");
        assert!(mapping.is_empty());
    }
}

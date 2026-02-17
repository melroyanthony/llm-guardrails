use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use regex::Regex;

static HEDGING_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    let phrases = [
        "I think",
        "I believe",
        "I'm not sure",
        "I am not sure",
        "it is possible that",
        "it might be",
        "probably",
        "perhaps",
        "maybe",
        "as far as I know",
        "to the best of my knowledge",
        "I cannot confirm",
        "I don't have access",
        "I do not have access",
        "reportedly",
        "allegedly",
        "it seems",
        "it appears",
    ];
    phrases
        .iter()
        .map(|p| Regex::new(&format!("(?i){}", regex::escape(p))).unwrap())
        .collect()
});

fn hallucination_score(text: &str) -> f64 {
    if text.is_empty() {
        return 0.0;
    }
    let hits = HEDGING_PATTERNS
        .iter()
        .filter(|p| p.is_match(text))
        .count();
    (hits as f64 / 5.0).min(1.0)
}

struct Issue {
    rule: String,
    message: String,
    severity: String,
}

fn check_json(text: &str, schema_str: &str) -> Vec<Issue> {
    let mut issues = Vec::new();

    let data: serde_json::Value = match serde_json::from_str(text) {
        Ok(v) => v,
        Err(e) => {
            issues.push(Issue {
                rule: "json_schema".into(),
                message: format!("Output is not valid JSON: {}", e),
                severity: "error".into(),
            });
            return issues;
        }
    };

    let schema: serde_json::Value = match serde_json::from_str(schema_str) {
        Ok(v) => v,
        Err(e) => {
            issues.push(Issue {
                rule: "json_schema".into(),
                message: format!("Invalid schema JSON: {}", e),
                severity: "error".into(),
            });
            return issues;
        }
    };

    // Check top-level type
    if let Some(expected_type) = schema.get("type").and_then(|v| v.as_str()) {
        match expected_type {
            "object" if !data.is_object() => {
                issues.push(Issue {
                    rule: "json_schema".into(),
                    message: "Expected a JSON object at top level".into(),
                    severity: "error".into(),
                });
            }
            "array" if !data.is_array() => {
                issues.push(Issue {
                    rule: "json_schema".into(),
                    message: "Expected a JSON array at top level".into(),
                    severity: "error".into(),
                });
            }
            _ => {}
        }
    }

    // Check required keys (one level deep)
    if let Some(obj) = data.as_object() {
        if let Some(required) = schema.get("required").and_then(|v| v.as_array()) {
            for key in required {
                if let Some(key_str) = key.as_str() {
                    if !obj.contains_key(key_str) {
                        issues.push(Issue {
                            rule: "json_schema".into(),
                            message: format!("Required key missing: '{}'", key_str),
                            severity: "error".into(),
                        });
                    }
                }
            }
        }
    }

    issues
}

/// Validate LLM output text against configurable rules.
///
/// Returns (is_valid, issues_list, hallucination_score) where issues_list
/// is a Python list of dicts with keys: rule, message, severity.
#[pyfunction]
#[pyo3(signature = (text, json_schema=None, max_length=None, check_hallucination=true, hallucination_threshold=0.6, required_keywords=None, blocked_keywords=None))]
pub fn output_validate(
    py: Python<'_>,
    text: &str,
    json_schema: Option<&str>,
    max_length: Option<usize>,
    check_hallucination: bool,
    hallucination_threshold: f64,
    required_keywords: Option<Vec<String>>,
    blocked_keywords: Option<Vec<String>>,
) -> PyResult<(bool, Py<PyList>, f64)> {
    let mut issues: Vec<Issue> = Vec::new();
    let mut h_score = 0.0f64;

    // 1. Max-length check
    if let Some(max_len) = max_length {
        if text.len() > max_len {
            issues.push(Issue {
                rule: "max_length".into(),
                message: format!(
                    "Output length ({}) exceeds maximum ({})",
                    text.len(),
                    max_len
                ),
                severity: "error".into(),
            });
        }
    }

    // 2. JSON-schema validation
    if let Some(schema_str) = json_schema {
        issues.extend(check_json(text, schema_str));
    }

    // 3. Hallucination scoring
    if check_hallucination {
        h_score = hallucination_score(text);
        if h_score >= hallucination_threshold {
            issues.push(Issue {
                rule: "hallucination".into(),
                message: format!(
                    "High hedging-language score ({:.2}), possible hallucination",
                    h_score
                ),
                severity: "warning".into(),
            });
        }
    }

    // 4. Required keywords
    if let Some(ref keywords) = required_keywords {
        let lower_text = text.to_lowercase();
        for kw in keywords {
            if !lower_text.contains(&kw.to_lowercase()) {
                issues.push(Issue {
                    rule: "required_keyword".into(),
                    message: format!("Required keyword missing: '{}'", kw),
                    severity: "error".into(),
                });
            }
        }
    }

    // 5. Blocked keywords
    if let Some(ref keywords) = blocked_keywords {
        let lower_text = text.to_lowercase();
        for kw in keywords {
            if lower_text.contains(&kw.to_lowercase()) {
                issues.push(Issue {
                    rule: "blocked_keyword".into(),
                    message: format!("Blocked keyword found: '{}'", kw),
                    severity: "error".into(),
                });
            }
        }
    }

    let has_errors = issues.iter().any(|i| i.severity == "error");

    // Convert issues to Python list of dicts
    let py_issues = PyList::empty(py);
    for issue in &issues {
        let dict = PyDict::new(py);
        dict.set_item("rule", &issue.rule)?;
        dict.set_item("message", &issue.message)?;
        dict.set_item("severity", &issue.severity)?;
        py_issues.append(&dict)?;
    }

    let h_score = (h_score * 10_000.0).round() / 10_000.0;

    Ok((!has_errors, py_issues.unbind(), h_score))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hallucination_scoring() {
        let score = hallucination_score("I think this is probably maybe correct.");
        assert!(score > 0.0);
    }

    #[test]
    fn test_no_hedging() {
        let score = hallucination_score("Paris is the capital of France.");
        assert_eq!(score, 0.0);
    }

    #[test]
    fn test_empty_text() {
        let score = hallucination_score("");
        assert_eq!(score, 0.0);
    }
}

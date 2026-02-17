use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;

struct StereotypePattern {
    regex: Regex,
    description: &'static str,
}

static STEREOTYPE_PATTERNS: Lazy<Vec<StereotypePattern>> = Lazy::new(|| {
    vec![
        StereotypePattern {
            regex: Regex::new(
                r"(?i)\b(women|men|girls|boys)\s+(are|aren't|can't|should|shouldn't)\s+(naturally|inherently|biologically|always|never)",
            )
            .unwrap(),
            description: "Gender-stereotyping language detected",
        },
        StereotypePattern {
            regex: Regex::new(
                r"(?i)\b(all|every|no)\s+(men|women|asians?|blacks?|whites?|latinos?|hispanics?|muslims?|christians?|jews?|hindus?)\s+(are|have|lack|need)",
            )
            .unwrap(),
            description: "Absolute generalisation about a demographic group",
        },
        StereotypePattern {
            regex: Regex::new(
                r"(?i)\b(typical|stereotypical|expected)\s+(of|for)\s+(a|an|the)\s+(man|woman|asian|black|white|latino|hispanic|muslim|christian|jew|hindu)",
            )
            .unwrap(),
            description: "Explicit stereotyping framing detected",
        },
        StereotypePattern {
            regex: Regex::new(
                r"(?i)\b(elderly|old\s+people|seniors?)\s+(are|can't|shouldn't|always|never)\b",
            )
            .unwrap(),
            description: "Age-stereotyping language detected",
        },
        StereotypePattern {
            regex: Regex::new(
                r"(?i)\b(disabled|handicapped)\s+(people|persons?|individuals?)\s+(can't|are\s+unable|should\s+not|never)",
            )
            .unwrap(),
            description: "Disability-stereotyping language detected",
        },
    ]
});

static MALE_TOKENS: &[&str] = &[
    "he", "him", "his", "man", "men", "boy", "boys", "male", "father", "husband",
];
static FEMALE_TOKENS: &[&str] = &[
    "she", "her", "hers", "woman", "women", "girl", "girls", "female", "mother", "wife",
];

static GENERALISATION_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(
        r"(?i)\b(all|every|no|none\s+of\s+the|always|never)\s+(men|women|people\s+from|members\s+of|those\s+who)\b",
    )
    .unwrap()
});

const STEREOTYPE_WEIGHT: f64 = 0.40;
const IMBALANCE_WEIGHT: f64 = 0.25;
const GENERALISATION_WEIGHT: f64 = 0.35;
const IMBALANCE_THRESHOLD: f64 = 3.0;

fn count_tokens(text: &str, tokens: &[&str]) -> usize {
    let lower = text.to_lowercase();
    tokens.iter().filter(|t| lower.contains(*t)).count()
}

/// Score text for demographic bias, returning (score, flags).
#[pyfunction]
pub fn bias_score(text: &str) -> (f64, Vec<String>) {
    let mut flags: Vec<String> = Vec::new();
    let mut raw_scores: Vec<f64> = Vec::new();

    // 1. Stereotyping patterns
    let mut stereotype_hits = 0usize;
    for sp in STEREOTYPE_PATTERNS.iter() {
        if sp.regex.is_match(text) {
            flags.push(sp.description.to_string());
            stereotype_hits += 1;
        }
    }
    if stereotype_hits > 0 {
        let normalised = (stereotype_hits as f64 * 0.5).min(1.0);
        raw_scores.push(normalised * STEREOTYPE_WEIGHT);
    }

    // 2. Gender-reference imbalance
    let male_count = count_tokens(text, MALE_TOKENS);
    let female_count = count_tokens(text, FEMALE_TOKENS);
    if male_count > 0 && female_count > 0 {
        let max_c = male_count.max(female_count) as f64;
        let min_c = male_count.min(female_count) as f64;
        let ratio = max_c / min_c;
        if ratio >= IMBALANCE_THRESHOLD {
            let dominant = if male_count > female_count {
                "male"
            } else {
                "female"
            };
            flags.push(format!(
                "Gender-reference imbalance: {} references outnumber the other by {:.1}x",
                dominant, ratio
            ));
            let score = ((ratio - IMBALANCE_THRESHOLD) / 5.0 + 0.3).min(1.0);
            raw_scores.push(score * IMBALANCE_WEIGHT);
        }
    }

    // 3. Absolute generalisations
    let gen_matches: Vec<_> = GENERALISATION_PATTERN.find_iter(text).collect();
    if !gen_matches.is_empty() {
        let count = gen_matches.len();
        flags.push(format!(
            "Absolute generalisation marker(s) found ({} occurrence(s))",
            count
        ));
        let score = (count as f64 * 0.4).min(1.0);
        raw_scores.push(score * GENERALISATION_WEIGHT);
    }

    let total: f64 = if raw_scores.is_empty() {
        0.0
    } else {
        raw_scores.iter().sum::<f64>().min(1.0)
    };

    // Round to 4 decimal places for consistency with the Python version.
    let total = (total * 10_000.0).round() / 10_000.0;

    (total, flags)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_neutral_text() {
        let (score, flags) = bias_score("The weather today is sunny with a high of 75 degrees.");
        assert_eq!(score, 0.0);
        assert!(flags.is_empty());
    }

    #[test]
    fn test_gender_stereotype() {
        let (score, flags) = bias_score("Women are naturally bad at mathematics.");
        assert!(score > 0.0);
        assert!(flags
            .iter()
            .any(|f| f.to_lowercase().contains("stereotyp") || f.to_lowercase().contains("generalisation")));
    }

    #[test]
    fn test_absolute_generalisation() {
        let (score, flags) = bias_score("All women are emotional.");
        assert!(score > 0.0);
        assert!(!flags.is_empty());
    }
}

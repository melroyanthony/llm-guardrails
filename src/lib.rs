use pyo3::prelude::*;

/// Fixed case count for property tests. CI uses one seed so a failure repeats.
#[cfg(test)]
pub(crate) fn property_config() -> proptest::test_runner::Config {
    use proptest::test_runner::{Config, RngSeed};

    let mut config = Config::with_cases(24);
    config.max_shrink_iters = 64;
    if std::env::var_os("CI").is_some() {
        config.rng_seed = RngSeed::Fixed(20_261_113);
    }
    config
}

mod bias_scorer;
mod injection_detector;
mod output_validator;
mod pii_redactor;

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(pii_redactor::pii_redact, m)?)?;
    m.add_function(wrap_pyfunction!(pii_redactor::pii_restore, m)?)?;
    m.add_function(wrap_pyfunction!(injection_detector::injection_score, m)?)?;
    m.add_function(wrap_pyfunction!(injection_detector::injection_analyse, m)?)?;
    m.add_function(wrap_pyfunction!(
        injection_detector::injection_list_rules,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(bias_scorer::bias_score, m)?)?;
    m.add_function(wrap_pyfunction!(output_validator::output_validate, m)?)?;
    Ok(())
}

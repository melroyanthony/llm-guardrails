use pyo3::prelude::*;

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
    m.add_function(wrap_pyfunction!(injection_detector::injection_list_rules, m)?)?;
    m.add_function(wrap_pyfunction!(bias_scorer::bias_score, m)?)?;
    m.add_function(wrap_pyfunction!(output_validator::output_validate, m)?)?;
    Ok(())
}

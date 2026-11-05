# Guards

`GuardrailsPipeline` runs the guards in-process. Construct it with the switches you want. Nothing in the library reads `.env-template`.

| Switch | Default | What it does |
| --- | --- | --- |
| `pii_enabled` | `True` | Redact on the way in, restore on the way out |
| `injection_enabled` | `True` | Score patterns in the sanitised prompt |
| `bias_enabled` | `True` | Score a few bias patterns in the reply |
| `output_validation_enabled` | `True` | Apply `ValidationRules` to the reply |
| `injection_threshold` | `0.5` | Block when the injection score reaches this |
| `pii_allow_entities` | `None` | When set, only these labels are redacted |
| `pii_deny_entities` | `None` | Labels that are never redacted |

`allow_entities` and `deny_entities` are read-only after construction. An empty allow list raises `ValueError`. A denied label wins when it is also allowed. Unknown labels raise `ValueError`.

## PII

Placeholders look like `<<EMAIL_1>>` and `<<PHONE_1>>`. The mapping is `{placeholder: original}` from `pre_process`. Pass that mapping to `post_process` when you want the original values back.

SSNs whose area is `000`, `666`, or `9xx`, whose group is `00`, or whose serial is `0000` are left alone. A name or date of birth is redacted only beside a context word such as `name`, `born`, `DOB`, `Dr.`, or `Ms.`. `Jane Doe called` is not redacted.

## Injection

`pre.injection.score` is a float. `pre.blocked` is true when that score is at least the threshold. `matched_rules` names the patterns that fired. A low score is not a guarantee that the prompt is harmless.

## Output

`post.validation.is_valid` and `post.bias.score` describe the reply you passed in. The validator checks a small rule set, including top-level JSON `type` and `required` when you ask it to. It is not a full JSON Schema validator. The bias scorer looks for a few patterns. A score of `0.0` only means those patterns did not fire.

```text
Noted.
True
0.0
```

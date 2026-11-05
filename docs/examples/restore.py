from llm_guardrails import GuardrailsPipeline

pipeline = GuardrailsPipeline()
pre = pipeline.pre_process("Mail a@b.co about the notes.")
post = pipeline.post_process("Noted.", pre.pii_mapping)
print(post.final_text)
print(post.validation.is_valid)
print(post.bias.score)

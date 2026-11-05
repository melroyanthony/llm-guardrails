from llm_guardrails import GuardrailsPipeline

pipeline = GuardrailsPipeline()
pre = pipeline.pre_process("Mail a@b.co about the notes.")
print(pre.sanitised_text)
print("blocked", pre.blocked)

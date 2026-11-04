# AI Model Integration

Quick reference for AI model selection and integration patterns.

## OpenAI Models (December 2025)

### Chat/Completion Models

| Model | Use Case | Notes |
|-------|----------|-------|
| **gpt-5-mini** | Triage, analysis, structured output | Best cost/performance ratio |
| **gpt-4.1** | Complex reasoning, nuanced tasks | Higher cost, better quality |
| **o4-mini** | Multi-step reasoning | Uses reasoning tokens, no system message |

### Embedding Models

| Model | Dimensions | Use Case | Cost |
|-------|------------|----------|------|
| **text-embedding-3-large** | 3072 | High quality semantic matching | Higher |
| **text-embedding-3-small** | 1536 | Cost-effective, good quality | Lower |

---

## Known Limitations

### GPT-5-mini
- **No `temperature` parameter**: Only supports default temperature
- Works well with JSON mode for structured output

### Reasoning Models (o1, o4)
- **No system message support**: Use user message instead
- Reasoning tokens count toward usage
- Better for multi-step problem solving

---

## Integration Patterns

### Structured Output with GPT-5-mini

```typescript
// TypeScript (Node.js)
import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

interface TriageResult {
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  actions: string[];
  reasoning: string;
}

async function generateTriage(content: string): Promise<TriageResult> {
  const response = await openai.chat.completions.create({
    model: 'gpt-5-mini',
    messages: [
      {
        role: 'system',
        content: `You are a triage analyst. Output JSON with: severity, confidence (0-1), actions (array), reasoning.`,
      },
      {
        role: 'user',
        content: `Analyze this event: ${content}`,
      },
    ],
    response_format: { type: 'json_object' },
    // NOTE: temperature not supported by GPT-5-mini
  });

  return JSON.parse(response.choices[0].message.content!);
}
```

```python
# Python (FastAPI)
import openai
from pydantic import BaseModel

class TriageResult(BaseModel):
    severity: str
    confidence: float
    actions: list[str]
    reasoning: str

async def generate_triage(content: str) -> TriageResult:
    client = openai.AsyncOpenAI()

    response = await client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a triage analyst. Output JSON with: severity, confidence, actions, reasoning.",
            },
            {
                "role": "user",
                "content": f"Analyze this event: {content}",
            },
        ],
        response_format={"type": "json_object"},
        # NOTE: temperature not supported by GPT-5-mini
    )

    return TriageResult.model_validate_json(response.choices[0].message.content)
```

---

## Embedding Generation

### TypeScript (Node.js)

```typescript
async function generateEmbedding(text: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-large',
    input: text,
    encoding_format: 'float',
  });
  return response.data[0].embedding; // 3072 dimensions
}
```

### Python

```python
async def generate_embedding(text: str) -> list[float]:
    client = openai.AsyncOpenAI()

    response = await client.embeddings.create(
        model="text-embedding-3-large",
        input=text,
        encoding_format="float",
    )
    return response.data[0].embedding  # 3072 dimensions
```

---

## Vector Search Pattern

### Cosine Similarity

```typescript
// utils/similarity.ts
export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error('Vectors must have same length');
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i++) {
    const aVal = a[i] ?? 0;
    const bVal = b[i] ?? 0;
    dotProduct += aVal * bVal;
    normA += aVal * aVal;
    normB += bVal * bVal;
  }

  const magnitude = Math.sqrt(normA) * Math.sqrt(normB);
  return magnitude === 0 ? 0 : dotProduct / magnitude;
}
```

### Semantic Search

```typescript
interface ScoredItem<T> {
  item: T;
  score: number;
}

async function findRelevant<T extends { embedding: number[] }>(
  query: string,
  items: T[],
  topK = 3
): Promise<ScoredItem<T>[]> {
  const queryEmbedding = await generateEmbedding(query);

  return items
    .map((item) => ({
      item,
      score: cosineSimilarity(queryEmbedding, item.embedding),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);
}
```

---

## Error Handling

### Rate Limiting

```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 1000
): Promise<T> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      if (error?.status === 429 && attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }
      throw error;
    }
  }
  throw new Error('Max retries exceeded');
}

// Usage
const result = await withRetry(() => generateTriage(content));
```

### Fallback Response

```typescript
function createFallbackTriage(): TriageResult {
  return {
    severity: 'medium',
    confidence: 0.5,
    actions: ['Manual review required - AI triage unavailable'],
    reasoning: 'Automated triage could not be generated. Please review manually.',
  };
}

async function safeTriage(content: string): Promise<TriageResult> {
  try {
    return await generateTriage(content);
  } catch (error) {
    logger.error('triage', 'AI triage failed', error);
    return createFallbackTriage();
  }
}
```

---

## Cost Estimates (December 2025)

| Operation | Model | Tokens | Est. Cost |
|-----------|-------|--------|-----------|
| Embedding (per text) | text-embedding-3-large | ~200 | ~$0.00003 |
| Triage generation | gpt-5-mini | ~2500 total | ~$0.02 |
| Complex analysis | gpt-4.1 | ~3000 total | ~$0.12 |

**Monthly estimate (100 events/day):**
- Embeddings: ~$1
- Triage (gpt-5-mini): ~$60
- Total: ~$61/month

---

## Environment Configuration

```bash
# .env
OPENAI_API_KEY=sk-...

# Optional: Override defaults
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_CHAT_MODEL=gpt-5-mini
OPENAI_TIMEOUT_MS=30000
```

---

## Model Selection Guide

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Triage/Classification | gpt-5-mini | Fast, cost-effective, structured output |
| Semantic search | text-embedding-3-large | High quality matching |
| Complex reasoning | o4-mini or gpt-4.1 | Better multi-step logic |
| Budget constrained | gpt-5-mini + text-embedding-3-small | Lower cost |
| Highest quality | gpt-4.1 + text-embedding-3-large | Best results |

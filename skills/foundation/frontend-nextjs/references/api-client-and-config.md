## API Client Pattern

```tsx
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new ApiError(res.status, `API error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  items: {
    list: () => fetchApi<Item[]>('/api/v1/items'),
    get: (id: number) => fetchApi<Item>(`/api/v1/items/${id}`),
    create: (data: ItemCreate) =>
      fetchApi<Item>('/api/v1/items', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: number, data: ItemUpdate) =>
      fetchApi<Item>(`/api/v1/items/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      fetchApi<void>(`/api/v1/items/${id}`, { method: 'DELETE' }),
  },
};
```

## next.config.js

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // For Docker deployment
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
};

module.exports = nextConfig;
```


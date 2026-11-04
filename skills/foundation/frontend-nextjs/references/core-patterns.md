## Core Patterns

### Root Layout

```tsx
// app/layout.tsx
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'App Name',
  description: 'App description',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background">
        <main className="container mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
```

### Server Component Page with Data Fetching

```tsx
// app/items/page.tsx
// Server Component - can fetch data directly

import { ItemList } from '@/components/items/item-list';

const API_URL = process.env.API_URL || 'http://localhost:8000';

async function getItems() {
  const res = await fetch(`${API_URL}/api/v1/items`, {
    next: { revalidate: 60 }, // ISR: revalidate every 60s
  });

  if (!res.ok) {
    throw new Error('Failed to fetch items');
  }

  return res.json();
}

export default async function ItemsPage() {
  const items = await getItems();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Items</h1>
      <ItemList items={items} />
    </div>
  );
}
```

### Client Component with Interactivity

```tsx
// components/items/item-list.tsx
'use client';

import { useState } from 'react';
import { Item } from '@/types';

interface ItemListProps {
  items: Item[];
}

export function ItemList({ items: initialItems }: ItemListProps) {
  const [items, setItems] = useState(initialItems);
  const [filter, setFilter] = useState('');

  const filteredItems = items.filter((item) =>
    item.name.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div>
      <input
        type="text"
        placeholder="Filter items..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="border px-3 py-2 rounded mb-4 w-full"
      />
      <ul className="space-y-2">
        {filteredItems.map((item) => (
          <li key={item.id} className="border p-3 rounded">
            {item.name} - Qty: {item.quantity}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Server Actions (Mutations)

```tsx
// app/actions/items.ts
'use server';

import { revalidatePath } from 'next/cache';

const API_URL = process.env.API_URL || 'http://localhost:8000';

export async function createItem(formData: FormData) {
  const name = formData.get('name') as string;
  const quantity = Number(formData.get('quantity'));

  const res = await fetch(`${API_URL}/api/v1/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, quantity }),
  });

  if (!res.ok) {
    throw new Error('Failed to create item');
  }

  revalidatePath('/items');
  return res.json();
}

export async function deleteItem(id: number) {
  const res = await fetch(`${API_URL}/api/v1/items/${id}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    throw new Error('Failed to delete item');
  }

  revalidatePath('/items');
}
```

### Form with Server Action

```tsx
// components/items/create-item-form.tsx
'use client';

import { useFormStatus } from 'react-dom';
import { createItem } from '@/app/actions/items';

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50"
    >
      {pending ? 'Creating...' : 'Create Item'}
    </button>
  );
}

export function CreateItemForm() {
  return (
    <form action={createItem} className="space-y-4">
      <div>
        <label htmlFor="name" className="block text-sm font-medium">
          Name
        </label>
        <input
          type="text"
          id="name"
          name="name"
          required
          className="border px-3 py-2 rounded w-full"
        />
      </div>
      <div>
        <label htmlFor="quantity" className="block text-sm font-medium">
          Quantity
        </label>
        <input
          type="number"
          id="quantity"
          name="quantity"
          required
          min="0"
          className="border px-3 py-2 rounded w-full"
        />
      </div>
      <SubmitButton />
    </form>
  );
}
```

### Loading UI

```tsx
// app/items/loading.tsx
export default function Loading() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-gray-200 animate-pulse rounded" />
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-gray-200 animate-pulse rounded" />
        ))}
      </div>
    </div>
  );
}
```

### Error UI

```tsx
// app/items/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="text-center py-8">
      <h2 className="text-xl font-bold text-red-600 mb-4">
        Something went wrong!
      </h2>
      <p className="text-gray-600 mb-4">{error.message}</p>
      <button
        onClick={reset}
        className="bg-blue-500 text-white px-4 py-2 rounded"
      >
        Try again
      </button>
    </div>
  );
}
```


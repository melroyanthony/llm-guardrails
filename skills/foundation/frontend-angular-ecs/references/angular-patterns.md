## Angular 21 Patterns

### Standalone Component Bootstrap (no NgModules)

```typescript
// apps/shell/src/main.ts
import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, appConfig).catch(console.error);
```

```typescript
// apps/shell/src/app/app.config.ts
import {
  ApplicationConfig,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideRouter, withViewTransitions } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideClientHydration } from '@angular/platform-browser';
import { routes } from './app.routes';
import { authInterceptor } from './interceptors/auth.interceptor';
import { errorInterceptor } from './interceptors/error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    // No Zone.js — signals + explicit markForCheck() drive change detection
    provideZonelessChangeDetection(),
    provideRouter(routes, withViewTransitions()),
    provideHttpClient(withInterceptors([authInterceptor, errorInterceptor])),
    provideClientHydration(),               // Required for SSR hydration
  ],
};
```

### Signals for Reactive State

Signals replace RxJS subjects for local and shared state. Use `toSignal()` to bridge existing RxJS observables:

```typescript
// libs/data-access/src/lib/component-config.store.ts
import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';

export interface ComponentConfig {
  componentId: string;
  componentType: string;
  config: Record<string, unknown>;
  version: number;
  updatedAt: string;
}

@Injectable({ providedIn: 'root' })
export class ComponentConfigStore {
  private readonly http = inject(HttpClient);

  // Writable signals — source of truth
  private readonly _configs = signal<ComponentConfig[]>([]);
  private readonly _loading = signal(false);

  // Computed signals — derived state, no manual subscriptions
  readonly configs = this._configs.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly sliderConfigs = computed(() =>
    this._configs().filter((c) => c.componentType === 'slider')
  );
  readonly totalCount = computed(() => this._configs().length);

  load(): void {
    this._loading.set(true);
    this.http.get<ComponentConfig[]>('/api/configs').subscribe({
      next: (configs) => {
        this._configs.set(configs);
        this._loading.set(false);
      },
      error: () => this._loading.set(false),
    });
  }

  update(updated: ComponentConfig): void {
    this._configs.update((list) =>
      list.map((c) => (c.componentId === updated.componentId ? updated : c))
    );
  }
}
```

### `inject()` Function Instead of Constructor Injection

```typescript
// Preferred in Angular 21 — works in components, services, guards, interceptors
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ComponentConfigStore } from './component-config.store';

@Component({
  selector: 'app-config-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (store.loading()) {
      <app-spinner />
    } @else {
      @for (config of store.configs(); track config.componentId) {
        <app-config-card [config]="config" />
      } @empty {
        <p>No configs found.</p>
      }
    }
  `,
})
export class ConfigListComponent implements OnInit {
  protected readonly store = inject(ComponentConfigStore);
  private readonly router = inject(Router);

  ngOnInit(): void {
    this.store.load();
  }
}
```

### Typed HttpClient with Functional Interceptors

```typescript
// apps/shell/src/app/interceptors/auth.interceptor.ts
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthStore } from '@myworkspace/data-access';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authStore = inject(AuthStore);
  const token = authStore.accessToken();      // Signal read — no subscription needed

  if (token && req.url.startsWith('/api')) {
    return next(req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    }));
  }
  return next(req);
};
```

```typescript
// apps/shell/src/app/interceptors/error.interceptor.ts
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { Router } from '@angular/router';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401) {
        router.navigate(['/login']);
      }
      return throwError(() => err);
    })
  );
};
```

## SSR with @angular/ssr

```bash
ng add @angular/ssr --project=shell
```

```typescript
// apps/shell/src/app/app.config.server.ts
import { mergeApplicationConfig, ApplicationConfig } from '@angular/core';
import { provideServerRendering } from '@angular/platform-server';
import { appConfig } from './app.config';

const serverConfig: ApplicationConfig = {
  providers: [provideServerRendering()],
};

export const config = mergeApplicationConfig(appConfig, serverConfig);
```

Build outputs:
- `dist/apps/shell/browser/` — static assets (HTML, JS, CSS)
- `dist/apps/shell/server/` — SSR Node.js server bundle

For SSR on ECS: run the Node.js SSR server instead of nginx, or use nginx as a reverse proxy in front of it on port 4000.


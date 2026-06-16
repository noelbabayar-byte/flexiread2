/**
 * FlexiRead API client.
 *
 * Wraps the backend REST API (auth, upload, processing, content) and adapts the
 * backend's page/text payload into the reader engine's block-based BookContent.
 *
 * Token handling: access + refresh tokens are kept in localStorage. On a 401 the
 * client transparently tries the refresh endpoint once before failing.
 */

import { BookContent, ContentBlock, PageData } from '@/reader/types';

// =============================================================================
// FIX #1: API_BASE - Vite import.meta.env kullanimi duzeltildi
// =============================================================================
// ESKI (calismiyordu): (import.meta as any).env?.VITE_API_URL
// YENI (calisiyor):   import.meta.env.VITE_API_URL
// =============================================================================
const API_BASE: string =
  (import.meta.env.VITE_API_URL as string)?.replace(/\/$/, '') ||
  'http://localhost:8000';

const ACCESS_KEY = 'flexiread_access_token';
const REFRESH_KEY = 'flexiread_refresh_token';

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export const tokenStore = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string | null): void {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  get isAuthenticated(): boolean {
    return !!localStorage.getItem(ACCESS_KEY);
  },
};

// ---------------------------------------------------------------------------
// Backend response shapes
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in: number;
}

export interface UploadUrlResponse {
  book_id: string;
  presigned_url: string;
  s3_key: string;
  expires_in: number;
}

export interface BookStatus {
  id: string;
  title: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  total_pages: number;
  processed_pages: number;
  error_message: string | null;
  created_at: string;
}

interface BackendContentBlock {
  id?: string;
  type?: ContentBlock['type'];
  content?: string;
  metadata?: ContentBlock['metadata'];
}

interface BackendPage {
  page_number: number;
  text?: string | null;
  paragraphs?: string[] | null;
  blocks?: BackendContentBlock[] | null;
  method?: 'direct' | 'ocr' | 'none' | null;
  is_ocr?: boolean | null;
  confidence?: number | null;
}

interface BackendContentResponse {
  id?: string;
  book_id?: string;
  title: string;
  status: string;
  total_pages?: number | null;
  metadata?: { title?: string; author?: string; language?: string } | null;
  summary?: Record<string, unknown> | null;
  pages?: BackendPage[] | null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// ---------------------------------------------------------------------------
// Core fetch with auth + single refresh retry
// ---------------------------------------------------------------------------

async function rawFetch(path: string, init: RequestInit, auth: boolean): Promise<Response> {
  const headers = new Headers(init.headers || {});
  if (auth && tokenStore.access) {
    headers.set('Authorization', `Bearer ${tokenStore.access}`);
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

async function tryRefresh(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const res = await rawFetch(
    '/api/v1/auth/refresh',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    },
    false,
  );
  if (!res.ok) return false;
  const data: TokenResponse = await res.json();
  tokenStore.set(data.access_token, data.refresh_token);
  return true;
}

async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  auth = true,
): Promise<T> {
  let res = await rawFetch(path, init, auth);

  if (res.status === 401 && auth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await rawFetch(path, init, auth);
    } else {
      tokenStore.clear();
    }
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const jsonBody = (data: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

// FIX #2: Register fonksiyonu backend'den donen kullanici verisini de aliyor
export interface UserOut {
  id: string;
  email: string;
  full_name: string | null;
  plan_type: string;
  is_active: boolean;
  created_at: string;
}

export async function register(
  email: string,
  password: string,
  fullName?: string,
): Promise<UserOut> {
  return apiFetch<UserOut>(
    '/api/v1/auth/register',
    jsonBody({ email, password, full_name: fullName }),
    false,
  );
}

export async function login(email: string, password: string): Promise<void> {
  const data = await apiFetch<TokenResponse>(
    '/api/v1/auth/login',
    jsonBody({ email, password }),
    false,
  );
  tokenStore.set(data.access_token, data.refresh_token);
}

export function logout(): Promise<void> {
  const done = apiFetch('/api/v1/auth/logout', { method: 'POST' }).catch(() => {
    /* best-effort: revoke server-side, but always clear locally */
  });
  tokenStore.clear();
  return done as Promise<void>;
}

// ---------------------------------------------------------------------------
// Books
// ---------------------------------------------------------------------------

export function listBooks(): Promise<{ items: BookStatus[]; total: number }> {
  return apiFetch('/api/v1/books/');
}

export function getBookStatus(bookId: string): Promise<BookStatus> {
  return apiFetch(`/api/v1/books/${bookId}/status`);
}

async function getUploadUrl(file: File, title?: string): Promise<UploadUrlResponse> {
  return apiFetch<UploadUrlResponse>(
    '/api/v1/books/upload-url',
    jsonBody({ filename: file.name, file_size: file.size, title }),
  );
}

async function putToS3(presignedUrl: string, file: File): Promise<void> {
  // Content-Type must match what the presigned URL was signed with.
  const res = await fetch(presignedUrl, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/pdf' },
    body: file,
  });
  if (!res.ok) {
    throw new ApiError(res.status, 'Direct S3 upload failed');
  }
}

function processBook(bookId: string): Promise<{ book_id: string; task_id: string }> {
  return apiFetch(`/api/v1/books/${bookId}/process`, { method: 'POST' });
}

/**
 * Full upload flow: request presigned URL, push the file to S3, then trigger
 * processing. Returns the book id so the caller can poll status.
 */
export async function uploadAndProcess(file: File, title?: string): Promise<string> {
  const token = tokenStore.access;
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  
  const res = await fetch(`${API_BASE}/api/v1/books/upload`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || 'Upload failed');
  }
  const data = await res.json();
  return data.book_id;
}
/**
 * Poll status until the book reaches a terminal state.
 */
export async function pollUntilDone(
  bookId: string,
  onProgress?: (s: BookStatus) => void,
  intervalMs = 2000,
): Promise<BookStatus> {
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const status = await getBookStatus(bookId);
    onProgress?.(status);
    if (status.status === 'completed' || status.status === 'failed') {
      return status;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

// ---------------------------------------------------------------------------
// Content + adapter
// ---------------------------------------------------------------------------

/**
 * Normalize the known backend page shapes into reader blocks.
 *
 * The app has produced a few content formats over time:
 * - current OCR output: { text, method, confidence }
 * - older/doc format: { paragraphs, is_ocr, confidence }
 * - reader-native format: { blocks, is_ocr, confidence }
 */
function normalizeBlocks(page: BackendPage): ContentBlock[] {
  const source = page.is_ocr || page.method === 'ocr' ? 'ocr' : 'native';

  if (Array.isArray(page.blocks) && page.blocks.length > 0) {
    return page.blocks
      .map((block, i): ContentBlock | null => {
        const content = typeof block.content === 'string' ? block.content : '';
        const type = block.type || 'text';

        if (!['text', 'image', 'formula', 'question'].includes(type)) {
          return null;
        }

        return {
          id: block.id || `p${page.page_number}-b${i}`,
          type,
          content,
          metadata: {
            source,
            confidence: page.confidence ?? undefined,
            ...block.metadata,
          },
        };
      })
      .filter((block): block is ContentBlock => block !== null);
  }

  const rawParagraphs = Array.isArray(page.paragraphs)
    ? page.paragraphs
    : typeof page.text === 'string'
    ? page.text.split(/\n\s*\n/)
    : [];

  const paragraphs = rawParagraphs
    .map((p) => String(p).replace(/\s+/g, ' ').trim())
    .filter((p) => p.length > 0);

  if (paragraphs.length === 0) {
    return [
      {
        id: `p${page.page_number}-empty`,
        type: 'text',
        content: '',
        metadata: { source, confidence: page.confidence ?? undefined },
      },
    ];
  }

  return paragraphs.map((content, i) => ({
    id: `p${page.page_number}-b${i}`,
    type: 'text',
    content,
    metadata: { source, confidence: page.confidence ?? undefined },
  }));
}

function adaptContent(raw: BackendContentResponse): BookContent {
  const pages: PageData[] = (raw.pages || []).map((p) => ({
    page_number: p.page_number,
    blocks: normalizeBlocks(p),
    is_ocr: Boolean(p.is_ocr || p.method === 'ocr'),
    confidence: p.confidence ?? undefined,
  }));

  return {
    book_id: raw.book_id || raw.id || '',
    total_pages: raw.total_pages || pages.length,
    pages,
    metadata: {
      title: raw.metadata?.title || raw.title,
      author: raw.metadata?.author,
      language: raw.metadata?.language,
    },
  };
}

export async function getBookContent(bookId: string): Promise<BookContent> {
  const raw = await apiFetch<BackendContentResponse>(
    `/api/v1/books/${bookId}/content`,
  );
  return adaptContent(raw);
}

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

const API_BASE: string =
  (import.meta as any).env?.VITE_API_URL?.replace(/\/$/, '') ||
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

interface BackendPage {
  page_number: number;
  text: string;
  method: 'direct' | 'ocr' | 'none';
  confidence: number;
}

interface BackendContentResponse {
  id: string;
  title: string;
  status: string;
  total_pages: number;
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

export async function register(
  email: string,
  password: string,
  fullName?: string,
): Promise<void> {
  await apiFetch(
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
  const { book_id, presigned_url } = await getUploadUrl(file, title);
  await putToS3(presigned_url, file);
  await processBook(book_id);
  return book_id;
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
 * Split a page's plain text into paragraph blocks. The backend stores one text
 * blob per page; the reader engine wants discrete blocks.
 */
function textToBlocks(page: BackendPage): ContentBlock[] {
  const source = page.method === 'ocr' ? 'ocr' : 'native';
  const paragraphs = page.text
    .split(/\n\s*\n/)
    .map((p) => p.replace(/\s+/g, ' ').trim())
    .filter((p) => p.length > 0);

  if (paragraphs.length === 0) {
    return [
      {
        id: `p${page.page_number}-empty`,
        type: 'text',
        content: '',
        metadata: { source, confidence: page.confidence },
      },
    ];
  }

  return paragraphs.map((content, i) => ({
    id: `p${page.page_number}-b${i}`,
    type: 'text',
    content,
    metadata: { source, confidence: page.confidence },
  }));
}

function adaptContent(raw: BackendContentResponse): BookContent {
  const pages: PageData[] = (raw.pages || []).map((p) => ({
    page_number: p.page_number,
    blocks: textToBlocks(p),
    is_ocr: p.method === 'ocr',
    confidence: p.confidence,
  }));

  return {
    book_id: raw.id,
    total_pages: raw.total_pages,
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

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  getBookContent,
  listBooks,
  login,
  logout,
  register,
  tokenStore,
} from './client'

// Minimal fetch Response helper for mocking.
function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response

}

describe('api client auth + token flow', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('login stores the access + refresh tokens', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        access_token: 'access-123',
        refresh_token: 'refresh-456',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await login('user@example.com', 'password123')

    expect(tokenStore.access).toBe('access-123')
    expect(tokenStore.refresh).toBe('refresh-456')
    expect(tokenStore.isAuthenticated).toBe(true)

    // login must hit the v1 auth endpoint without an Authorization header.
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/auth/login')
    expect((init.headers as Headers).get('Authorization')).toBeNull()
  })

  it('register posts to the register endpoint and returns the user', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'u1',
        email: 'user@example.com',
        full_name: 'Ada',
        plan_type: 'free',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const user = await register('user@example.com', 'password123', 'Ada')

    expect(user.email).toBe('user@example.com')
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/auth/register')
  })

  it('attaches the bearer token to authenticated requests', async () => {
    tokenStore.set('access-xyz', 'refresh-xyz')
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ items: [], total: 0 }))
    vi.stubGlobal('fetch', fetchMock)

    await listBooks()

    const [, init] = fetchMock.mock.calls[0]
    expect((init.headers as Headers).get('Authorization')).toBe('Bearer access-xyz')
  })

  it('on 401 it refreshes the token once and retries the request', async () => {
    tokenStore.set('stale-access', 'good-refresh')

    const fetchMock = vi
      .fn()
      // 1) original request -> 401
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
      // 2) refresh -> new tokens
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: 'fresh-access',
          refresh_token: 'fresh-refresh',
          token_type: 'bearer',
          expires_in: 3600,
        }),
      )
      // 3) retried original request -> success
      .mockResolvedValueOnce(jsonResponse({ items: [{ id: 'b1' }], total: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await listBooks()

    expect(result.total).toBe(1)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    // The retried call must carry the refreshed token.
    const retryInit = fetchMock.mock.calls[2][1]
    expect((retryInit.headers as Headers).get('Authorization')).toBe(
      'Bearer fresh-access',
    )
    expect(tokenStore.access).toBe('fresh-access')
  })

  it('clears tokens and throws when refresh also fails', async () => {
    tokenStore.set('stale-access', 'bad-refresh')

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: 'invalid refresh' }, 401))
    vi.stubGlobal('fetch', fetchMock)

    await expect(listBooks()).rejects.toBeInstanceOf(ApiError)
    expect(tokenStore.isAuthenticated).toBe(false)
  })

  it('logout always clears local tokens even if the server call fails', async () => {
    tokenStore.set('access', 'refresh')
    const fetchMock = vi.fn().mockRejectedValue(new Error('network down'))
    vi.stubGlobal('fetch', fetchMock)

    await logout()

    expect(tokenStore.isAuthenticated).toBe(false)
  })

  it('surfaces backend error detail as an ApiError', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ detail: 'E-posta zaten kayıtlı' }, 400))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      register('dup@example.com', 'password123'),
    ).rejects.toMatchObject({ status: 400, message: 'E-posta zaten kayıtlı' })
  })
})

describe('content adapter', () => {
  beforeEach(() => {
    localStorage.clear()
    tokenStore.set('access', 'refresh')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('maps backend pages into reader blocks and flags OCR pages', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'book-1',
        title: 'Kitap',
        status: 'completed',
        total_pages: 1,
        metadata: { title: 'Kitap', author: 'Yazar', language: 'tr' },
        pages: [
          {
            page_number: 1,
            text: 'İlk paragraf.\n\nİkinci paragraf.',
            method: 'ocr',
            confidence: 0.9,
          },
        ],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const content = await getBookContent('book-1')

    expect(content.book_id).toBe('book-1')
    expect(content.total_pages).toBe(1)
    expect(content.pages).toHaveLength(1)
    expect(content.pages[0].is_ocr).toBe(true)
    expect(content.pages[0].blocks).toHaveLength(2)
    expect(content.pages[0].blocks[0].content).toBe('İlk paragraf.')
    expect(content.pages[0].blocks[0].metadata?.source).toBe('ocr')
    expect(content.metadata?.author).toBe('Yazar')
  })
})

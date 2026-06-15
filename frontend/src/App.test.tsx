import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the API layer so the component test exercises UI flow, not the network.
// vi.mock is hoisted above imports, so the shared mocks must be created with
// vi.hoisted (also hoisted) to be available inside the factory.
const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  listBooks: vi.fn(),
  auth: { value: false },
}))
const { login, listBooks } = mocks

vi.mock('./api/client', () => {
  class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  }
  return {
    ApiError,
    login: mocks.login,
    listBooks: mocks.listBooks,
    register: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    getBookContent: vi.fn(),
    uploadAndProcess: vi.fn(),
    pollUntilDone: vi.fn(),
    tokenStore: {
      get isAuthenticated() {
        return mocks.auth.value
      },
    },
  }
})

import App from './App'

describe('App auth flow', () => {
  beforeEach(() => {
    mocks.auth.value = false
    login.mockReset()
    listBooks.mockReset()
    listBooks.mockResolvedValue({ items: [], total: 0 })
  })

  it('shows the login screen first', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'FlexiRead' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('E-posta')).toBeInTheDocument()
  })

  it('logs in and moves to the library on success', async () => {
    login.mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByPlaceholderText('E-posta'), 'user@example.com')
    await user.type(
      screen.getByPlaceholderText('Parola (en az 8 karakter)'),
      'password123',
    )
    await user.click(screen.getByRole('button', { name: 'Giriş' }))

    expect(login).toHaveBeenCalledWith('user@example.com', 'password123')
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Kitaplığım' }),
      ).toBeInTheDocument(),
    )
  })

  it('shows the backend error message when login fails', async () => {
    const { ApiError } = (await import('./api/client')) as unknown as {
      ApiError: new (status: number, message: string) => Error
    }
    login.mockRejectedValue(new ApiError(401, 'Geçersiz kimlik bilgileri'))
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByPlaceholderText('E-posta'), 'user@example.com')
    await user.type(
      screen.getByPlaceholderText('Parola (en az 8 karakter)'),
      'password123',
    )
    await user.click(screen.getByRole('button', { name: 'Giriş' }))

    await waitFor(() =>
      expect(screen.getByText('Geçersiz kimlik bilgileri')).toBeInTheDocument(),
    )
    // Still on the auth screen.
    expect(screen.queryByRole('heading', { name: 'Kitaplığım' })).toBeNull()
  })
})

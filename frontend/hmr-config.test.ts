// @vitest-environment node
// Importing the real vite.config pulls in @vitejs/plugin-react -> esbuild,
// which trips a TextEncoder/Uint8Array realm invariant under jsdom. This test
// only inspects config values, so run it in a plain Node environment.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Regression test for the "açılan port hata veriyor" bug.
 *
 * The dev server used to hardcode `hmr.clientPort = 443`. That is only correct
 * behind an HTTPS proxy (GitHub Codespaces). On plain localhost / local Docker
 * there is no server on port 443, so the Vite HMR client spammed the browser
 * console with endless `ws://localhost:443` ERR_CONNECTION_REFUSED errors — the
 * "the opened port errors" symptom.
 *
 * The fix makes the 443 override conditional on the Codespaces environment.
 * These tests lock that behavior in for both environments.
 */
async function loadConfig() {
  vi.resetModules()
  const mod = await import('./vite.config')
  // defineConfig returns the config object verbatim.
  return mod.default as { server: { hmr: unknown } }
}

describe('vite dev server HMR config', () => {
  const originalCodespaces = process.env.CODESPACES
  const originalName = process.env.CODESPACE_NAME

  beforeEach(() => {
    delete process.env.CODESPACES
    delete process.env.CODESPACE_NAME
  })

  afterEach(() => {
    if (originalCodespaces === undefined) delete process.env.CODESPACES
    else process.env.CODESPACES = originalCodespaces
    if (originalName === undefined) delete process.env.CODESPACE_NAME
    else process.env.CODESPACE_NAME = originalName
  })

  it('does NOT pin the HMR client to port 443 on plain localhost', async () => {
    const config = await loadConfig()
    // The bug was `hmr: { clientPort: 443 }`. Locally it must not be that.
    expect(config.server.hmr).not.toMatchObject({ clientPort: 443 })
  })

  it('uses Vite default HMR (true) when not in Codespaces', async () => {
    const config = await loadConfig()
    expect(config.server.hmr).toBe(true)
  })

  it('pins the HMR client to 443 when CODESPACES=true', async () => {
    process.env.CODESPACES = 'true'
    const config = await loadConfig()
    expect(config.server.hmr).toMatchObject({ clientPort: 443 })
  })

  it('pins the HMR client to 443 when CODESPACE_NAME is set', async () => {
    process.env.CODESPACE_NAME = 'fluffy-space-engine-abc123'
    const config = await loadConfig()
    expect(config.server.hmr).toMatchObject({ clientPort: 443 })
  })
})

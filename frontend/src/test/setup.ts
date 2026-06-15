import '@testing-library/jest-dom'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Unmount React trees and clear the jsdom DOM between tests so component tests
// don't leak state into each other.
afterEach(() => {
  cleanup()
})

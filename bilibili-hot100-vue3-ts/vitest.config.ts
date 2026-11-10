import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      // Playwright owns tests/; vitest only runs the co-located unit tests.
      include: ['src/**/*.test.ts'],
      environment: 'node'
    }
  })
)

# E2E Test Framework

FlexiRead için uçtan uca test altyapısı Playwright ile planlanmıştır. Part 4 kapsamında CI/CD ve backend test iskeleti kurulduğu için bu dizin, frontend akışlarını kapsayacak sonraki Playwright senaryolarına ayrılmıştır.

Önerilen komutlar:

```bash
cd frontend
pnpm add -D @playwright/test
pnpm exec playwright install
pnpm exec playwright test
```

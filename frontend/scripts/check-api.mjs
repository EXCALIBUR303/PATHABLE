import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const temporary = mkdtempSync(join(tmpdir(), 'pathable-api-'))
try {
  const target = join(temporary, 'api.generated.ts')
  execFileSync(
    process.execPath,
    ['node_modules/openapi-typescript/bin/cli.js', '../docs/openapi.json', '-o', target],
    { stdio: 'pipe' },
  )
  if (readFileSync(target, 'utf8') !== readFileSync('src/types/api.generated.ts', 'utf8')) {
    console.error('API types are out of date. Run npm run api:generate.')
    process.exitCode = 1
  } else console.log('Generated API types match the backend OpenAPI contract.')
} finally {
  rmSync(temporary, { recursive: true, force: true })
}

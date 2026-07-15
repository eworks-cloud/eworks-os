/**
 * Startup configuration for the Operator Console.
 *
 * Resolves the eworks.db path and access token from the environment. Both are
 * required — there is no hardcoded fallback path, so a missing variable fails
 * loudly instead of silently pointing at the wrong (or no) database.
 */

export type ConsoleConfig = {
  dbPath: string;
  accessToken: string;
};

class MissingConfigError extends Error {
  constructor(varName: string) {
    super(
      `Missing required environment variable: ${varName}. ` +
        'Set it in web/.env.local (see web/.env.example) before starting the console.',
    );
    this.name = 'MissingConfigError';
  }
}

function requireEnv(varName: string): string {
  const value = process.env[varName];
  if (!value || value.trim() === '') {
    throw new MissingConfigError(varName);
  }
  return value;
}

let cachedConfig: ConsoleConfig | undefined;

/** Resolves and caches the console config, throwing if required vars are unset. */
export function getConfig(): ConsoleConfig {
  if (!cachedConfig) {
    cachedConfig = {
      dbPath: requireEnv('EWORKS_DB_PATH'),
      accessToken: requireEnv('OPERATOR_CONSOLE_ACCESS_TOKEN'),
    };
  }
  return cachedConfig;
}

/** Test-only: clears the memoized config so tests can exercise fresh env state. */
export function __resetConfigForTests(): void {
  cachedConfig = undefined;
}

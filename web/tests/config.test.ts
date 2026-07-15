import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { getConfig, __resetConfigForTests } from '../lib/config';

const ORIGINAL_ENV = { ...process.env };

describe('getConfig', () => {
  beforeEach(() => {
    __resetConfigForTests();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    __resetConfigForTests();
    process.env = { ...ORIGINAL_ENV };
  });

  it('resolves dbPath and accessToken from env', () => {
    process.env.EWORKS_DB_PATH = 'data/eworks.db';
    process.env.OPERATOR_CONSOLE_ACCESS_TOKEN = 'test-token';

    expect(getConfig()).toEqual({
      dbPath: 'data/eworks.db',
      accessToken: 'test-token',
    });
  });

  it('throws loudly when EWORKS_DB_PATH is unset', () => {
    delete process.env.EWORKS_DB_PATH;
    process.env.OPERATOR_CONSOLE_ACCESS_TOKEN = 'test-token';

    expect(() => getConfig()).toThrow(/EWORKS_DB_PATH/);
  });

  it('throws loudly when OPERATOR_CONSOLE_ACCESS_TOKEN is unset', () => {
    process.env.EWORKS_DB_PATH = 'data/eworks.db';
    delete process.env.OPERATOR_CONSOLE_ACCESS_TOKEN;

    expect(() => getConfig()).toThrow(/OPERATOR_CONSOLE_ACCESS_TOKEN/);
  });

  it('does not fall back to a hardcoded path when unset', () => {
    delete process.env.EWORKS_DB_PATH;
    delete process.env.OPERATOR_CONSOLE_ACCESS_TOKEN;

    expect(() => getConfig()).toThrow();
  });
});

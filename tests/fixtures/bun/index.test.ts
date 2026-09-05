import { expect, test } from 'bun:test';
import { greeting } from './index';

test('build entry point is usable', () => {
  expect(greeting('workflows')).toBe('hello, workflows');
});

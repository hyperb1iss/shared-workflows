import { createColors } from 'picocolors';

const colors = createColors(false);
export const greeting = (name: string) => colors.magenta(`hello, ${name}`);

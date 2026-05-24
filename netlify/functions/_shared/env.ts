export function getEnv(name: string): string {
  const netlifyEnv = (globalThis as any).Netlify?.env?.get(name);
  return netlifyEnv ?? process.env[name] ?? "";
}


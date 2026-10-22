import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import { site } from './src/site.ts';
import { readFile, rm, writeFile } from 'node:fs/promises';

const redirects = {
  '/about.html': '/posts/java-basics/',
  '/article.html': '/posts/spring-basics/',
  '/tutirial.html': '/posts/spring-mvc-annotations/',
  '/archive.html': '/posts/mybatis-basics/',
};

export default defineConfig({
  site: process.env.SITE_URL || site.url,
  output: 'static',
  trailingSlash: 'ignore',
  build: { format: 'directory' },
  vite: { plugins: [tailwindcss()] },
  markdown: {
    shikiConfig: {
      themes: { light: 'github-light', dark: 'github-dark' },
      wrap: false,
    },
  },
  redirects,
  integrations: [{
    name: 'legacy-html-redirects',
    hooks: {
      'astro:build:done': async ({ dir }) => {
        // Directory builds emit /about.html/index.html; preserve the original file URL.
        for (const path of Object.keys(redirects)) {
          const folder = new URL(`.${path}/`, dir);
          const html = await readFile(new URL('index.html', folder));
          await rm(folder, { recursive: true });
          await writeFile(new URL(`.${path}`, dir), html);
        }
      },
    },
  }],
  devToolbar: { enabled: false },
});

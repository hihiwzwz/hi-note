import type { APIContext } from 'astro';
import { getPosts, postUrl } from '../posts';
import { categories } from '../site';
const escape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');
export async function GET(context: APIContext) {
  const posts = await getPosts();
  const entries = [
    ...['/', '/about/', '/categories/', ...categories.map((category) => `/categories/${category.id}/`)].map((path) => ({ path, date: undefined as string | undefined })),
    ...posts.map((post) => ({ path: postUrl(post), date: post.data.updatedAt ?? post.data.publishedAt })),
  ];
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entries.map(({ path, date }) => `<url><loc>${escape(new URL(path, context.site).href)}</loc>${date ? `<lastmod>${date}</lastmod>` : ''}</url>`).join('')}</urlset>`, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}

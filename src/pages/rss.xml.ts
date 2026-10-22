import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { getPosts, postUrl } from '../posts';
import { site } from '../site';
export async function GET(context: APIContext) {
  const posts = await getPosts();
  return rss({
    title: site.name,
    description: site.description,
    site: context.site!,
    items: posts.filter((post) => post.data.publishedAt).map((post) => ({
      title: post.data.title,
      description: post.data.description,
      link: postUrl(post),
      pubDate: new Date(`${post.data.publishedAt}T00:00:00+08:00`),
    })),
    customData: '<language>zh-cn</language>',
  });
}

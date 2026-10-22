import { getCollection, type CollectionEntry } from 'astro:content';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import { toString } from 'mdast-util-to-string';

export type Post = CollectionEntry<'posts'>;
const migratedIds = new Set(['java-basics', 'spring-basics', 'spring-mvc-annotations', 'mybatis-basics']);

export async function getPosts(): Promise<Post[]> {
  const posts = await getCollection('posts', ({ data }) => !data.draft);
  for (const post of posts) {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(post.id)) {
      throw new Error(`文章文件名请使用小写英文、数字和连字符：${post.id}`);
    }
    if (!post.data.publishedAt && !migratedIds.has(post.id)) {
      throw new Error(`公开文章需要 publishedAt：${post.id}`);
    }
    if (post.data.cover && !existsSync(resolve('public', post.data.cover.slice(1)))) {
      throw new Error(`封面文件不存在：${post.data.cover}`);
    }
  }
  return posts.sort((a, b) => {
    const dateOrder = (b.data.publishedAt ?? '').localeCompare(a.data.publishedAt ?? '');
    return dateOrder || a.id.localeCompare(b.id, 'en');
  });
}

export function postUrl(post: Pick<Post, 'id'>) {
  return `/posts/${post.id}/`;
}

export function plainText(body = '') {
  const tree = unified().use(remarkParse).parse(body);
  type Node = { type: string; value?: string; children?: Node[] };
  function removeHtmlTags(node: Node) {
    if (node.type === 'html') node.value = node.value?.replace(/<[^>]*>/g, ' ');
    node.children?.forEach(removeHtmlTags);
  }
  removeHtmlTags(tree);
  // Separate block nodes so words from adjacent paragraphs do not merge in search.
  return tree.children.map((node) => toString(node, { includeImageAlt: true }))
    .join(' ').replace(/\s+/g, ' ').trim();
}

export function readingMinutes(body = '') {
  const text = plainText(body);
  const chinese = text.match(/\p{Script=Han}/gu)?.length ?? 0;
  const words = text.replace(/\p{Script=Han}/gu, ' ').match(/[\p{L}\p{N}]+/gu)?.length ?? 0;
  return Math.max(1, Math.ceil(chinese / 350 + words / 200));
}

export function formatDate(date: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC',
  }).format(new Date(`${date}T00:00:00Z`));
}

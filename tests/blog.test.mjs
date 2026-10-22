import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { searchPosts, excerpt } from '../src/search.ts';

const dist = resolve('dist');
const read = (path) => readFileSync(join(dist, path), 'utf8');
const ids = ['java-basics', 'mybatis-basics', 'spring-basics', 'spring-mvc-annotations'];

test('migrated articles have content, metadata and valid heading anchors', () => {
  for (const id of ids) {
    const html = read(`posts/${id}/index.html`);
    assert.match(html, /lang="zh-CN"/);
    assert.match(html, /datetime="2022-08-21"/);
    assert.match(html, /class="prose prose-lg article-prose"/);
    assert.match(html, /<h2\b/);
    assert.match(html, /文章目录/);
    assert.equal((html.match(/<h1\b/g) ?? []).length, 1);
    const anchors = [...html.matchAll(/href="#([^"]+)"/g)].map((m) => decodeURIComponent(m[1]));
    for (const anchor of anchors) assert.ok(html.includes(`id="${anchor}"`), `Missing heading ${id}: ${anchor}`);
  }
});

test('homepage, categories, RSS and sitemap include the published notes', () => {
  const home = read('index.html');
  const rss = read('rss.xml');
  const sitemap = read('sitemap.xml');
  for (const id of ids) {
    assert.ok(home.includes(`/posts/${id}/`));
    assert.ok(rss.includes(`/posts/${id}/`));
    assert.ok(sitemap.includes(`/posts/${id}/`));
  }
  for (const id of ['java', 'spring', 'spring-mvc', 'mybatis']) {
    const html = read(`categories/${id}/index.html`);
    const count = (html.match(/data-post-id=/g) ?? []).length;
    assert.ok(count >= 1);
    assert.ok(html.includes(`${count} 篇笔记`));
  }
  assert.doesNotMatch(sitemap, /404\.html|about\.html|search-index|\/search\//);
  assert.match(read('404.html'), /noindex, follow/);
});

test('legacy redirects coexist with the new about page', () => {
  const redirects = { 'about.html': 'java-basics', 'article.html': 'spring-basics', 'tutirial.html': 'spring-mvc-annotations', 'archive.html': 'mybatis-basics' };
  for (const [old, id] of Object.entries(redirects)) {
    const html = read(old);
    assert.match(html, /http-equiv="refresh"/i);
    assert.ok(html.includes(`/posts/${id}/`));
  }
  assert.match(read('about/index.html'), /你好，我是 hiwz/);
  assert.doesNotMatch(read('index.html'), /http-equiv="refresh"/i);
});

test('search covers Chinese body text, case-insensitive terms and empty results', () => {
  const entries = JSON.parse(read('search-index.json'));
  for (const id of ids) assert.ok(entries.some((entry) => entry.id === id));
  assert.ok(searchPosts(entries, '依赖注入').some((entry) => entry.id === 'spring-basics'));
  assert.ok(searchPosts(entries, 'BEANFACTORY').some((entry) => entry.id === 'spring-basics'));
  assert.equal(searchPosts(entries, '持久层')[0].id, 'mybatis-basics');
  assert.deepEqual(searchPosts(entries, '不存在的关键词'), []);
  assert.deepEqual(searchPosts(entries, '   '), []);
  assert.deepEqual(searchPosts(entries, '<script>alert(1)</script>'), []);
  const spring = searchPosts(entries, 'spring BeanFactory');
  assert.ok(spring.some((entry) => entry.id === 'spring-basics'));
  assert.ok(excerpt(spring.find((entry) => entry.id === 'spring-basics'), 'BeanFactory').includes('BeanFactory'));
});

test('search ranks title matches above description and body matches', () => {
  const entries = [
    { id: 'body', title: 'A', description: 'D', body: 'Java' },
    { id: 'description', title: 'B', description: 'Java', body: '' },
    { id: 'title', title: 'Java', description: 'D', body: '' },
  ];
  assert.deepEqual(searchPosts(entries, 'java').map((entry) => entry.id), ['title', 'description', 'body']);
});

function htmlFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? htmlFiles(path) : entry.name.endsWith('.html') ? [path] : [];
  });
}

test('local page links, images and bundled assets resolve in the output', () => {
  for (const path of htmlFiles(dist)) {
    const html = readFileSync(path, 'utf8');
    for (const match of html.matchAll(/(?:href|src)="(\/[^"#?]*)(?:[?#][^"]*)?"/g)) {
      if (match[1].startsWith('//')) continue;
      let target = join(dist, decodeURIComponent(match[1]));
      if (existsSync(target) && statSync(target).isDirectory()) target = join(target, 'index.html');
      assert.ok(existsSync(target), `Broken link in ${path}: ${match[1]}`);
    }
  }
});

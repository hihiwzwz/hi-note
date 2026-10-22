import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { glob } from 'astro/loaders';
import { categories } from './site';

const date = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, '日期格式应为 YYYY-MM-DD').refine(
  (value) => {
    const parsed = new Date(`${value}T00:00:00Z`);
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
  },
  '日期无效',
);

const posts = defineCollection({
  loader: glob({ pattern: '*.md', base: './posts' }),
  schema: z.object({
    title: z.string().trim().min(1),
    description: z.string().trim().min(1),
    category: z.string().refine((id) => categories.some((category) => category.id === id), '请在 src/site.ts 中配置分类'),
    publishedAt: date.optional(),
    updatedAt: date.optional(),
    cover: z.string().regex(/^\/images\/[a-zA-Z0-9/_-]+\.(jpg|jpeg|png|webp|avif)$/).optional(),
    coverAlt: z.string().trim().optional(),
    coverWidth: z.number().int().positive().default(1200),
    coverHeight: z.number().int().positive().default(800),
    draft: z.boolean().default(false),
  }).refine((data) => !data.cover || Boolean(data.coverAlt), '有封面时必须填写 coverAlt')
    .refine((data) => !data.updatedAt || !data.publishedAt || data.updatedAt >= data.publishedAt, '更新时间不能早于发布日期'),
});

export const collections = { posts };

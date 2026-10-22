export const site = {
  name: 'hiwz',
  description: '记录学习，记录生活。把零散的思考，慢慢写成自己的笔记。',
  url: 'https://www.hiwz.net',
  avatar: '/images/avatar.jpg',
  icp: '京ICP备2022023588号',
  navigation: [
    { label: '文章', href: '/' },
    { label: '分类', href: '/categories/' },
    { label: '关于', href: '/about/' },
  ],
};

export const categories = [
  { id: 'java', name: 'Java', description: '语言基础、运行机制与日常积累。' },
  { id: 'spring', name: 'Spring', description: '理解框架，也理解它解决的问题。' },
  { id: 'spring-mvc', name: 'Spring MVC', description: '从一次请求出发，梳理 Web 开发。' },
  { id: 'mybatis', name: 'MyBatis', description: 'SQL、映射与数据持久化。' },
] as const;

export function categoryName(id: string) {
  return categories.find((category) => category.id === id)?.name ?? id;
}

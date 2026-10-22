# hiwz

hiwz 的个人博客，用 Markdown 记录学习笔记和生活。支持文章分类、搜索、RSS 订阅和明暗主题。

网站：[hiwz.net](https://www.hiwz.net/)

## 使用

```sh
npm ci           # 安装依赖
npm run dev      # 本地预览
npm run deploy   # 发布上线
```

文章放在 `posts/`，图片放在 `public/images/文章名/`，网站代码放在 `src/`。图片使用 `/images/文章名/图片.jpg` 引用。

新文章可复制已有 Markdown，修改标题、摘要、分类和发布日期；`draft: true` 的文章不会发布。本地预览地址以终端输出为准，通常是 `http://localhost:4321/`。

## 许可

基于 [notes-website](https://github.com/yyzwz/notes-website)，代码许可见 [LICENSE](LICENSE)。

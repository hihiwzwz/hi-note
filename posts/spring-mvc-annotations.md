---
title: "Spring MVC 常用注解"
description: "记录 Controller、RequestMapping、RequestBody 等常用注解，串起请求映射和参数绑定中的基础概念。"
category: "spring-mvc"
publishedAt: "2022-08-21"
cover: "/images/spring-mvc-annotations/cover.jpg"
coverAlt: "蓝天下向上延伸的现代建筑"
draft: false
---

## SpringMVC常用注解

- @Controller 负责注册一个bean 到spring 上下文中。
- @RequestMapping 注解为控制器指定可以处理哪些 URL 请求。
- @RequestBody 该注解用于读取Request请求的body部分数据，使用系统默认配置的HttpMessageConverter进行解析，然后把相应的数据绑定到要返回的对象上 ，再把HttpMessageConverter返回的对象数据绑定到 controller中方法的参数上。
- @ModelAttribute 在方法定义上使用 @ModelAttribute 注解：Spring MVC 在调用目标处理方法前，会先逐个调用在方法级上标注了@ModelAttribute 的方法。
- @PathVariable 在处理方法入参处使用 @RequestParam 可以把请求参 数传递给请求方法。

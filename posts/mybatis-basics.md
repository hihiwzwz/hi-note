---
title: "MyBatis 入门笔记"
description: "MyBatis 将 POJO 与 SQL 连接起来，减少 JDBC 操作中的重复工作，同时让开发者直接编写和控制查询。这篇笔记记录了 MyBatis 的基本作用，以及它与 Hibernate 在持久化思路上的区别。"
category: "mybatis"
publishedAt: "2022-08-21"
cover: "/images/mybatis-basics/cover.jpg"
coverAlt: "两个人隔着门相互推挡的黑白插画"
coverWidth: 900
coverHeight: 506
draft: false
---

## 什么是MyBatis？

MyBatis 是支持普通 SQL 查询，存储过程和高级映射的优秀持久层框架。 MyBatis 消除了几乎所有的 JDBC 代码和参数的手工设置以及对结果集的检索。 MyBatis 可以使用简单的XML 或注解用于配置和原始映射，将接口和 Java 的 POJO（ Plain Old Java Objects，普通的Java 对象）映射成数据库中的记录.

## mybatis与hibernate的对比？

(1)MyBATIS 目前提供了三种语言实现的版本，包括：Java、.NET以及Ruby

mybatis提供一种“半自动化”的ORM实现。

这里的“半自动化”，是相对Hibernate等提供了全面的数据库封装机制的“全自动化”ORM实现而言，“全自动”ORM实现了POJO和数据库表之间的映射，以及 SQL 的自动生成和执行。

而mybatis的着力点，则在于POJO与SQL之间的映射关系。

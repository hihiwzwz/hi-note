---
title: "我对 Spring 的理解"
description: "从依赖注入到面向切面编程，梳理 Spring 的核心组成，以及各个模块如何为应用开发提供支持。"
category: "spring"
publishedAt: "2022-08-21"
cover: "/images/spring-basics/cover.jpg"
coverAlt: "阳光穿过树林的绿色枝叶"
draft: false
---

## 我对Spring的理解

- 轻量级J2EE应用开发框架
- 主要构成：依赖注入容器，AOP实现、DAO/ORM支持、Web集成
- Core封装包：框架的最基础部分，提供IoC依赖注入特性。这里的基础概念是BeanFactory，它提供对Factory模式的经典实现来消除对程序性单例模式的需要，并真正地允许从成程序逻辑中分分离出依赖关系和配置。
- 构建与Core封装包基础上的Context封装包，提供了一种框架式的对象访问方法，有些像JNDI注册器。Context封装包的特性来自于Beans封装包，并添加了对国际化（I18N）的支持（如资源绑定）时间传播，资源装载的方式和Context的透明创建，比如说通过Servlet容器
- DAO提供了JDBC的抽象层，它可消除冗长的JDBC编码和解析数据库厂商特有的错误代码。并且，JDBC封装包还提供了一种比编程性更好的声明性事务管理方法，不仅仅是实现了特定接口，而且对所有的POJO都适用。
- ORM封装包提供了常用的“对象-关系”映射API的集成层。利用ORM封装包，可以混合使用所有Spring提供的特性进行”对象-关系“映射。如简单声明性事务管理。
- Spring的AOP封装包提供了符合AOP（Aspect—oriented-programming）面向切面编程。
- Spring的Web包提供了基础的针对web开发的集成特性，当与WebWork或struts一起使用Spring时，这个包可以与其他框架结合。
- Spring中的MVC封装包提供了Web应用的Model-View-Controller（MVC）实现。Spring的MVC框架提供了一种清晰的分离模型。Spring的MVC框架提供了一种清晰的分离模型，在领域模型代码和web form之间，并且还可以借助Spring框架的其他特性

## Spring的作用

- IOC控制反转
- 面向切面编程

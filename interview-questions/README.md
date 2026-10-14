# Java 中/高级后端面试题库

> 面向中高级 Java 后端开发岗位，按知识点分类整理，覆盖高频面试真题。

## 知识体系总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     中/高级 Java 后端面试知识体系                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│   │   Java 核心      │    │   Spring 生态    │    │   数据库         │        │
│   │   权重: 30%      │    │   权重: 30%      │    │   权重: 25%      │        │
│   └────────┬────────┘    └────────┬────────┘    └────────┬────────┘        │
│            │                      │                      │                  │
│   ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐        │
│   │ • 基础/集合      │    │ • IoC/AOP       │    │ • MySQL 索引     │        │
│   │ • JVM/内存模型   │    │ • Spring MVC    │    │ • 事务/锁        │        │
│   │ • 并发编程       │    │ • Spring Boot   │    │ • 主从/分库分表  │        │
│   │ • 泛型/反射      │    │ • 事务传播      │    │ • Redis          │        │
│   │ • Java8+ 特性    │    │ • 循环依赖      │    │ • MyBatis        │        │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│                                                                             │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│   │   微服务架构      │    │   分布式/中间件   │    │   场景设计题      │        │
│   │   权重: 30%      │    │   权重: 25%      │    │   权重: 20%      │        │
│   └────────┬────────┘    └────────┬────────┘    └────────┬────────┘        │
│            │                      │                      │                  │
│   ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐        │
│   │ • 服务注册/发现   │    │ • 分布式锁       │    │ • 秒杀系统       │        │
│   │ • 负载均衡       │    │ • 分布式事务     │    │ • 订单超时       │        │
│   │ • 网关/限流      │    │ • 消息队列       │    │ • 权限系统       │        │
│   │ • 链路追踪       │    │ • 分布式ID       │    │ • (扩展中)       │        │
│   │ • 服务熔断降级   │    │ • 缓存设计       │    │                  │        │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  计算机网络  权重: 15%  ·  TCP/HTTP/HTTPS/Cookie-JWT/跨域            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
interview-questions/
├── README.md                           # 本文件 (总览)
├── 01-java-core/                       # Java 核心
│   ├── java-basics.md                  # Java 基础 (String/equals/异常/拷贝)
│   ├── collections-framework.md        # 集合框架 (HashMap/ConcurrentHashMap)
│   ├── concurrency-programming.md      # 并发编程 (锁/线程池/AQS)
│   ├── jvm-memory-model.md             # JVM & 内存模型 (GC/类加载/OOM)
│   ├── generics-reflection.md          # 泛型与反射 (擦除/动态代理)
│   ├── java8-features.md               # Java 8+ (Lambda/Stream/Optional)
│   └── binary-tree.md                  # 二叉树 (遍历/BST/LCA)
├── 02-spring/                          # Spring 生态
│   ├── spring-core.md                  # Spring Core (IoC/AOP/Bean/循环依赖)
│   ├── spring-mvc.md                   # Spring MVC (请求流程/拦截器/异常)
│   ├── spring-boot.md                  # Spring Boot (自动装配/启动流程)
│   └── spring-transaction.md           # Spring 事务 (传播/失效/嵌套)
├── 03-database/                        # 数据库
│   ├── mysql.md                        # MySQL (索引/MVCC/锁/主从/分库分表)
│   ├── redis.md                        # Redis (数据结构/持久化/缓存问题)
│   └── mybatis.md                      # MyBatis (#{} vs ${}/缓存/插件)
├── 04-microservice/                    # 微服务架构
│   ├── service-governance.md           # 服务治理 (Nacos/Gateway/Feign)
│   └── fault-tolerance.md              # 服务容错 (限流/熔断/降级)
├── 05-distributed/                     # 分布式 & 中间件
│   ├── distributed-lock.md             # 分布式锁 (Redisson/RedLock/ZK)
│   ├── distributed-transaction.md      # 分布式事务 (Seata/TCC/Saga)
│   ├── message-queue.md                # 消息队列 (RabbitMQ + Kafka)
│   └── distributed-id.md               # 分布式ID (雪花/Leaf/号段)
├── 06-scenario-design/                 # 场景设计题
│   ├── seckill-system.md               # 秒杀系统设计
│   ├── order-timeout.md                # 订单超时取消方案
│   └── permission-system.md            # 权限系统设计 (RBAC/JWT/数据权限)
└── 07-network/                         # 计算机网络
    └── tcp-http.md                     # TCP/HTTP/HTTPS/Cookie-JWT/跨域
```

## 题目统计

| 知识块 | 文件数 | 题数 | 核心考点 |
|--------|--------|------|----------|
| Java 核心 | 7 | 67 | 基础/集合/并发/JVM/泛型反射/Java8/二叉树 |
| Spring 生态 | 4 | 29 | IoC/AOP/MVC/Boot/事务 |
| 数据库 | 3 | 23 | 索引/MVCC/锁/主从/Redis/MyBatis |
| 微服务架构 | 2 | 10 | 注册中心/网关/限流/熔断 |
| 分布式/中间件 | 4 | 25 | 分布式锁/事务/MQ/ID |
| 场景设计 | 3 | 6+2篇设计文 | 秒杀/订单超时/权限 |
| 计算机网络 | 1 | 9 | TCP/HTTP/HTTPS/鉴权 |
| **合计** | **24** | **约 175** | - |

> 场景设计中的秒杀、订单超时两篇为「架构方案文」体例（方案对比 + 实现 + 总结），不计入 QN 编号。

## 新增/扩充说明

本轮整理相对初版的主要变化：

**新增专题（7 篇）**
- `java-basics.md` — String 不可变、equals/hashCode、异常体系、深浅拷贝
- `java8-features.md` — Lambda/Stream/Optional/invokedynamic
- `generics-reflection.md` — 泛型擦除、PECS、JDK vs CGLIB 动态代理
- `spring-mvc.md` — DispatcherServlet 流程、拦截器、全局异常
- `distributed-lock.md` — Redisson 看门狗、RedLock、ZK/etcd 对比
- `permission-system.md` — RBAC 表设计、JWT 落地、数据权限
- `tcp-http.md` — 三次握手、HTTPS、Cookie/Session/JWT、URL 全链路

**原文件补强**
- `jvm-memory-model.md`：+对象创建、存活判定、JVM 参数、类加载细节
- `collections-framework.md`：+TreeMap、ConcurrentHashMap size、COW、遍历删除
- `mysql.md`：+分库分表实战、主从复制、深分页优化
- `spring-transaction.md`：+REQUIRES_NEW vs NESTED、长事务、事务与锁
- `message-queue.md`：+Kafka 架构、消息不丢、RabbitMQ vs Kafka 选型

## 使用建议

1. **按知识块复习**：每个文件独立完整，可按模块逐个攻克
2. **关注高频题**：文件中标注了 `（高频）`，优先掌握
3. **理解原理**：不要死记硬背，理解底层原理才能应对追问
4. **动手实践**：结合项目经验回答，展示实战能力
5. **场景题当项目讲**：秒杀/权限/订单超时按「方案对比 → 选型理由 → 落地细节」三段式作答

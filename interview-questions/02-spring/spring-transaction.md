# Spring 事务

## Q1: @Transactional 事务传播机制？

| 传播行为 | 说明 |
|----------|------|
| REQUIRED | 有就加入，没有就新建 (默认) |
| SUPPORTS | 有就加入，没有就非事务运行 |
| MANDATORY | 有就加入，没有就抛异常 |
| REQUIRES_NEW | 总是新建，挂起当前事务 |
| NOT_SUPPORTED | 总是非事务，挂起当前事务 |
| NEVER | 总是非事务，有事务就抛异常 |
| NESTED | 有就嵌套事务 (savepoint)，没有就新建 |

### 常用场景

```java
// REQUIRED (默认): 大多数场景
@Transactional(propagation = Propagation.REQUIRED)
public void createOrder() { ... }

// REQUIRES_NEW: 独立事务，不受外层回滚影响
// 例如: 记录操作日志，即使业务回滚，日志也要保留
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void saveLog() { ... }

// NESTED: 嵌套事务，部分回滚
// 例如: 订单创建失败不影响库存扣减记录
@Transactional(propagation = Propagation.NESTED)
public void deductStock() { ... }
```

---

## Q2: @Transactional 失效场景？（高频）

```
┌──────────────────────────────────────────────────────────┐
│              事务失效的 8 种场景                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 方法不是 public                                      │
│     └─▶ Spring AOP 只能代理 public 方法                  │
│                                                          │
│  2. 自调用 (this 调用)                                   │
│     └─▶ methodA() 调用 this.methodB()                   │
│     └─▶ 不走代理，事务不生效                             │
│     └─▶ 解决: 注入自身 / AopContext.currentProxy()      │
│                                                          │
│  3. 异常被 catch 吞掉                                    │
│     └─▶ catch 后没有 rethrow，Spring 不知道要回滚        │
│                                                          │
│  4. 抛出的是 checked exception                            │
│     └─▶ 默认只回滚 RuntimeException 和 Error             │
│     └─▶ 解决: @Transactional(rollbackFor=Exception.class)│
│                                                          │
│  5. 数据库引擎不支持事务 (MyISAM)                        │
│                                                          │
│  6. 非 Spring 管理的 Bean                                │
│                                                          │
│  7. 多线程调用                                           │
│     └─▶ 新线程不在同一个事务中                           │
│                                                          │
│  8. propagation 设置不当 (如 REQUIRES_NEW)               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 自调用问题详解

```java
@Service
public class OrderService {

    @Transactional
    public void createOrder() {
        // 业务逻辑
        this.updateStock();  // ❌ 自调用，事务不生效
    }

    @Transactional
    public void updateStock() {
        // 库存扣减
    }
}

// 解决方案 1: 注入自身
@Service
public class OrderService {

    @Autowired
    private OrderService self;  // 注入代理对象

    @Transactional
    public void createOrder() {
        self.updateStock();  // ✅ 走代理
    }
}

// 解决方案 2: AopContext
@EnableAspectJAutoProxy(exposeProxy = true)  // 需要开启
@Service
public class OrderService {

    @Transactional
    public void createOrder() {
        OrderService proxy = (OrderService) AopContext.currentProxy();
        proxy.updateStock();  // ✅ 走代理
    }
}

// 解决方案 3: 抽取到另一个 Service
@Service
public class StockService {

    @Transactional
    public void updateStock() {
        // 库存扣减
    }
}
```

---

## Q3: @Transactional 的 rollbackFor 属性？

```java
// ❌ 错误: 默认只回滚 RuntimeException
@Transactional
public void createOrder() throws Exception {
    // ...
    throw new Exception("业务异常");  // 不会回滚!
}

// ✅ 正确: 指定 rollbackFor
@Transactional(rollbackFor = Exception.class)
public void createOrder() throws Exception {
    // ...
    throw new Exception("业务异常");  // 会回滚
}
```

### 回滚规则

| 异常类型 | 默认行为 | 指定 rollbackFor 后 |
|----------|----------|---------------------|
| RuntimeException | 回滚 | 回滚 |
| Error | 回滚 | 回滚 |
| checked Exception | 不回滚 | 回滚 |

---

## Q4: 事务隔离级别在 Spring 中如何配置？

```java
// 方法级别配置
@Transactional(isolation = Isolation.READ_COMMITTED)
public void queryData() { ... }

// Spring 支持的隔离级别
public enum Isolation {
    DEFAULT(-1),           // 使用数据库默认级别
    READ_UNCOMMITTED(1),   // 读未提交
    READ_COMMITTED(2),     // 读已提交
    REPEATABLE_READ(4),    // 可重复读
    SERIALIZABLE(8);       // 串行化
}
```

### MySQL 默认隔离级别

> "MySQL InnoDB 默认是 REPEATABLE READ，但通过 MVCC + Next-Key Lock 实际上解决了大部分幻读问题。Spring 中如果不指定，默认使用数据库的隔离级别。"

---

## Q5: 编程式事务 vs 声明式事务？

```java
// 声明式事务 (推荐)
@Transactional
public void createOrder() {
    // 业务逻辑
}

// 编程式事务 (灵活)
@Service
public class OrderService {

    @Autowired
    private TransactionTemplate transactionTemplate;

    public void createOrder() {
        transactionTemplate.execute(status -> {
            try {
                // 业务逻辑
                return null;
            } catch (Exception e) {
                status.setRollbackOnly();  // 手动标记回滚
                throw e;
            }
        });
    }
}

// PlatformTransactionManager 方式 (更底层)
@Service
public class OrderService {

    @Autowired
    private PlatformTransactionManager transactionManager;

    public void createOrder() {
        TransactionStatus status = transactionManager.getTransaction(
            new DefaultTransactionDefinition());
        try {
            // 业务逻辑
            transactionManager.commit(status);
        } catch (Exception e) {
            transactionManager.rollback(status);
            throw e;
        }
    }
}
```

### 对比

| 维度 | 声明式事务 | 编程式事务 |
|------|------------|------------|
| 使用方式 | @Transactional 注解 | TransactionTemplate |
| 侵入性 | 低 | 高 |
| 灵活性 | 一般 | 高 |
| 粒度 | 方法级别 | 代码块级别 |
| 推荐场景 | 大多数场景 | 需要细粒度控制 |

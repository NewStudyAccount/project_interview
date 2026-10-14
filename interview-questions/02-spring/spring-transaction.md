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

---

## Q6: 事务嵌套/传播行为实战场景？REQUIRES_NEW 和 NESTED 区别？（高频）

### REQUIRES_NEW vs NESTED

| 维度 | REQUIRES_NEW | NESTED |
|------|--------------|--------|
| 实现机制 | 挂起当前事务，新建独立事务 | 在当前事务内建 Savepoint |
| 连接 | 可能用新连接 (需要两个连接) | 始终同一个连接 |
| 外层回滚时 | 内层已提交的 **不受影响** | 内层 **一起回滚** |
| 内层回滚时 | 只回滚内层，外层继续 | 只回滚到 Savepoint，外层继续 |
| 依赖 | 无特殊要求 | 数据库支持 Savepoint (InnoDB 支持) |
| 死锁风险 | 更高 (两个连接互相等锁) | 更低 (单连接) |

### 实战场景

```java
@Service
public class OrderService {

    @Autowired
    private OrderMapper orderMapper;
    @Autowired
    private LogService logService;
    @Autowired
    private StockService stockService;

    // 主流程: 创建订单 + 扣库存 + 记日志
    @Transactional(rollbackFor = Exception.class)
    public void createOrder(Order order) {
        orderMapper.insert(order);

        // 场景 1: REQUIRES_NEW —— 日志独立提交
        // 即使后续库存扣减失败、订单回滚，操作日志也要保留
        logService.saveOpLog(order);   // 内部 REQUIRES_NEW

        // 场景 2: NESTED —— 库存扣减可部分回滚
        // 扣库存失败只回滚扣减动作，订单本身可继续或整体回滚
        try {
            stockService.deduct(order);  // 内部 NESTED
        } catch (Exception e) {
            // 记录失败原因，但不强制中断
            log.warn("库存扣减失败", e);
        }
    }
}

@Service
public class LogService {
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void saveOpLog(Order order) {
        logMapper.insert(new OpLog(order));
    }
}

@Service
public class StockService {
    @Transactional(propagation = Propagation.NESTED)
    public void deduct(Order order) {
        stockMapper.deduct(order.getSkuId(), order.getQty());
    }
}
```

### 流程对比图

```
┌──────────────────────────────────────────────────────────┐
│           REQUIRES_NEW vs NESTED 回滚边界                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  REQUIRES_NEW:                                            │
│  ┌──────────────┐     ┌──────────────┐                   │
│  │ 外层事务      │     │ 内层新事务    │  (独立连接)       │
│  │ insert order │     │ insert log   │                   │
│  │     │        │     │   COMMIT ✅  │ ← 日志保留        │
│  │  失败回滚 ❌ │     │              │                   │
│  │  (不影响内层)│     └──────────────┘                   │
│  └──────────────┘                                        │
│                                                          │
│  NESTED:                                                  │
│  ┌──────────────────────────────────────┐                │
│  │ 外层事务                              │                │
│  │  insert order                         │                │
│  │  ┌─ SAVEPOINT ─────────────────────┐  │                │
│  │  │  deduct stock                   │  │                │
│  │  │  失败 → ROLLBACK TO SAVEPOINT   │  │                │
│  │  │  (只回滚扣减，外层继续)         │  │                │
│  │  └─────────────────────────────────┘  │                │
│  │  外层 COMMIT ✅ (订单仍可成功)        │                │
│  └──────────────────────────────────────┘                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试答法

> "REQUIRES_NEW 会挂起当前事务、新开一个独立事务，甚至可能用新的数据库连接，内层提交后外层再失败也影响不到它，适合记审计日志这种必须落库的场景。NESTED 是在当前事务里打 Savepoint，内层失败只回滚到保存点，外层还可以继续；但外层整体回滚时内层也会回滚。选型原则：需要绝对独立就用 REQUIRES_NEW，只需要局部回滚就用 NESTED。注意 REQUIRES_NEW 会多占连接、增加死锁风险，高并发下要谨慎。"

### 面试关键点

> "Spring 里事务传播是面试高频。除了记住定义，要能举出真实场景：日志/审计用 REQUIRES_NEW，批量子任务部分失败用 NESTED。还要点出自调用会导致传播失效，以及 REQUIRES_NEW 的连接开销。"

---

## Q7: 长事务问题？如何避免？

### 长事务的危害

```
┌──────────────────────────────────────────────────────────┐
│                    长事务的危害                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 连接长时间占用                                        │
│     └─▶ 连接池耗尽，拖垮整个应用                          │
│                                                          │
│  2. 锁持有时间变长                                        │
│     └─▶ 行锁/间隙锁不释放，并发度骤降                     │
│                                                          │
│  3. 主从延迟                                              │
│     └─▶ 大事务导致从库回放慢，读写分离不一致              │
│                                                          │
│  4. 回滚时间长                                            │
│     └─▶ 失败时 undo log 回滚耗时，故障恢复慢              │
│                                                          │
│  5. undo / redo 日志膨胀                                  │
│     └─▶ undo 段无法清理，磁盘与内存压力                    │
│                                                          │
│  6. 死锁概率上升                                          │
│     └─▶ 持锁越久越容易和其他事务互相等待                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 典型反模式

```java
// ❌ 反模式 1: 事务里做 RPC / 调用第三方
@Transactional
public void placeOrder(Order order) {
    orderMapper.insert(order);
    paymentClient.charge(order);      // 网络调用，可能几十秒
    inventoryClient.deduct(order);
    smsClient.send(order.getPhone()); // 又一次 RPC
}

// ❌ 反模式 2: 事务里处理大量数据 / 慢查询
@Transactional
public void importUsers(List<User> list) {
    for (User u : list) {
        userMapper.insert(u);  // 几万条，事务一直不提交
    }
}

// ❌ 反模式 3: 事务里做文件 IO / 生成报表
@Transactional
public void exportReport() {
    List<Data> rows = dataMapper.selectAll();
    writeExcel(rows);  // 写文件很慢
}
```

### 正确做法

```java
// ✅ 缩小事务边界: 只包住 DB 操作
public void placeOrder(Order order) {
    // 1. 事务外: 准备数据、调用 RPC (或改为异步/最终一致)
    String payNo = paymentClient.charge(order);

    // 2. 事务内: 只做本地 DB 写入
    orderService.saveOrder(order, payNo);

    // 3. 事务后: 通知、短信、事件发布
    eventPublisher.publishEvent(new OrderCreatedEvent(order));
    smsAsync.send(order.getPhone());
}

@Transactional(rollbackFor = Exception.class)
public void saveOrder(Order order, String payNo) {
    orderMapper.insert(order);
    payLogMapper.insert(new PayLog(payNo, order));
}

// ✅ 大批量分片提交
public void importUsers(List<User> list) {
    Lists.partition(list, 500).forEach(batch -> {
        userMapper.batchInsert(batch);  // 每批独立事务
    });
}
```

### 排查手段

| 手段 | 命令/工具 | 看什么 |
|------|-----------|--------|
| MySQL 活跃事务 | `SELECT * FROM information_schema.innodb_trx` | `trx_started` 超过阈值的事务 |
| 锁等待 | `SELECT * FROM sys.innodb_lock_waits` | 谁在等谁的锁 |
| 慢查询 | `SHOW PROCESSLIST` / 慢日志 | 执行中的长 SQL |
| 应用侧 | Druid / HikariCP 监控 | 连接占用时长 |
| 链路追踪 | SkyWalking / Zipkin | 事务方法内是否夹带 RPC |

### 面试答法

> "长事务本质是把不该包在一起的操作放进了同一个事务。典型问题是事务里调 RPC、发短信、写文件。危害包括连接池耗尽、锁持有过久、主从延迟、回滚慢。解决思路是缩小事务边界：只把本地 DB 写操作放进 @Transactional，RPC 和通知放到事务外或走最终一致；批量数据分片提交。排查可以用 information_schema.innodb_trx 看活跃事务时长，结合应用连接池监控。"

---

## Q8: 事务与锁的顺序问题？死锁如何与事务一起排查？

### 事务与锁的关系

```
┌──────────────────────────────────────────────────────────┐
│               事务持锁与死锁形成                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  事务 A                          事务 B                   │
│  BEGIN                           BEGIN                    │
│  UPDATE t SET ... WHERE id=1     UPDATE t SET ...         │
│  → 拿到 id=1 行锁                → 拿到 id=2 行锁         │
│  UPDATE ... WHERE id=2           UPDATE ... WHERE id=1    │
│  → 等待 id=2 锁                  → 等待 id=1 锁           │
│         │                                │                │
│         └────────── 互相等待 ────────────┘                │
│                    DEADLOCK                               │
│                                                          │
│  根因: 加锁顺序不一致 + 事务过大持锁过久                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 代码层面的顺序问题

```java
// ❌ 两个方法以相反顺序更新同一组记录
@Transactional
public void transfer(Long from, Long to, BigDecimal amt) {
    accountMapper.deduct(from, amt);  // 先锁 from
    accountMapper.add(to, amt);       // 再锁 to
}

@Transactional
public void reverseTransfer(Long from, Long to, BigDecimal amt) {
    accountMapper.deduct(to, amt);    // 先锁 to  ← 顺序反了
    accountMapper.add(from, amt);     // 再锁 from
}

// ✅ 固定加锁顺序: 按主键/编号升序加锁
@Transactional
public void transfer(Long from, Long to, BigDecimal amt) {
    if (from < to) {
        accountMapper.deduct(from, amt);
        accountMapper.add(to, amt);
    } else {
        accountMapper.add(to, amt);
        accountMapper.deduct(from, amt);
    }
}

// ✅ 或用 SELECT ... FOR UPDATE 先按固定顺序取锁
@Transactional
public void transfer(Long from, Long to, BigDecimal amt) {
    List<Long> ids = Stream.of(from, to).sorted().collect(Collectors.toList());
    accountMapper.selectForUpdate(ids);  // 统一顺序加锁
    accountMapper.deduct(from, amt);
    accountMapper.add(to, amt);
}
```

### 死锁排查流程

```
┌──────────────────────────────────────────────────────────┐
│              死锁 + 事务 联合排查步骤                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 确认是否死锁                                          │
│     ├── 应用日志: DeadlockLoserDataAccessException        │
│     └── MySQL:  SHOW ENGINE INNODB STATUS                 │
│         └─▶ LATEST DETECTED DEADLOCK 段落                │
│                                                          │
│  2. 还原两个事务的加锁顺序                                │
│     ├── 从死锁日志看: 各自持有/等待哪些锁                 │
│     └── 对应到业务 SQL (索引、扫描范围)                   │
│                                                          │
│  3. 看事务边界是否过大                                    │
│     ├── innodb_trx 里 trx_started / trx_rows_modified    │
│     └── 事务内是否夹了 RPC / 循环慢操作                   │
│                                                          │
│  4. 解决方案                                              │
│     ├── 统一加锁顺序 (按 id 升序)                         │
│     ├── 缩小事务粒度，尽快提交                            │
│     ├── 降低隔离级别 (如 RR → RC，减少间隙锁)             │
│     ├── 使用乐观锁 (version 字段) 替代部分悲观锁          │
│     ├── 合理建索引，避免锁升级为间隙锁/表锁               │
│     └── 必要时业务层重试死锁                              │
│                                                          │
│  5. 验证                                                  │
│     ├── 压测复现场景                                      │
│     └── 监控死锁次数归零                                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 死锁日志关键信息

```sql
-- 查看最近一次死锁
SHOW ENGINE INNODB STATUS\G

-- 活跃事务与持锁
SELECT * FROM information_schema.innodb_trx;

-- 锁等待关系
SELECT * FROM sys.innodb_lock_waits;

-- 开启死锁全量记录 (建议生产开启)
-- innodb_print_all_deadlocks = ON
```

### 面试答法

> "死锁和事务强相关：事务越大、持锁越久，越容易和其他事务形成环形等待。根因通常是加锁顺序不一致。排查上，应用层捕获 DeadlockLoserDataAccessException，数据库层看 SHOW ENGINE INNODB STATUS 里的 LATEST DETECTED DEADLOCK，再结合 information_schema.innodb_trx 看长事务。解决靠三板斧：统一加锁顺序、缩小事务、必要时乐观锁或业务重试。"

### 面试关键点

> "要能连起来讲：长事务放大锁持有时间 → 加锁顺序不一致 → 死锁。给出具体代码级的顺序修复方案（按 id 排序后 FOR UPDATE），并提到 RC 比 RR 间隙锁更少、innodb_print_all_deadlocks 排查手段。"

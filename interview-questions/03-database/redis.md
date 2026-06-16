# Redis

## Q1: Redis 数据结构及使用场景？

| 数据结构 | 底层实现 | 典型场景 |
|----------|----------|----------|
| String | SDS | 缓存、计数器、分布式锁 |
| Hash | ziplist / hashtable | 对象存储、购物车 |
| List | ziplist / quicklist | 消息队列、最新列表 |
| Set | intset / hashtable | 标签、共同好友 |
| ZSet | ziplist / skiplist+hashtable | 排行榜、延迟队列 |
| Bitmap | String | 签到、在线状态 |
| HyperLogLog | 概率算法 | UV 统计 (误差 0.81%) |
| Stream | radix tree + listpack | 消息队列 (5.0+) |

---

## Q2: Redis 持久化？RDB vs AOF？

```
┌──────────────────────────────────────────────────────────┐
│                  Redis 持久化对比                         │
├──────────────┬───────────────────┬───────────────────────┤
│     维度      │      RDB          │       AOF             │
├──────────────┼───────────────────┼───────────────────────┤
│  原理        │ 定时快照           │ 追加写命令            │
│  触发方式    │ save/bgsave/自动   │ always/everysec/no    │
│  文件大小    │ 小 (二进制压缩)    │ 大 (文本命令)         │
│  恢复速度    │ 快                 │ 慢                    │
│  数据安全    │ 可能丢失两次快照间 │ 最多丢 1 秒数据       │
│  性能影响    │ fork 时阻塞        │ 持续写入，影响较小     │
│  适用场景    │ 备份、灾难恢复     │ 数据安全性要求高       │
└──────────────┴───────────────────┴───────────────────────┘

混合持久化 (Redis 4.0+, 推荐):
├── AOF 重写时，前半部分用 RDB 格式，后半部分用 AOF 格式
├── 兼顾恢复速度和数据安全
└── aof-use-rdb-preamble yes
```

### RDB 配置

```conf
# 自动触发
save 900 1      # 900 秒内至少 1 个 key 变化
save 300 10     # 300 秒内至少 10 个 key 变化
save 60 10000   # 60 秒内至少 10000 个 key 变化

# bgsave 流程
1. fork 子进程
2. 子进程遍历内存，写入 RDB 文件
3. 写完后替换旧 RDB 文件
```

### AOF 配置

```conf
appendonly yes
appendfsync everysec  # 推荐: 每秒同步一次

# AOF 重写
auto-aof-rewrite-percentage 100  # 文件增长 100% 触发
auto-aof-rewrite-min-size 64mb   # 最小 64MB
```

---

## Q3: 内存淘汰策略？

Redis 4.0+ 提供 8 种淘汰策略:

| 策略 | 范围 | 淘汰规则 |
|------|------|----------|
| noeviction | - | 不淘汰，写入报错 (默认) |
| allkeys-lru | 所有 key | LRU 最近最少使用 |
| allkeys-lfu | 所有 key | LFU 最不经常使用 (4.0+) |
| allkeys-random | 所有 key | 随机淘汰 |
| volatile-lru | 设置过期的 key | LRU |
| volatile-lfu | 设置过期的 key | LFU (4.0+) |
| volatile-random | 设置过期的 key | 随机 |
| volatile-ttl | 设置过期的 key | TTL 最小的 |

### 面试答法

> "推荐使用 allkeys-lru 或 allkeys-lfu。如果业务中有明确的热点数据，用 lfu 更合适；如果访问模式接近 LRU 假设，用 lru。注意 lru 和 lfu 的区别：LRU 是最近最少使用，LFU 是最不经常使用。LFU 在 Redis 4.0 引入，通过概率计数器实现。"

---

## Q4: 缓存穿透、击穿、雪崩？

```
┌──────────────────────────────────────────────────────────┐
│              缓存三大问题                                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  穿透 (查不存在的数据)                                    │
│  ┌──────┐   查询   ┌──────┐   查询   ┌──────┐          │
│  │Client│────────▶│Redis │  miss   │ MySQL│          │
│  └──────┘         └──────┘────────▶└──────┘          │
│  每次都穿透到 DB                                         │
│  解决: ① 布隆过滤器 ② 缓存空值 (短 TTL)                 │
│                                                          │
│  击穿 (热点 key 过期)                                    │
│  ┌──────┐   ┌──────┐   ┌──────┐                        │
│  │ T1   │──▶│      │──▶│      │                        │
│  │ T2   │──▶│Redis │──▶│ MySQL│  大量并发打到 DB        │
│  │ T3   │──▶│(miss)│──▶│      │                        │
│  └──────┘   └──────┘   └──────┘                        │
│  解决: ① 互斥锁 (setnx) ② 逻辑过期 ③ 永不过期          │
│                                                          │
│  雪崩 (大面积 key 同时过期 / Redis 宕机)                  │
│  ┌──────┐         ┌──────┐                              │
│  │Client│────────▶│Redis │  全部 miss                   │
│  └──────┘         └──────┘                              │
│     │                   │                               │
│     ▼                   ▼                               │
│  ┌──────┐         ┌──────┐  大量请求打到 DB             │
│  │Client│────────▶│MySQL │                              │
│  └──────┘         └──────┘                              │
│  解决: ① 随机过期时间 ② 多级缓存 ③ 限流降级             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 代码示例

```java
// 缓存穿透: 缓存空值
public User getUser(Long id) {
    String key = "user:" + id;
    String value = redis.get(key);
    if (value != null) {
        if ("NULL".equals(value)) return null;
        return JSON.parseObject(value, User.class);
    }
    // 缓存 miss, 查 DB
    User user = userMapper.selectById(id);
    if (user == null) {
        // 缓存空值, 设置短 TTL
        redis.setex(key, 300, "NULL");
        return null;
    }
    redis.setex(key, 3600, JSON.toJSONString(user));
    return user;
}

// 缓存击穿: 互斥锁
public User getUserWithLock(Long id) {
    String key = "user:" + id;
    String value = redis.get(key);
    if (value != null) return JSON.parseObject(value, User.class);

    String lockKey = "lock:user:" + id;
    boolean locked = redis.setnx(lockKey, "1", 10);
    if (locked) {
        try {
            User user = userMapper.selectById(id);
            redis.setex(key, 3600, JSON.toJSONString(user));
            return user;
        } finally {
            redis.del(lockKey);
        }
    } else {
        // 等待后重试
        Thread.sleep(50);
        return getUserWithLock(id);
    }
}

// 缓存雪崩: 随机过期时间
int baseTTL = 3600;
int randomTTL = new Random().nextInt(600); // 0-600 秒随机
redis.setex(key, baseTTL + randomTTL, value);
```

---

## Q5: Redis 分布式锁实现？

```
┌──────────────────────────────────────────────────────────┐
│              Redis 分布式锁方案                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  基础版:                                                 │
│  SET key value NX EX 30                                  │
│  ├── NX: 不存在才设置 (互斥)                             │
│  ├── EX: 设置过期时间 (防死锁)                           │
│  └── value: 唯一标识 (UUID, 防误删)                      │
│                                                          │
│  释放锁 (Lua 脚本保证原子性):                            │
│  if redis.call('get', KEYS[1]) == ARGV[1] then          │
│      return redis.call('del', KEYS[1])                   │
│  else                                                    │
│      return 0                                            │
│  end                                                     │
│                                                          │
│  进阶问题:                                               │
│  ├── 锁过期但业务没完成 → 看门狗机制 (Redisson)          │
│  ├── Redis 主从切换丢锁 → RedLock (争议大)               │
│  └── 可重入 → Hash 结构记录重入次数                     │
│                                                          │
│  推荐: 直接用 Redisson                                   │
│  ├── 看门狗自动续期                                      │
│  ├── 可重入锁                                            │
│  ├── 读写锁 / 信号量 / 闭锁                             │
│  └── RedLock 支持                                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Redisson 分布式锁使用

```java
@Autowired
private RedissonClient redisson;

public void deductStock() {
    RLock lock = redisson.getLock("lock:stock:" + skuId);
    try {
        // 尝试获取锁, 等待 3 秒, 锁自动过期 30 秒
        boolean locked = lock.tryLock(3, 30, TimeUnit.SECONDS);
        if (!locked) {
            throw new RuntimeException("获取锁失败");
        }
        // 业务逻辑
        Stock stock = stockMapper.selectById(skuId);
        stock.setQuantity(stock.getQuantity() - 1);
        stockMapper.updateById(stock);
    } finally {
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
```

---

## Q6: Redis 集群模式？

```
┌──────────────────────────────────────────────────────────┐
│              Redis 三种集群模式                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  主从复制 (Replication):                                 │
│  ┌──────┐     ┌──────┐     ┌──────┐                    │
│  │Master│────▶│Slave1│     │Slave2│                    │
│  └──────┘     └──────┘     └──────┘                    │
│  ├── 读写分离, 主写从读                                 │
│  ├── 主挂了需要手动切换                                 │
│  └── 数据复制有延迟                                     │
│                                                          │
│  哨兵模式 (Sentinel):                                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │Sentinel1│  │Sentinel2│  │Sentinel3│                 │
│  └────┬────┘  └────┬────┘  └────┬────┘                 │
│       │            │            │                       │
│       └────────────┼────────────┘                       │
│                    │ 监控                                │
│       ┌────────────┼────────────┐                       │
│       ▼            ▼            ▼                       │
│  ┌──────┐     ┌──────┐     ┌──────┐                    │
│  │Master│────▶│Slave1│     │Slave2│                    │
│  └──────┘     └──────┘     └──────┘                    │
│  ├── 自动故障转移                                       │
│  ├── 奇数个哨兵 (>=3)                                   │
│  └── 单主瓶颈                                           │
│                                                          │
│  Cluster:                                                │
│  ┌──────┐     ┌──────┐     ┌──────┐                    │
│  │Node1 │────▶│Node2 │────▶│Node3 │                    │
│  │16384 │     │16384 │     │16384 │                    │
│  │slots │     │slots │     │slots │                    │
│  └──────┘     └──────┘     └──────┘                    │
│  ├── 数据分片 (16384 个 slot)                           │
│  ├── 自动故障转移                                       │
│  ├── 去中心化                                           │
│  └── 推荐生产使用                                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Cluster 分片原理

```
slot = CRC16(key) % 16384

Node1: slot 0-5460
Node2: slot 5461-10922
Node3: slot 10923-16383

相同 slot 的 key 在同一节点，避免跨节点操作。
```

---

## Q7: Redis 延迟队列怎么实现？

```
┌──────────────────────────────────────────────────────────┐
│              Redis 延迟队列方案                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  方案一: ZSet 实现                                       │
│  ┌──────────────────────────────────────────────────┐    │
│  │  生产者:                                          │    │
│  │  ZADD delay_queue <timestamp> <message>          │    │
│  │                                                  │    │
│  │  消费者 (定时轮询):                               │    │
│  │  ZRANGEBYSCORE delay_queue 0 <current_timestamp> │    │
│  │  ├── 有到期消息 → ZREM 删除并处理                 │    │
│  │  └── 无消息 → sleep                              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  方案二: RabbitMQ 死信队列                               │
│  ┌──────────────────────────────────────────────────┐    │
│  │  订单创建 → 正常队列 (TTL=30min)                  │    │
│  │                    │                              │    │
│  │                    ▼ (过期)                        │    │
│  │              死信队列 (DLQ)                        │    │
│  │                    │                              │    │
│  │                    ▼                              │    │
│  │              消费者: 查询订单状态                  │    │
│  │              ├── 未支付 → 取消订单, 释放库存      │    │
│  │              └── 已支付 → 忽略                    │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  方案三: Redisson 延迟队列                               │
│  RBlockingQueue<Object> queue = ...;                    │
│  RBlockingQueue<Object> destinationQueue = ...;         │
│  RDelayedQueue<Object> delayedQueue =                   │
│      redisson.getDelayedQueue(queue);                   │
│                                                          │
│  // 延迟 30 分钟                                        │
│  delayedQueue.offer(message, 30, TimeUnit.MINUTES);     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

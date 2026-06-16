# 分布式 ID

## Q1: 分布式 ID 方案对比？

| 方案 | 性能 | 有序 | 问题 |
|------|------|------|------|
| UUID | 高 | 无序 | 索引不友好 |
| 数据库自增 | 低 | 有序 | 单点瓶颈 |
| 数据库号段 | 中 | 趋势有序 | 需要实现 |
| Redis INCR | 高 | 有序 | Redis 依赖 |
| 雪花算法 | 高 | 趋势有序 | 时钟回拨问题 |
| Leaf | 高 | 有序 | 美团开源，推荐 |

---

## Q2: 雪花算法原理？

```
┌──────────────────────────────────────────────────────────┐
│              雪花算法 (Snowflake) 结构                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  0 │ 41位时间戳 │ 10位机器ID │ 12位序列号               │
│  ▲                                                       │
│  符号位 (0)                                              │
│                                                          │
│  41位时间戳: 毫秒级，可用 69 年                          │
│  10位机器ID: 5位数据中心 + 5位机器 = 1024 台机器         │
│  12位序列号: 每毫秒可生成 4096 个 ID                     │
│                                                          │
│  单机每秒可生成: 4096 * 1000 = 409.6 万个 ID            │
│                                                          │
│  问题: 时钟回拨                                         │
│  ├── 服务器时间被调整到过去                              │
│  ├── 可能生成重复 ID                                    │
│  └── 解决: 抛异常 / 等待 / 扩展位预留                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 雪花算法实现

```java
public class SnowflakeIdGenerator {

    // 起始时间戳 (2020-01-01 00:00:00)
    private final long startTimestamp = 1577808000000L;

    // 各部分位数
    private final long machineIdBits = 5L;
    private final long datacenterIdBits = 5L;
    private final long sequenceBits = 12L;

    // 最大值
    private final long maxMachineId = ~(-1L << machineIdBits); // 31
    private final long maxDatacenterId = ~(-1L << datacenterIdBits); // 31
    private final long sequenceMask = ~(-1L << sequenceBits); // 4095

    // 左移位数
    private final long machineIdShift = sequenceBits; // 12
    private final long datacenterIdShift = sequenceBits + machineIdBits; // 17
    private final long timestampShift = sequenceBits + machineIdBits + datacenterIdBits; // 22

    private long machineId;
    private long datacenterId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();

        if (timestamp < lastTimestamp) {
            throw new RuntimeException("时钟回拨");
        }

        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & sequenceMask;
            if (sequence == 0) {
                timestamp = waitNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0L;
        }

        lastTimestamp = timestamp;

        return ((timestamp - startTimestamp) << timestampShift)
                | (datacenterId << datacenterIdShift)
                | (machineId << machineIdShift)
                | sequence;
    }

    private long waitNextMillis(long lastTimestamp) {
        long timestamp = System.currentTimeMillis();
        while (timestamp <= lastTimestamp) {
            timestamp = System.currentTimeMillis();
        }
        return timestamp;
    }
}
```

---

## Q3: 美团 Leaf 方案？

```
┌──────────────────────────────────────────────────────────┐
│              Leaf 两种模式                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Leaf-segment (号段模式):                                │
│  ┌─────────────────────────────────────────────────┐     │
│  │  数据库表:                                       │     │
│  │  biz_tag | max_id | step | description          │     │
│  │  order   | 1000   | 1000 | 订单号               │     │
│  │                                                 │     │
│  │  流程:                                           │     │
│  │  1. 从 DB 获取号段: [1, 1000]                   │     │
│  │  2. 在内存中分配 ID (原子递增)                   │     │
│  │  3. 用到 80% 时异步加载下一个号段                │     │
│  │     → 双 Buffer 保证平滑过渡                    │     │
│  │  4. 号段用完 → 加载新号段: [1001, 2000]         │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  双 Buffer 机制:                                         │
│  ┌──────────┐    ┌──────────┐                           │
│  │ Buffer 1 │    │ Buffer 2 │                           │
│  │ [1-1000] │    │[1001-2000]│                          │
│  │ 当前使用  │    │  预加载   │                           │
│  └──────────┘    └──────────┘                           │
│                                                          │
│  Leaf-snowflake (雪花模式):                              │
│  ├── 使用 ZooKeeper 分配机器 ID                         │
│  ├── 解决时钟回拨: 启动时检查 ZK 时间                   │
│  └── 适用于趋势有序场景                                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q4: 数据库号段模式实现？

```sql
-- 号段表
CREATE TABLE id_generator (
    biz_tag VARCHAR(64) NOT NULL COMMENT '业务标识',
    max_id BIGINT NOT NULL COMMENT '当前最大ID',
    step INT NOT NULL COMMENT '号段步长',
    description VARCHAR(256) DEFAULT NULL COMMENT '描述',
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (biz_tag)
) ENGINE=InnoDB;

-- 初始化
INSERT INTO id_generator (biz_tag, max_id, step, description)
VALUES ('order', 0, 1000, '订单号');

-- 获取号段
UPDATE id_generator SET max_id = max_id + step WHERE biz_tag = 'order';
SELECT max_id, step FROM id_generator WHERE biz_tag = 'order';
```

### Java 实现

```java
@Service
public class IdGeneratorService {

    @Autowired
    private IdGeneratorMapper idGeneratorMapper;

    // 双 Buffer
    private Segment currentSegment;
    private Segment nextSegment;
    private volatile boolean loadingNext = false;

    public long nextId(String bizTag) {
        if (currentSegment == null || !currentSegment.hasNext()) {
            loadSegment(bizTag);
        }
        long id = currentSegment.next();
        // 预加载下一个号段
        if (currentSegment.remaining() < currentSegment.getStep() * 0.2) {
            asyncLoadNextSegment(bizTag);
        }
        return id;
    }

    private void loadSegment(String bizTag) {
        if (nextSegment != null) {
            currentSegment = nextSegment;
            nextSegment = null;
        } else {
            currentSegment = fetchFromDB(bizTag);
        }
    }

    private Segment fetchFromDB(String bizTag) {
        // UPDATE id_generator SET max_id = max_id + step WHERE biz_tag = ?
        // SELECT max_id, step FROM id_generator WHERE biz_tag = ?
        IdGenerator generator = idGeneratorMapper.selectById(bizTag);
        long startId = generator.getMaxId() - generator.getStep() + 1;
        long endId = generator.getMaxId();
        return new Segment(startId, endId);
    }
}
```

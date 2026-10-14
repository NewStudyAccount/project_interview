# 消息队列

## Q1: 为什么使用消息队列？

| 场景 | 说明 | 示例 |
|------|------|------|
| 异步 | 耗时操作异步处理 | 发送短信/邮件 |
| 解耦 | 降低系统耦合度 | 订单→库存→物流 |
| 削峰 | 应对突发流量 | 秒杀下单 |

---

## Q2: RabbitMQ 消息可靠性？

```
┌──────────────────────────────────────────────────────────┐
│              RabbitMQ 消息可靠性                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  生产者 → Broker:                                        │
│  ├── Confirm 模式: 异步确认                              │
│  ├── Return 模式: 路由失败回调                           │
│  └── 事务模式: 性能差，不推荐                            │
│                                                          │
│  Broker 存储:                                            │
│  ├── 交换机/队列持久化 (durable=true)                    │
│  ├── 消息持久化 (deliveryMode=2)                         │
│  └── 镜像队列 / Quorum Queue (集群高可用)               │
│                                                          │
│  Broker → 消费者:                                        │
│  ├── 手动 ACK (acknowledge)                              │
│  ├── 消费失败: reject + requeue / 死信队列               │
│  └── 幂等性: 消息ID + 去重表 / Redis SET                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 生产者确认

```java
@Configuration
public class RabbitConfig {

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory factory) {
        RabbitTemplate template = new RabbitTemplate(factory);
        // Confirm 回调
        template.setConfirmCallback((correlationData, ack, cause) -> {
            if (!ack) {
                log.error("消息发送失败: {}", cause);
                // 重试或记录失败消息
            }
        });
        // Return 回调
        template.setReturnsCallback(returned -> {
            log.error("消息路由失败: {}", returned.getMessage());
        });
        template.setMandatory(true);
        return template;
    }
}
```

### 消费者手动 ACK

```java
@RabbitListener(queues = "order.queue")
public void handleMessage(Message message, Channel channel,
                          @Header(AmqpHeaders.DELIVERY_TAG) long tag) {
    try {
        // 处理消息
        processMessage(message);
        // 手动确认
        channel.basicAck(tag, false);
    } catch (Exception e) {
        try {
            // 拒绝消息, requeue=true 重新入队, false 进入死信
            channel.basicNack(tag, false, false);
        } catch (IOException ex) {
            log.error("NACK 失败", ex);
        }
    }
}
```

---

## Q3: 消息幂等性如何保证？

```
┌──────────────────────────────────────────────────────────┐
│              消息幂等性方案                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  方案一: 去重表                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │  CREATE TABLE msg_dedup (                       │     │
│  │      msg_id VARCHAR(64) PRIMARY KEY,            │     │
│  │      create_time DATETIME                       │     │
│  │  );                                             │     │
│  │                                                 │     │
│  │  消费前: SELECT * FROM msg_dedup WHERE msg_id=? │     │
│  │  不存在 → 处理业务 + INSERT INTO msg_dedup      │     │
│  │  存在 → 跳过                                    │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  方案二: Redis SET                                        │
│  ┌─────────────────────────────────────────────────┐     │
│  │  SETNX msg:{msgId} 1 EX 86400                  │     │
│  │  成功 → 处理业务                                │     │
│  │  失败 → 说明已消费，跳过                        │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  方案三: 状态机                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │  订单状态: PENDING → PAID → SHIPPED             │     │
│  │  UPDATE orders SET status='PAID'                │     │
│  │  WHERE id=? AND status='PENDING'                │     │
│  │  影响行数=0 → 说明已经处理过                    │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  方案四: 乐观锁 (version)                                │
│  ┌─────────────────────────────────────────────────┐     │
│  │  UPDATE orders SET status='PAID', version=2     │     │
│  │  WHERE id=? AND version=1                       │     │
│  │  影响行数=0 → 说明已经处理过                    │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q4: 延迟消息怎么实现？

```
┌──────────────────────────────────────────────────────────┐
│              延迟消息方案                                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  方案一: RabbitMQ 死信队列                               │
│  ┌──────────────────────────────────────────────────┐    │
│  │  正常队列 (TTL=30min) ──▶ 死信队列 ──▶ 消费者    │    │
│  │                                                  │    │
│  │  配置:                                           │    │
│  │  x-dead-letter-exchange: dlx.exchange           │    │
│  │  x-dead-letter-routing-key: dlx.routing.key     │    │
│  │  x-message-ttl: 1800000 (30分钟)                │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  方案二: RabbitMQ 延迟插件                               │
│  ┌──────────────────────────────────────────────────┐    │
│  │  安装 rabbitmq_delayed_message_exchange 插件     │    │
│  │                                                  │    │
│  │  @Bean                                           │    │
│  │  public CustomExchange delayedExchange() {       │    │
│  │      return new CustomExchange("delayed.exchange",│    │
│  │          "x-delayed-message", true, false);      │    │
│  │  }                                               │    │
│  │                                                  │    │
│  │  发送时设置 header: x-delay=1800000              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  方案三: Redis ZSet                                       │
│  ┌──────────────────────────────────────────────────┐    │
│  │  生产者: ZADD delay_queue <timestamp> <message>  │    │
│  │                                                  │    │
│  │  消费者 (定时轮询):                               │    │
│  │  ZRANGEBYSCORE delay_queue 0 <now> LIMIT 0 100  │    │
│  │  → 处理到期消息                                  │    │
│  │  → ZREM 删除已处理消息                           │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  方案四: RocketMQ 原生支持                                │
│  ┌──────────────────────────────────────────────────┐    │
│  │  message.setDelayTimeLevel(3); // 延迟级别       │    │
│  │  // 1s 5s 10s 30s 1m 2m 3m 4m 5m 6m 7m 8m 9m   │    │
│  │  // 10m 20m 30m 1h 2h                           │    │
│  │                                                  │    │
│  │  // RocketMQ 5.0+ 支持任意时间延迟               │    │
│  │  message.setDelayTime(30, TimeUnit.MINUTES);     │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q5: 消息顺序性如何保证？

```
┌──────────────────────────────────────────────────────────┐
│              消息顺序性方案                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  问题: 多消费者并行消费时，无法保证顺序                  │
│                                                          │
│  方案一: 单分区/单队列                                   │
│  ├── 所有消息发送到同一个队列                            │
│  ├── 单个消费者消费                                      │
│  └── 缺点: 吞吐量低                                     │
│                                                          │
│  方案二: 分区有序                                        │
│  ├── 相同业务 key 的消息发到同一个队列                   │
│  ├── 每个队列单个消费者                                  │
│  └── 例如: 同一订单的消息有序，不同订单可并行            │
│                                                          │
│  RabbitMQ 实现:                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │  // 发送时指定 routing key (订单ID)              │     │
│  │  template.convertAndSend("exchange",            │     │
│  │      "order." + orderId, message);              │     │
│  │                                                 │     │
│  │  // 队列绑定:                                    │     │
│  │  // queue.order.1 ← order.#                    │     │
│  │  // queue.order.2 ← order.#                    │     │
│  │  // 每个队列绑定一个消费者                      │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  Kafka 实现:                                             │
│  ┌─────────────────────────────────────────────────┐     │
│  │  // 指定 partition key                           │     │
│  │  producer.send(new ProducerRecord<>(            │     │
│  │      "topic", orderId, message));               │     │
│  │                                                 │     │
│  │  // 相同 orderId 的消息在同一个 partition        │     │
│  │  // 单个消费者消费一个 partition                 │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q6: Kafka 架构？分区与副本？为什么吞吐高？（高频）

### 核心架构

```
┌──────────────────────────────────────────────────────────┐
│              Kafka 架构                                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Producer ──▶ Broker 集群 ──▶ Consumer Group              │
│                                                          │
│  Topic (逻辑概念，如 order-topic)                         │
│  ┌─────────────────────────────────────────────────┐     │
│  │  Partition 0  (Leader + Follower + Follower)    │     │
│  │  Partition 1  (Leader + Follower + Follower)    │     │
│  │  Partition 2  (Leader + Follower + Follower)    │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  核心角色:                                               │
│  ├── Broker:  Kafka 服务器，存储消息                      │
│  ├── Topic:   逻辑队列，分成多个 Partition                │
│  ├── Partition: 有序分片，消费并行度单位                  │
│  ├── Replica:  副本，Leader 读写，Follower 同步           │
│  ├── Consumer Group: 一组消费者共同消费 Topic             │
│  └── ZooKeeper/KRaft: 元数据与控制器选举                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 分区与副本机制

| 概念 | 作用 | 说明 |
|------|------|------|
| Partition | 并行 + 扩展 | 分区数决定消费并行度上限 |
| Leader | 读写入口 | 生产/消费都走 Leader |
| Follower | 高可用 | ISR 同步副本，Leader 挂了可选举 |
| ISR | 同步副本集 | 保持同步的 Follower 列表 |
| Offset | 消费位点 | 消费者在分区中的位置 |
| Consumer Group | 负载均衡 | 组内每分区只被一个消费者消费 |

```
┌──────────────────────────────────────────────────────────┐
│              分区与副本示例 (3 分区 × 3 副本)               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Broker-1        Broker-2        Broker-3                │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐              │
│  │ P0-L    │    │ P0-F    │    │ P0-F    │              │
│  │ P1-F    │    │ P1-L    │    │ P1-F    │              │
│  │ P2-F    │    │ P2-F    │    │ P2-L    │              │
│  └─────────┘    └─────────┘    └─────────┘              │
│                                                          │
│  消费: Group 内 3 个消费者 → 每人一个 Partition           │
│  扩容: 增加 Partition (只能加不能减) + 增加消费者          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 为什么吞吐高？

| 优化点 | 说明 |
|------|------|
| 顺序写磁盘 | 追加写 log，比随机写快几个数量级，接近内存速度 |
| 零拷贝 | sendfile 直接从磁盘/页缓存到网卡，绕过用户态 |
| 分区并行 | 多分区多消费者并行处理 |
| 批量 + 压缩 | Producer 批量发送，支持 lz4/snappy/zstd 压缩 |
| 页缓存 | 操作系统 Page Cache 缓存热点数据 |
| 拉取模式 | 消费者按自己能力拉取，避免推压垮消费者 |
| 稀疏索引 + 顺序读 | 消息定位快 |

### 面试答法

> "Kafka 是分布式分区日志：Topic 逻辑上分成多个 Partition，每个 Partition 有 Leader/Follower 副本，Leader 负责读写，Follower 在 ISR 中同步。吞吐高的原因是顺序写磁盘、零拷贝、分区并行、批量压缩、页缓存和拉取模型。分区数决定并行度，副本数决定可靠性，典型是 3 副本。"

---

## Q7: Kafka 如何保证消息不丢？生产者/消费者/副本机制？（高频）

### 三个环节都可能丢消息

```
┌──────────────────────────────────────────────────────────┐
│              Kafka 消息可靠性 (不丢消息)                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ① 生产者 → Broker                                      │
│  ├── acks=0:  发完就不管 → 可能丢                        │
│  ├── acks=1:  Leader 写成功即算 → Leader 挂可能丢        │
│  └── acks=all / -1: ISR 全部确认 → 最可靠                │
│                                                          │
│  配套:                                                   │
│  ├── retries: 发送失败自动重试                           │
│  ├── max.in.flight.requests.per.connection=1             │
│  │   (重试时保证顺序，避免乱序)                          │
│  └── 同步发送或带回调的异步发送                           │
│                                                          │
│  ② Broker 存储                                            │
│  ├── replication.factor ≥ 3                              │
│  ├── min.insync.replicas ≥ 2                             │
│  │   (acks=all 时至少 2 个副本确认)                      │
│  ├── unclean.leader.election.enable=false                │
│  │   (禁止非 ISR 副本当 Leader，防丢数据)                │
│  └── 刷盘策略: log.flush 配置 (一般依赖副本机制)          │
│                                                          │
│  ③ Broker → 消费者                                       │
│  ├── 手动提交 offset (enable.auto.commit=false)          │
│  ├── 业务处理成功后再 commit                             │
│  └── 处理失败: 不提交 / 重试 / 死信 topic                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 生产者关键配置

```properties
# 生产者配置 (Producer)
acks=all
retries=3
max.in.flight.requests.per.connection=1
enable.idempotence=true
# 批量与压缩
batch.size=16384
linger.ms=5
compression.type=lz4
```

### 消费者关键配置

```properties
# 消费者配置 (Consumer)
enable.auto.commit=false
# 业务成功后手动 commitSync / commitAsync
# 重复消费应对: 以消息 ID 做幂等 (去重表 / 状态机)
```

### 不丢消息组合拳

| 环节 | 配置 | 目标 |
|------|------|------|
| 生产者 | acks=all + retries + 幂等 | 发送不丢、不重不乱 |
| Broker | 副本≥3 + min.ISR≥2 + 关闭不干净选举 | 存储不丢 |
| 消费者 | 手动提交 offset + 幂等消费 | 消费不丢不重 |

### 面试答法

> "Kafka 不丢消息要管三个环节。生产端 acks=all、开启重试和幂等；服务端副本数 3、min.insync.replicas=2、关闭 unclean leader election；消费端关闭自动提交，业务成功后再 commit。注意 acks=all 配合 min.ISR 才有意义。吞吐和可靠要权衡，金融级场景还要加事务或对账。"

---

## Q8: RabbitMQ vs Kafka 如何选型？

| 维度 | RabbitMQ | Kafka |
|------|----------|-------|
| 定位 | 传统消息中间件（智能 broker） | 分布式日志流平台 |
| 吞吐 | 万级 | 十万~百万级 |
| 协议 | AMQP | 自定义协议 |
| 消息模型 | 队列（推/消费即删） | 日志（保留期，可回溯） |
| 顺序性 | 单队列有序 | 单 Partition 有序 |
| 延迟消息 | 插件/死信队列 | 需外部实现（不擅长） |
| 事务 | 支持（性能差） | 支持（生产者事务） |
| 消息回溯 | 弱（删了就没了） | 强（按 offset 重放） |
| 运维复杂度 | 中 | 中高 |
| 典型场景 | 业务解耦、任务队列、重试/死信 | 日志采集、埋点、大数据管道、流处理 |

### 选型决策

```
┌──────────────────────────────────────────────────────────┐
│              选型思路                                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  需要: 业务解耦 / 任务分发 / 延迟重试 / 死信              │
│  └──▶ RabbitMQ (或 RocketMQ)                             │
│                                                          │
│  需要: 海量日志 / 埋点 / 用户行为 / 流计算 / 可回溯        │
│  └──▶ Kafka                                             │
│                                                          │
│  需要: 订单超时 / 延迟任务 / 事务消息                      │
│  └──▶ RocketMQ (延迟消息、事务消息原生支持)               │
│                                                          │
│  混合架构:                                               │
│  ├── 订单/支付等业务事件 → RabbitMQ / RocketMQ            │
│  └── 日志、监控、埋点、行为流水 → Kafka                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试答法

> "RabbitMQ 是传统消息队列，轻量、功能全（确认、死信、延迟插件），适合业务级解耦、任务队列。Kafka 是分布式日志流，吞吐高、可回溯、适合日志埋点和大数据管道。中小业务用 RabbitMQ 够用；海量数据和流处理选 Kafka。两者也能混用：业务走 MQ，日志走 Kafka。"

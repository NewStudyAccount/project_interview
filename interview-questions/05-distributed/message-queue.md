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

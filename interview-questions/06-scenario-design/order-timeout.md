# 订单超时取消方案

## 方案对比

| 方案 | 实现复杂度 | 实时性 | 可靠性 | 适用场景 |
|------|------------|--------|--------|----------|
| 定时任务扫描 | 低 | 差 (分钟级) | 高 | 小规模、低实时性 |
| RabbitMQ 死信队列 | 中 | 好 | 高 | 推荐方案 |
| RabbitMQ 延迟插件 | 中 | 好 | 高 | 推荐方案 |
| Redis ZSet | 中 | 好 | 中 | 精度要求高 |
| Redisson 延迟队列 | 低 | 好 | 高 | 推荐方案 |
| 时间轮 (Netty) | 高 | 好 | 中 | 高性能场景 |

---

## 方案一：RabbitMQ 死信队列（推荐）

```
┌──────────────────────────────────────────────────────────┐
│              RabbitMQ 死信队列方案                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  订单创建 ──▶ 正常队列 (TTL=30min)                       │
│                    │                                     │
│                    ▼ (消息过期)                           │
│              死信交换机 (DLX)                             │
│                    │                                     │
│                    ▼                                     │
│              死信队列 (DLQ)                               │
│                    │                                     │
│                    ▼                                     │
│              消费者:                                      │
│              ├── 查询订单状态                             │
│              ├── 未支付 → 取消订单, 释放库存              │
│              └── 已支付 → 忽略                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 配置

```java
@Configuration
public class RabbitMqConfig {

    // 死信交换机
    @Bean
    public DirectExchange orderDlxExchange() {
        return new DirectExchange("order.dlx.exchange");
    }

    // 死信队列
    @Bean
    public Queue orderDlxQueue() {
        return QueueBuilder.durable("order.dlx.queue").build();
    }

    // 绑定
    @Bean
    public Binding orderDlxBinding() {
        return BindingBuilder.bind(orderDlxQueue())
            .to(orderDlxExchange())
            .with("order.dlx");
    }

    // 正常交换机
    @Bean
    public DirectExchange orderExchange() {
        return new DirectExchange("order.exchange");
    }

    // 正常队列 (带 TTL 和死信配置)
    @Bean
    public Queue orderQueue() {
        return QueueBuilder.durable("order.queue")
            .withArgument("x-message-ttl", 1800000) // 30 分钟
            .withArgument("x-dead-letter-exchange", "order.dlx.exchange")
            .withArgument("x-dead-letter-routing-key", "order.dlx")
            .build();
    }

    @Bean
    public Binding orderBinding() {
        return BindingBuilder.bind(orderQueue())
            .to(orderExchange())
            .with("order.create");
    }
}
```

### 生产者

```java
@Service
public class OrderService {

    @Autowired
    private RabbitTemplate rabbitTemplate;

    public Order createOrder(OrderDTO dto) {
        // 1. 创建订单
        Order order = new Order();
        order.setStatus(OrderStatus.PENDING_PAYMENT);
        orderMapper.insert(order);

        // 2. 发送延时消息 (TTL 由队列配置决定)
        rabbitTemplate.convertAndSend("order.exchange", "order.create",
            order.getId().toString());

        return order;
    }
}
```

### 消费者

```java
@RabbitListener(queues = "order.dlx.queue")
public void handleOrderTimeout(Message message, Channel channel,
                                @Header(AmqpHeaders.DELIVERY_TAG) long tag) {
    try {
        Long orderId = Long.parseLong(new String(message.getBody()));
        Order order = orderMapper.selectById(orderId);

        if (order != null && order.getStatus() == OrderStatus.PENDING_PAYMENT) {
            // 1. 更新订单状态为已取消
            order.setStatus(OrderStatus.CANCELLED);
            orderMapper.updateById(order);

            // 2. 释放库存
            stockService.releaseStock(order.getSkuId(), order.getCount());

            // 3. 释放优惠券 (如有)
            couponService.releaseCoupon(order.getCouponId());

            log.info("订单超时取消: {}", orderId);
        }

        channel.basicAck(tag, false);
    } catch (Exception e) {
        try {
            channel.basicNack(tag, false, true);
        } catch (IOException ex) {
            log.error("NACK 失败", ex);
        }
    }
}
```

---

## 方案二：RabbitMQ 延迟插件

### 安装插件

```bash
# 下载插件
wget https://github.com/rabbitmq/rabbitmq-delayed-message-exchange/releases

# 复制到 RabbitMQ 插件目录
cp rabbitmq_delayed_message_exchange-3.12.0.ez /opt/rabbitmq/plugins/

# 启用插件
rabbitmq-plugins enable rabbitmq_delayed_message_exchange
```

### 配置

```java
@Configuration
public class DelayedMqConfig {

    @Bean
    public CustomExchange delayedExchange() {
        Map<String, Object> args = new HashMap<>();
        args.put("x-delayed-type", "direct");
        return new CustomExchange("order.delayed.exchange",
            "x-delayed-message", true, false, args);
    }

    @Bean
    public Queue delayedQueue() {
        return QueueBuilder.durable("order.delayed.queue").build();
    }

    @Bean
    public Binding delayedBinding() {
        return BindingBuilder.bind(delayedQueue())
            .to(delayedExchange())
            .with("order.delayed")
            .noargs();
    }
}
```

### 生产者

```java
public void createOrderWithDelay(Order order) {
    // 创建订单
    orderMapper.insert(order);

    // 发送延迟消息
    rabbitTemplate.convertAndSend("order.delayed.exchange",
        "order.delayed", order.getId().toString(), message -> {
            message.getMessageProperties().setDelay(1800000); // 30 分钟
            return message;
        });
}
```

---

## 方案三：Redis ZSet 实现

```java
@Service
public class OrderTimeoutService {

    @Autowired
    private StringRedisTemplate redisTemplate;

    private static final String ORDER_TIMEOUT_KEY = "order:timeout";

    /**
     * 添加订单到延迟队列
     */
    public void addOrderTimeout(Long orderId, long timeoutMillis) {
        long executeAt = System.currentTimeMillis() + timeoutMillis;
        redisTemplate.opsForZSet().add(ORDER_TIMEOUT_KEY,
            orderId.toString(), executeAt);
    }

    /**
     * 取消订单时移除
     */
    public void removeOrderTimeout(Long orderId) {
        redisTemplate.opsForZSet().remove(ORDER_TIMEOUT_KEY,
            orderId.toString());
    }

    /**
     * 定时任务: 每秒扫描处理超时订单
     */
    @Scheduled(fixedDelay = 1000)
    public void processTimeoutOrders() {
        long now = System.currentTimeMillis();

        // 获取已到期的订单
        Set<String> orderIds = redisTemplate.opsForZSet()
            .rangeByScore(ORDER_TIMEOUT_KEY, 0, now, 0, 100);

        if (orderIds == null || orderIds.isEmpty()) {
            return;
        }

        for (String orderIdStr : orderIds) {
            // 尝试移除 (原子操作，防止重复处理)
            Long removed = redisTemplate.opsForZSet()
                .remove(ORDER_TIMEOUT_KEY, orderIdStr);
            if (removed != null && removed > 0) {
                Long orderId = Long.parseLong(orderIdStr);
                cancelOrder(orderId);
            }
        }
    }

    private void cancelOrder(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order != null && order.getStatus() == OrderStatus.PENDING_PAYMENT) {
            order.setStatus(OrderStatus.CANCELLED);
            orderMapper.updateById(order);
            // 释放库存、优惠券等
        }
    }
}
```

---

## 方案四：Redisson 延迟队列

```java
@Service
public class OrderTimeoutService {

    @Autowired
    private RedissonClient redisson;

    private RBlockingQueue<Long> orderQueue;
    private RDelayedQueue<Long> delayedQueue;

    @PostConstruct
    public void init() {
        orderQueue = redisson.getBlockingQueue("order:timeout:queue");
        delayedQueue = redisson.getDelayedQueue(orderQueue);
    }

    /**
     * 添加订单超时任务
     */
    public void addOrderTimeout(Long orderId, long delay, TimeUnit unit) {
        delayedQueue.offer(orderId, delay, unit);
    }

    /**
     * 消费者: 监听超时队列
     */
    @Scheduled(fixedDelay = 100)
    public void processTimeout() {
        try {
            Long orderId = orderQueue.poll(100, TimeUnit.MILLISECONDS);
            if (orderId != null) {
                cancelOrder(orderId);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

---

## 方案五：定时任务扫描

```java
@Service
public class OrderTimeoutService {

    /**
     * 每分钟扫描一次超时订单
     */
    @Scheduled(cron = "0 * * * * ?")
    public void scanTimeoutOrders() {
        // 查询 30 分钟前创建且未支付的订单
        LocalDateTime timeout = LocalDateTime.now().minusMinutes(30);
        List<Order> orders = orderMapper.selectList(
            new LambdaQueryWrapper<Order>()
                .eq(Order::getStatus, OrderStatus.PENDING_PAYMENT)
                .le(Order::getCreateTime, timeout)
        );

        for (Order order : orders) {
            try {
                cancelOrder(order);
            } catch (Exception e) {
                log.error("取消订单失败: {}", order.getId(), e);
            }
        }
    }

    private void cancelOrder(Order order) {
        order.setStatus(OrderStatus.CANCELLED);
        orderMapper.updateById(order);
        // 释放库存
        stockService.releaseStock(order.getSkuId(), order.getCount());
    }
}
```

### 优化：分页扫描

```java
@Scheduled(cron = "0 * * * * ?")
public void scanTimeoutOrders() {
    int pageSize = 100;
    int pageNum = 1;
    LocalDateTime timeout = LocalDateTime.now().minusMinutes(30);

    while (true) {
        Page<Order> page = orderMapper.selectPage(
            new Page<>(pageNum, pageSize),
            new LambdaQueryWrapper<Order>()
                .eq(Order::getStatus, OrderStatus.PENDING_PAYMENT)
                .le(Order::getCreateTime, timeout)
                .orderByAsc(Order::getId)
        );

        List<Order> orders = page.getRecords();
        if (orders.isEmpty()) break;

        for (Order order : orders) {
            cancelOrder(order);
        }

        if (orders.size() < pageSize) break;
        pageNum++;
    }
}
```

---

## 面试总结

### 推荐方案

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 中小规模 | RabbitMQ 死信队列 | 简单可靠 |
| 已有 Redis | Redisson 延迟队列 | 无需额外组件 |
| 高精度 | Redis ZSet | 精确到毫秒 |
| 超大规模 | 定时任务 + 分库分表 | 可扩展 |

### 关键注意事项

1. **幂等性**: 消费者需要保证幂等，防止重复取消
2. **状态检查**: 取消前检查订单状态，只取消未支付的
3. **补偿机制**: 消息丢失时的补偿方案
4. **监控告警**: 超时订单数量监控

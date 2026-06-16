# 秒杀系统设计

## 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                  秒杀系统架构                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │Client│──▶│   CDN    │──▶│  Nginx   │──▶│ Gateway │ │
│  └──────┘   │ 静态页面  │   │ 限流/削峰│   │ 限流    │ │
│             └──────────┘   └──────────┘   └────┬────┘ │
│                                                 │       │
│              ┌──────────────────────────────────┘       │
│              ▼                                          │
│  ┌──────────────────┐   ┌──────────┐   ┌────────────┐ │
│  │   秒杀服务       │──▶│  Redis   │──▶│   MQ       │ │
│  │  ├── 库存预扣减   │   │ 预减库存  │   │  异步下单  │ │
│  │  ├── 用户去重     │   │ 用户标记  │   │  削峰填谷  │ │
│  │  └── 令牌桶限流   │   └──────────┘   └─────┬──────┘ │
│  └──────────────────┘                         │        │
│                                               ▼        │
│                                     ┌──────────────┐   │
│                                     │   订单服务    │   │
│                                     │  真正扣库存   │   │
│                                     │  创建订单     │   │
│                                     └──────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 核心策略

### 1. 前端削峰

```
┌──────────────────────────────────────────────────────────┐
│              前端防刷策略                                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 按钮防抖                                             │
│     ├── 点击后禁用 3 秒                                  │
│     └── 防止重复提交                                     │
│                                                          │
│  2. 验证码                                               │
│     ├── 滑块验证码 / 图形验证码                          │
│     └── 分散请求时间                                     │
│                                                          │
│  3. 动静分离                                             │
│     ├── 静态资源 CDN                                     │
│     ├── 页面静态化                                       │
│     └── 减少服务器压力                                   │
│                                                          │
│  4. 本地标记                                             │
│     ├── 秒杀开始前，标记库存是否已售罄                   │
│     └── 已售罄直接返回，不发请求                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 2. Nginx 层限流

```nginx
# 限制请求速率
limit_req_zone $binary_remote_addr zone=seckill:10m rate=10r/s;

server {
    location /api/seckill {
        limit_req zone=seckill burst=20 nodelay;
        proxy_pass http://backend;
    }
}

# 限制连接数
limit_conn_zone $binary_remote_addr zone=addr:10m;

server {
    location /api/seckill {
        limit_conn addr 5;
    }
}
```

### 3. Gateway 限流

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: seckill
          uri: lb://seckill-service
          predicates:
            - Path=/api/seckill/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 100
                redis-rate-limiter.burstCapacity: 200
                key-resolver: "#{@userKeyResolver}"
```

```java
@Bean
public KeyResolver userKeyResolver() {
    return exchange -> {
        String userId = exchange.getRequest()
            .getHeaders().getFirst("X-User-Id");
        return Mono.just(userId);
    };
}
```

### 4. Redis 库存预扣减

```java
@Service
public class SeckillService {

    @Autowired
    private StringRedisTemplate redisTemplate;

    @Autowired
    private RabbitTemplate rabbitTemplate;

    /**
     * 秒杀核心逻辑
     */
    public Result<Void> doSeckill(Long userId, Long skuId) {
        String stockKey = "seckill:stock:" + skuId;
        String userKey = "seckill:user:" + skuId + ":" + userId;

        // 1. 用户去重 (防止重复秒杀)
        Boolean alreadySeckilled = redisTemplate.opsForValue()
            .setIfAbsent(userKey, "1", 24, TimeUnit.HOURS);
        if (Boolean.FALSE.equals(alreadySeckilled)) {
            return Result.error("您已经秒杀过了");
        }

        // 2. 库存预扣减 (原子操作)
        Long stock = redisTemplate.opsForValue().decrement(stockKey);
        if (stock == null || stock < 0) {
            // 库存不足，回滚
            redisTemplate.opsForValue().increment(stockKey);
            redisTemplate.delete(userKey);
            return Result.error("库存不足");
        }

        // 3. 发送消息到 MQ，异步创建订单
        SeckillMessage message = new SeckillMessage();
        message.setUserId(userId);
        message.setSkuId(skuId);
        rabbitTemplate.convertAndSend("seckill.exchange", "seckill.order",
            JSON.toJSONString(message));

        return Result.success("秒杀成功，正在创建订单");
    }

    /**
     * 初始化库存 (活动开始前调用)
     */
    public void initStock(Long skuId, Integer stock) {
        String stockKey = "seckill:stock:" + skuId;
        redisTemplate.opsForValue().set(stockKey, stock.toString());
    }
}
```

### 5. MQ 异步下单

```java
@RabbitListener(bindings = @QueueBinding(
    value = @Queue("seckill.order.queue"),
    exchange = @Exchange("seckill.exchange"),
    key = "seckill.order"
))
public void handleSeckillOrder(Message message, Channel channel,
                                @Header(AmqpHeaders.DELIVERY_TAG) long tag) {
    try {
        SeckillMessage msg = JSON.parseObject(
            new String(message.getBody()), SeckillMessage.class);

        // 1. 查询商品信息
        Product product = productMapper.selectById(msg.getSkuId());

        // 2. 创建订单
        Order order = new Order();
        order.setUserId(msg.getUserId());
        order.setSkuId(msg.getSkuId());
        order.setPrice(product.getSeckillPrice());
        order.setStatus(OrderStatus.PENDING_PAYMENT);
        orderMapper.insert(order);

        // 3. 扣减数据库库存 (乐观锁)
        int affected = productMapper.deductStock(msg.getSkuId(), 1);
        if (affected == 0) {
            // 库存不足，订单取消
            order.setStatus(OrderStatus.CANCELLED);
            orderMapper.updateById(order);
        }

        // 4. 发送延时消息，30分钟后检查支付状态
        rabbitTemplate.convertAndSend("order.timeout.exchange",
            "order.timeout", JSON.toJSONString(order.getId()),
            msg1 -> {
                msg1.getMessageProperties().setDelay(1800000); // 30分钟
                return msg1;
            });

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

### 6. 数据库乐观锁扣减

```java
@Mapper
public interface ProductMapper {

    @Update("UPDATE product SET stock = stock - #{count}, " +
            "version = version + 1 " +
            "WHERE id = #{id} AND stock >= #{count} AND version = #{version}")
    int deductStock(@Param("id") Long id,
                    @Param("count") Integer count,
                    @Param("version") Integer version);
}
```

---

## 超卖问题解决方案

```
┌──────────────────────────────────────────────────────────┐
│              超卖防护 (三层保障)                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  第一层: Redis 原子扣减                                   │
│  ├── DECR 命令保证原子性                                 │
│  ├── 返回值 < 0 → 库存不足                              │
│  └── 拦截大部分无效请求                                  │
│                                                          │
│  第二层: 数据库乐观锁                                    │
│  ├── UPDATE ... WHERE stock >= count AND version = ?     │
│  ├── 影响行数 = 0 → 库存不足                            │
│  └── 兜底保障                                            │
│                                                          │
│  第三层: 订单状态检查                                    │
│  ├── 创建订单后再次确认库存                              │
│  └── 不足则取消订单                                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 热点商品问题

```
┌──────────────────────────────────────────────────────────┐
│              热点商品处理                                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  问题: 单个热点商品 Redis 压力过大                       │
│                                                          │
│  方案: 库存分片                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │  将 1000 个库存拆分到 10 个 Redis key:          │     │
│  │  seckill:stock:1001:0 = 100                     │     │
│  │  seckill:stock:1001:1 = 100                     │     │
│  │  seckill:stock:1001:2 = 100                     │     │
│  │  ...                                            │     │
│  │  seckill:stock:1001:9 = 100                     │     │
│  │                                                 │     │
│  │  请求随机选择一个分片:                           │     │
│  │  int index = ThreadLocalRandom.current()        │     │
│  │      .nextInt(10);                              │     │
│  │  String key = "seckill:stock:" + skuId + ":" + index;│
│  └─────────────────────────────────────────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 面试总结

### 秒杀系统要点

| 层次 | 策略 | 技术 |
|------|------|------|
| 前端 | 防抖、验证码、动静分离 | JS + CDN |
| 接入层 | 限流、削峰 | Nginx |
| 网关层 | 限流、鉴权 | Gateway + Sentinel |
| 服务层 | 库存预扣减、用户去重 | Redis + Lua |
| 消息层 | 异步下单、削峰填谷 | RabbitMQ |
| 数据层 | 乐观锁、最终扣减 | MySQL |

### 关键指标

- **QPS**: 秒杀接口需要支撑 10w+ QPS
- **响应时间**: 接口 RT < 100ms
- **库存准确**: 不超卖、不少卖
- **用户体验**: 排队等待、结果通知

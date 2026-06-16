# 服务容错

## Q1: Sentinel 限流原理？

```
┌──────────────────────────────────────────────────────────┐
│              Sentinel 限流算法                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  滑动窗口 (默认):                                        │
│  ┌─────────────────────────────────────┐                │
│  │  ┌─────┬─────┬─────┬─────┬─────┐   │                │
│  │  │ W1  │ W2  │ W3  │ W4  │ W5  │   │  时间窗口       │
│  │  │100  │80   │120  │90   │...  │   │  统计请求量     │
│  │  └─────┴─────┴─────┴─────┴─────┘   │                │
│  │  窗口大小: 1s, 格子数: 2            │                │
│  │  每个格子 500ms                     │                │
│  └─────────────────────────────────────┘                │
│                                                          │
│  三种流控效果:                                           │
│  ├── 快速失败: 直接拒绝 (默认)                           │
│  ├── Warm Up: 预热，逐步提升阈值                         │
│  └── 排队等待: 匀速通过 (漏桶)                           │
│                                                          │
│  熔断降级:                                               │
│  ├── 慢调用比例: RT 超过阈值                             │
│  ├── 异常比例: 异常占比超过阈值                          │
│  └── 异常数: 异常数超过阈值                              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 限流算法对比

| 算法 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| 计数器 | 固定窗口计数 | 简单 | 临界突刺 |
| 滑动窗口 | 滑动时间窗口 | 平滑 | 实现复杂 |
| 漏桶 | 固定速率流出 | 平滑 | 无法应对突发 |
| 令牌桶 | 固定速率放入令牌 | 允许突发 | 实现复杂 |

```
┌──────────────────────────────────────────────────────────┐
│              漏桶 vs 令牌桶                               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  漏桶:                                                   │
│  ┌──────┐                                               │
│  │ 请求 │ ──▶ ┌──────┐ ──▶ 固定速率流出 ──▶ 服务       │
│  └──────┘     │ 漏桶 │                                  │
│               └──────┘                                  │
│  特点: 平滑限流，无法应对突发流量                        │
│                                                          │
│  令牌桶:                                                 │
│               ┌──────┐                                  │
│  固定速率 ──▶ │ 令牌 │ ──▶ 有令牌才处理 ──▶ 服务       │
│  放入令牌     │  桶  │                                  │
│               └──────┘                                  │
│  特点: 允许一定程度的突发流量                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q2: Sentinel 规则配置？

```java
// 代码配置
@PostConstruct
public void initFlowRules() {
    List<FlowRule> rules = new ArrayList<>();
    FlowRule rule = new FlowRule();
    rule.setResource("getUser");
    rule.setGrade(RuleConstant.FLOW_GRADE_QPS);
    rule.setCount(100); // QPS 阈值
    rule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_WARM_UP);
    rule.setWarmUpPeriodSec(10); // 预热时长
    rules.add(rule);
    FlowRuleManager.loadRules(rules);
}

// 注解方式
@SentinelResource(
    value = "getUser",
    blockHandler = "getUserBlockHandler",
    fallback = "getUserFallback"
)
public User getUser(Long id) {
    return userMapper.selectById(id);
}

// 限流处理
public User getUserBlockHandler(Long id, BlockException ex) {
    throw new RuntimeException("请求过于频繁");
}

// 降级处理
public User getUserFallback(Long id, Throwable ex) {
    return new User(); // 返回默认值
}
```

---

## Q3: 熔断器原理？

```
┌──────────────────────────────────────────────────────────┐
│              熔断器状态机                                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐   失败率超阈值   ┌──────────┐             │
│  │  CLOSED  │───────────────▶│   OPEN   │             │
│  │ (正常)    │                 │ (熔断)    │             │
│  └──────────┘                 └────┬─────┘             │
│       ▲                            │                    │
│       │                            │ 超时时间到         │
│       │                            ▼                    │
│       │                      ┌──────────┐              │
│       │  探测成功             │HALF-OPEN │              │
│       └──────────────────────│ (半开)    │              │
│                              └──────────┘              │
│                                   │                    │
│                          探测失败 │                    │
│                                   ▼                    │
│                              ┌──────────┐              │
│                              │   OPEN   │              │
│                              └──────────┘              │
│                                                          │
│  CLOSED → OPEN: 失败率超过阈值 (默认50%)               │
│  OPEN → HALF-OPEN: 等待超时时间 (默认5s)               │
│  HALF-OPEN → CLOSED: 探测请求成功                      │
│  HALF-OPEN → OPEN: 探测请求失败                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Sentinel 熔断配置

```java
@PostConstruct
public void initDegradeRules() {
    List<DegradeRule> rules = new ArrayList<>();
    DegradeRule rule = new DegradeRule();
    rule.setResource("getUser");
    rule.setGrade(CircuitBreakerStrategy.ERROR_RATIO.getType());
    rule.setCount(0.5); // 50% 错误率
    rule.setTimeWindow(10); // 熔断时长 10 秒
    rule.setMinRequestAmount(10); // 最小请求数
    rule.setStatIntervalMs(10000); // 统计时长
    rules.add(rule);
    DegradeRuleManager.loadRules(rules);
}
```

---

## Q4: 重试和超时控制？

### Feign 超时配置

```yaml
# 全局配置
feign:
  client:
    config:
      default:
        connectTimeout: 5000
        readTimeout: 10000
      # 针对特定服务
      user-service:
        connectTimeout: 3000
        readTimeout: 5000

# Ribbon 配置 (旧)
ribbon:
  ConnectTimeout: 5000
  ReadTimeout: 10000
  MaxAutoRetries: 1
  MaxAutoRetriesNextServer: 2
```

### 重试策略

```java
// Feign 重试
@Bean
public Retryer feignRetryer() {
    // 初始间隔 100ms, 最大间隔 1s, 最多重试 3 次
    return new Retryer.Default(100, 1000, 3);
}

// 自定义重试条件
@Bean
public ErrorDecoder feignErrorDecoder() {
    return (methodKey, response) -> {
        if (response.status() == 503) {
            // 503 时重试
            return new RetryableException(
                response.status(), "Service Unavailable",
                response.request().httpMethod(), null);
        }
        return new Exception("Feign Error");
    };
}
```

---

## Q5: 降级策略有哪些？

| 策略 | 说明 | 场景 |
|------|------|------|
| 返回默认值 | 返回兜底数据 | 查询接口 |
| 缓存降级 | 返回过期缓存 | 缓存服务 |
| 静态降级 | 返回静态页面 | 页面展示 |
| 抛异常 | 快速失败 | 写操作 |
| 调用备用服务 | 切换到备用链路 | 核心业务 |

### 降级示例

```java
@Component
public class UserFallbackFactory implements FallbackFactory<UserClient> {

    @Override
    public UserClient create(Throwable cause) {
        return new UserClient() {
            @Override
            public Result<UserVO> getUser(Long id) {
                // 返回默认值
                UserVO defaultUser = new UserVO();
                defaultUser.setId(id);
                defaultUser.setName("默认用户");
                return Result.success(defaultUser);
            }
        };
    }
}
```

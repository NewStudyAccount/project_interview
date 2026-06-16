# 服务治理

## Q1: Nacos 注册中心原理？

```
┌──────────────────────────────────────────────────────────┐
│                  Nacos 架构                               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  注册  ┌──────────────────────┐           │
│  │ Provider │───────▶│   Nacos Server       │           │
│  └──────────┘        │  ┌─────────────────┐ │           │
│                      │  │  Service Registry│ │           │
│  ┌──────────┐  订阅  │  │  ┌───┐ ┌───┐   │ │           │
│  │ Consumer │◀───────│  │  │IP1│ │IP2│   │ │           │
│  └──────────┘        │  │  └───┘ └───┘   │ │           │
│                      │  └─────────────────┘ │           │
│                      └──────────────────────┘           │
│                                                          │
│  AP/CP 切换:                                             │
│  ├── 临时实例 (ephemeral=true, 默认): AP 模式           │
│  │   └─▶ Distro 协议，最终一致性，心跳检测              │
│  └── 永久实例 (ephemeral=false): CP 模式                 │
│      └─▶ Raft 协议，强一致性                             │
│                                                          │
│  健康检查:                                               │
│  ├── 临时实例: 客户端心跳 (默认5s)                       │
│  └── 永久实例: 服务端主动探测                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Nacos vs Eureka 对比

| 维度 | Nacos | Eureka |
|------|-------|--------|
| CAP | AP + CP (可切换) | AP |
| 健康检查 | TCP/HTTP/MySQL | 客户端心跳 |
| 配置管理 | ✅ 内置 | ❌ 需要 Config Server |
| 雪崩保护 | ✅ | ✅ |
| 访问协议 | HTTP/DNS/GRPC | HTTP |
| Spring Cloud | Alibaba | Netflix (已停更) |

---

## Q2: Spring Cloud Gateway 工作流程？

```
┌──────────────────────────────────────────────────────────┐
│              Gateway 核心概念                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Client ──▶ Gateway ──▶ Filter Chain ──▶ Service        │
│                                                          │
│  三大核心:                                               │
│  ├── Route (路由): ID + URI + Predicate + Filter        │
│  ├── Predicate (断言): 匹配条件 (Path/Header/Method...) │
│  └── Filter (过滤器): 请求/响应处理                      │
│                                                          │
│  执行流程:                                               │
│  1. 请求到达 Gateway                                    │
│  2. GatewayHandlerMapping 匹配 Route                    │
│  3. 执行 Pre Filter 链                                  │
│  4. 代理请求转发到下游服务                               │
│  5. 执行 Post Filter 链                                 │
│  6. 返回响应                                            │
│                                                          │
│  内置 Filter:                                            │
│  ├── AddRequestHeader / AddResponseHeader               │
│  ├── RequestRateLimiter (基于 Redis)                    │
│  ├── CircuitBreaker (集成 Resilience4j)                 │
│  └── Retry / StripPrefix / RewritePath                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Gateway 配置示例

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/api/user/**
          filters:
            - StripPrefix=1
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10
                redis-rate-limiter.burstCapacity: 20
```

### 自定义全局过滤器

```java
@Component
public class AuthFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange,
                              GatewayFilterChain chain) {
        String token = exchange.getRequest()
            .getHeaders().getFirst("Authorization");
        if (StringUtils.isEmpty(token)) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
        // 验证 token
        // ...
        return chain.filter(exchange);
    }

    @Override
    public int getOrder() {
        return -1; // 优先级
    }
}
```

---

## Q3: 负载均衡策略？

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| RoundRobin | 轮询 (默认) | 通用 |
| Random | 随机 | 通用 |
| WeightedRoundRobin | 加权轮询 | 服务器性能不同 |
| LeastActive | 最少活跃数 | 长连接场景 |
| ConsistentHash | 一致性 Hash | 需要会话保持 |
| ResponseTimeWeighted | 响应时间权重 | 服务器性能差异大 |

### Spring Cloud LoadBalancer 自定义

```java
@Configuration
public class LoadBalancerConfig {

    @Bean
    public ReactorLoadBalancer<ServiceInstance>
            randomLoadBalancer(Environment environment,
                              LoadBalancerClientFactory factory) {
        String name = environment.getProperty(LoadBalancerClientFactory.PROPERTY_NAME);
        return new RandomLoadBalancer(
            factory.getLazyProvider(name, ServiceInstanceListSupplier.class),
            name);
    }
}
```

---

## Q4: OpenFeign 远程调用原理？

```
┌──────────────────────────────────────────────────────────┐
│              OpenFeign 工作原理                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. @EnableFeignClients 开启扫描                         │
│                                                          │
│  2. 扫描 @FeignClient 接口，生成代理对象                 │
│     └── FeignClientFactoryBean.getObject()              │
│         └── ReflectiveFeign.newInstance()                │
│             └── JDK 动态代理                             │
│                                                          │
│  3. 调用接口方法                                         │
│     └── SynchronousMethodHandler.invoke()               │
│         ├── 构建 RequestTemplate                        │
│         ├── 调用 RequestInterceptor (请求拦截)          │
│         ├── 选择 Client (默认 JDK HttpURLConnection)    │
│         │   ├── LoadBalancerFeignClient (负载均衡)      │
│         │   └── Apache HttpClient / OkHttp              │
│         └── 解码响应 (Decoder)                          │
│                                                          │
│  4. 集成 Ribbon/LoadBalancer 实现负载均衡               │
│     └── 从注册中心获取服务实例列表                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 使用示例

```java
// 1. 定义 FeignClient
@FeignClient(name = "user-service", fallbackFactory = UserFallbackFactory.class)
public interface UserClient {

    @GetMapping("/api/user/{id}")
    Result<UserVO> getUser(@PathVariable("id") Long id);

    @PostMapping("/api/user")
    Result<Void> createUser(@RequestBody UserDTO userDTO);
}

// 2. Fallback 降级
@Component
public class UserFallbackFactory implements FallbackFactory<UserClient> {
    @Override
    public UserClient create(Throwable cause) {
        return new UserClient() {
            @Override
            public Result<UserVO> getUser(Long id) {
                return Result.error("用户服务不可用");
            }
            // ...
        };
    }
}
```

---

## Q5: 服务优雅上下线？

### 优雅上线

```
┌──────────────────────────────────────────────────────────┐
│              优雅上线流程                                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 应用启动，初始化 Spring 容器                          │
│  2. 健康检查通过 (数据库/Redis 连接正常)                 │
│  3. 向 Nacos 注册服务实例                               │
│  4. 等待服务发现生效 (默认 30 秒)                        │
│  5. 开始接收请求                                         │
│                                                          │
│  问题: 注册后立即被调用，但容器还没准备好                 │
│                                                          │
│  解决:                                                   │
│  ├── Spring Boot Actuator /health 端点                  │
│  ├── Nacos 元数据标记                                    │
│  └── 延时注册                                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 优雅下线

```
┌──────────────────────────────────────────────────────────┐
│              优雅下线流程                                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 收到 SIGTERM / kill 信号                             │
│  2. 停止接收新请求                                       │
│  3. 等待正在处理的请求完成                               │
│  4. 从 Nacos 注销服务实例                                │
│  5. 等待服务发现生效 (客户端缓存过期)                    │
│  6. 关闭线程池、连接池等资源                             │
│  7. 进程退出                                             │
│                                                          │
│  问题: 注销后客户端可能还有缓存，仍然发请求过来          │
│                                                          │
│  解决:                                                   │
│  ├── Spring 优雅停机 (server.shutdown=graceful)          │
│  ├── Nacos 主动通知客户端                                │
│  └── 下线前 sleep 几秒等待缓存过期                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

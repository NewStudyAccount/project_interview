# Spring Boot

## Q1: 自动装配原理？

```
┌──────────────────────────────────────────────────────────┐
│              @SpringBootApplication 拆解                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  @SpringBootApplication                                  │
│  ├── @SpringBootConfiguration  → 标记为配置类            │
│  ├── @ComponentScan            → 扫描组件                │
│  └── @EnableAutoConfiguration  → 自动装配核心            │
│       └── @Import(AutoConfigurationImportSelector.class) │
│                                                          │
│  流程:                                                   │
│  1. AutoConfigurationImportSelector                     │
│     └─▶ 读取 META-INF/spring/org.springframework.boot   │
│         .autoconfiguration.AutoConfigurationImports      │
│         文件                                              │
│     (Spring Boot 2.7+ 改为 META-INF/spring/             │
│      org.springframework.boot.autoconfigure.             │
│      AutoConfiguration.imports)                          │
│                                                          │
│  2. 获取所有候选自动配置类 (~130+ 个)                    │
│                                                          │
│  3. 通过 @Conditional 系列注解过滤:                      │
│     ├── @ConditionalOnClass      类路径存在某类          │
│     ├── @ConditionalOnMissingBean 容器中不存在某Bean     │
│     ├── @ConditionalOnProperty   配置属性满足条件        │
│     └── @ConditionalOnWebApplication Web 应用            │
│                                                          │
│  4. 满足条件的配置类注册为 Bean                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试答法

> "Spring Boot 自动装配的核心是 @EnableAutoConfiguration 注解，它通过 AutoConfigurationImportSelector 加载 META-INF 下的自动配置类列表，然后通过 @Conditional 系列注解进行条件过滤，只有满足条件的配置类才会被注册为 Bean。"

---

## Q2: @Conditional 系列注解有哪些？

| 注解 | 条件 |
|------|------|
| @ConditionalOnClass | 类路径存在指定类 |
| @ConditionalOnMissingClass | 类路径不存在指定类 |
| @ConditionalOnBean | 容器中存在指定 Bean |
| @ConditionalOnMissingBean | 容器中不存在指定 Bean |
| @ConditionalOnProperty | 配置属性满足条件 |
| @ConditionalOnResource | 存在指定资源文件 |
| @ConditionalOnWebApplication | 是 Web 应用 |
| @ConditionalOnNotWebApplication | 不是 Web 应用 |
| @ConditionalOnExpression | SpEL 表达式为 true |
| @ConditionalOnJava | Java 版本满足条件 |

### 自定义 Starter 示例

```java
// 1. 自动配置类
@Configuration
@ConditionalOnClass(RedisService.class)
@EnableConfigurationProperties(RedisProperties.class)
public class RedisAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public RedisService redisService(RedisProperties properties) {
        return new RedisService(properties.getHost(), properties.getPort());
    }
}

// 2. 配置属性类
@ConfigurationProperties(prefix = "redis")
public class RedisProperties {
    private String host = "localhost";
    private int port = 6379;
    // getters/setters
}

// 3. 注册自动配置类
// META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
// com.example.RedisAutoConfiguration
```

---

## Q3: Spring Boot 配置文件加载优先级？

```
优先级从高到低:
1. 命令行参数 (--server.port=8081)
2. Java 系统属性 (-Dserver.port=8081)
3. 环境变量
4. file:./config/  (项目config目录)
5. file:./         (项目根目录)
6. classpath:/config/  (resources/config)
7. classpath:/         (resources根目录)
8. application-{profile}.yml (profile特定)
9. application.yml (默认)

高优先级覆盖低优先级，互补配置。
```

### 配置文件格式

| 格式 | 示例 |
|------|------|
| application.properties | server.port=8080 |
| application.yml | server: port: 8080 |
| application.yaml | server: port: 8080 |
| 环境变量 | SERVER_PORT=8080 |
| 命令行参数 | --server.port=8080 |

---

## Q4: Spring Boot 启动流程？

```
┌──────────────────────────────────────────────────────────┐
│              Spring Boot 启动流程                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. new SpringApplication(primarySources)                │
│     ├── 推断应用类型 (Servlet/Reactive/None)            │
│     ├── 加载 ApplicationContextInitializer               │
│     └── 加载 ApplicationListener                        │
│                                                          │
│  2. run(args)                                            │
│     ├── 创建计时器 StopWatch                             │
│     ├── 配置 Headless 模式                               │
│     ├── 获取 SpringApplicationRunListeners               │
│     ├── 准备环境 (prepareEnvironment)                    │
│     │   ├── 创建 ApplicationServletEnvironment           │
│     │   ├── 加载配置文件                                 │
│     │   └── 配置 PropertySources                        │
│     ├── 创建 ApplicationContext                          │
│     ├── 准备上下文 (prepareContext)                      │
│     │   ├── 应用 ApplicationContextInitializers          │
│     │   ├── 加载 Bean 定义                               │
│     │   └── 调用 listeners.contextPrepared              │
│     ├── 刷新上下文 (refreshContext)                      │
│     │   └── AbstractApplicationContext.refresh()         │
│     │       ├── prepareRefresh                          │
│     │       ├── obtainFreshBeanFactory                  │
│     │       ├── prepareBeanFactory                      │
│     │       ├── postProcessBeanFactory                  │
│     │       ├── invokeBeanFactoryPostProcessors         │
│     │       ├── registerBeanPostProcessors              │
│     │       ├── initMessageSource                        │
│     │       ├── initApplicationEventMulticaster         │
│     │       ├── onRefresh                                │
│     │       ├── registerListeners                        │
│     │       ├── finishBeanFactoryInitialization         │
│     │       └── finishRefresh                            │
│     ├── 刷新后处理 (afterRefresh)                        │
│     ├── 调用 runners                                    │
│     │   ├── ApplicationRunner                           │
│     │   └── CommandLineRunner                            │
│     └── 返回 ApplicationContext                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q5: Spring Boot 内嵌 Tomcat 原理？

```
┌──────────────────────────────────────────────────────────┐
│              内嵌 Tomcat 原理                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. spring-boot-starter-web 依赖                         │
│     └── spring-boot-starter-tomcat                       │
│         └── tomcat-embed-core                            │
│                                                          │
│  2. ServletWebServerFactoryAutoConfiguration             │
│     └── @ConditionalOnClass(Servlet.class)              │
│         └── 创建 TomcatServletWebServerFactory           │
│                                                          │
│  3. WebServerFactoryCustomizer 接口                      │
│     └── 自定义 Tomcat 配置                               │
│                                                          │
│  4. ServletWebServerApplicationContext.refresh()         │
│     └── onRefresh()                                     │
│         └── createWebServer()                            │
│             ├── getWebServerFactory()                    │
│             └── factory.getWebServer(servletContextInit) │
│                 └── new Tomcat()                         │
│                                                          │
│  自定义 Tomcat:                                          │
│  @Bean                                                   │
│  public WebServerFactoryCustomizer<TomcatServletWeb      │
│      ServerFactory> tomcatCustomizer() {                 │
│      return factory -> {                                │
│          factory.addConnectorCustomizers(connector -> {  │
│              connector.setMaxPostSize(10 * 1024 * 1024); │
│          });                                            │
│      };                                                 │
│  }                                                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q6: Spring Boot 如何优雅停机？

```yaml
# application.yml
server:
  shutdown: graceful  # 开启优雅停机

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s  # 停机超时时间
```

### 优雅停机流程

```
1. 收到 SIGTERM / kill 信号
2. 停止接收新请求
3. 等待正在处理的请求完成 (超时后强制关闭)
4. 关闭线程池、数据库连接池等资源
5. 关闭 ApplicationContext
6. 进程退出
```

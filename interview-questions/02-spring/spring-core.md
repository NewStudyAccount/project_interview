# Spring Core

## Q1: IoC 和 DI 的理解？

**回答模板：**

> "IoC（控制反转）是一种设计思想，将对象的创建和依赖关系的管理从代码中转移到容器。以前我们 `new UserService()`，现在由 Spring 容器创建并注入。DI（依赖注入）是 IoC 的具体实现方式，包括构造器注入、Setter 注入和字段注入（@Autowired）。推荐构造器注入，因为可以保证依赖不可变，且能发现循环依赖。"

### 三种注入方式对比

| 方式 | 优点 | 缺点 |
|------|------|------|
| 构造器注入 | 不可变、可发现循环依赖 | 参数多时冗长 |
| Setter 注入 | 灵活、可选依赖 | 不可变、可能遗漏 |
| 字段注入 (@Autowired) | 简洁 | 不可测试、隐藏依赖 |

---

## Q2: Bean 的生命周期？（高频）

```
┌──────────────────────────────────────────────────────────┐
│                 Bean 生命周期 (11步)                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 实例化 Instantiation                                  │
│     └─▶ 通过构造方法创建对象                              │
│  2. 属性赋值 Populate                                     │
│     └─▶ @Autowired / @Value 注入                         │
│  3. Aware 接口回调                                        │
│     ├─▶ BeanNameAware                                    │
│     ├─▶ BeanClassLoaderAware                             │
│     └─▶ BeanFactoryAware                                │
│  4. BeanPostProcessor.postProcessBeforeInitialization    │
│     └─▶ @PostConstruct 在这里执行                        │
│  5. InitializingBean.afterPropertiesSet                  │
│  6. 自定义 init-method                                   │
│  7. BeanPostProcessor.postProcessAfterInitialization     │
│     └─▶ AOP 代理在这里生成                               │
│  ──── Bean 可用 ────                                     │
│  8. 使用中...                                            │
│  ──── 容器关闭 ────                                      │
│  9. @PreDestroy                                          │
│  10. DisposableBean.destroy                              │
│  11. 自定义 destroy-method                               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q3: 循环依赖如何解决？三级缓存？

```
┌──────────────────────────────────────────────────────────┐
│                   三级缓存解决循环依赖                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  一级缓存: singletonObjects     (完成品)                 │
│  二级缓存: earlySingletonObjects (半成品，可能被代理)     │
│  三级缓存: singletonFactories   (ObjectFactory lambda)   │
│                                                          │
│  场景: A 依赖 B, B 依赖 A                                │
│                                                          │
│  1. 创建 A → 实例化 → 放入三级缓存                       │
│  2. A 填充属性 → 发现需要 B                              │
│  3. 创建 B → 实例化 → 放入三级缓存                       │
│  4. B 填充属性 → 发现需要 A                              │
│  5. 从三级缓存获取 A 的 ObjectFactory                    │
│     └─▶ 如果 A 需要 AOP，此时生成代理对象                │
│     └─▶ 放入二级缓存，移除三级缓存                       │
│  6. B 完成初始化 → 放入一级缓存                          │
│  7. A 拿到 B → 完成初始化 → 放入一级缓存                 │
│                                                          │
│  ⚠️ 不能解决的场景:                                      │
│  ├── 构造器注入的循环依赖                                │
│  └── prototype 作用域的循环依赖                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 为什么需要三级缓存而不是两级？

> "第三级缓存存放的是 ObjectFactory，而不是实际对象。这是为了解决 AOP 代理问题。如果 A 需要被代理，必须在创建早期就生成代理对象，而不是在初始化完成后。通过 ObjectFactory 的延迟调用，可以在需要时才创建代理，保证了代理对象的唯一性。"

---

## Q4: AOP 原理？JDK 动态代理 vs CGLIB？

```
┌──────────────────────────────────────────────────────────┐
│                   AOP 实现方式                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  JDK 动态代理 (基于接口)                                 │
│  ├── 实现: java.lang.reflect.Proxy                      │
│  ├── 条件: 目标类实现了接口                              │
│  ├── 原理: 生成接口的代理类，InvocationHandler 拦截      │
│  └── 性能: 调用通过反射，略慢                            │
│                                                          │
│  CGLIB (基于继承)                                        │
│  ├── 实现: 生成目标类的子类                              │
│  ├── 条件: 目标类不能是 final                            │
│  ├── 原理: FastClass 机制索引调用，无需反射              │
│  └── 性能: 生成慢，调用快                                │
│                                                          │
│  Spring 选择策略:                                        │
│  ├── 有接口 → JDK 动态代理 (Spring Boot 2.x 默认 CGLIB) │
│  └── 无接口 → CGLIB                                     │
│                                                          │
│  Spring Boot 2.x 默认使用 CGLIB                          │
│  spring.aop.proxy-target-class=true (默认)               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### AOP 核心概念

| 概念 | 说明 |
|------|------|
| Aspect | 切面，横切关注点的模块化 |
| Join Point | 连接点，程序执行的某个位置 |
| Advice | 通知，切面在特定连接点的动作 |
| Pointcut | 切点，匹配连接点的表达式 |
| Weaving | 织入，将切面应用到目标对象 |

### Advice 类型

```java
@Before("execution(* com.example.service.*.*(..))")
public void before(JoinPoint jp) { ... }

@After("execution(* com.example.service.*.*(..))")
public void after(JoinPoint jp) { ... }

@AfterReturning(pointcut = "...", returning = "result")
public void afterReturning(Object result) { ... }

@AfterThrowing(pointcut = "...", throwing = "ex")
public void afterThrowing(Exception ex) { ... }

@Around("execution(* com.example.service.*.*(..))")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
    // 前置
    Object result = pjp.proceed();
    // 后置
    return result;
}
```

---

## Q5: BeanFactory 和 ApplicationContext 的区别？

| 维度 | BeanFactory | ApplicationContext |
|------|-------------|-------------------|
| 功能 | 基础 IoC 容器 | BeanFactory 的扩展 |
| Bean 实例化 | 懒加载 | 启动时预加载 |
| 国际化 | ❌ | ✅ MessageSource |
| 事件发布 | ❌ | ✅ ApplicationEvent |
| AOP 支持 | 需手动配置 | 自动支持 |
| 资源访问 | ❌ | ✅ ResourceLoader |

### 面试答法

> "BeanFactory 是 Spring 最基础的容器接口，只提供基本的 IoC 功能。ApplicationContext 是它的子接口，增加了事件发布、国际化、AOP 等企业级功能。实际开发中我们用的都是 ApplicationContext。"

---

## Q6: Spring 中的设计模式？

| 设计模式 | 应用场景 |
|----------|----------|
| 工厂模式 | BeanFactory / FactoryBean |
| 单例模式 | Bean 默认作用域 singleton |
| 代理模式 | AOP (JDK动态代理/CGLIB) |
| 模板方法 | JdbcTemplate / RestTemplate |
| 观察者模式 | ApplicationEvent / ApplicationListener |
| 策略模式 | Resource / HandlerMapping |
| 适配器模式 | HandlerAdapter |
| 装饰器模式 | BeanWrapper |

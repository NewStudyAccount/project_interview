# Java 8+ 新特性

## Q1: Lambda 表达式原理？函数式接口？（高频）

### 函数式接口

只有一个抽象方法的接口（可以有 default / static / Object 方法），用 `@FunctionalInterface` 标注：

```java
@FunctionalInterface
public interface Function<T, R> {
    R apply(T t);  // 唯一抽象方法

    default <V> Function<T, V> andThen(Function<? super R, ? extends V> after) {
        return (T t) -> after.apply(apply(t));
    }
}
```

### 常用函数式接口

| 接口 | 抽象方法 | 入参 → 出参 | 典型场景 |
|------|----------|-------------|----------|
| `Function<T,R>` | apply | T → R | 转换映射 |
| `Consumer<T>` | accept | T → void | 消费处理 |
| `Supplier<T>` | get | → T | 延迟创建 |
| `Predicate<T>` | test | T → boolean | 条件过滤 |
| `BiFunction<T,U,R>` | apply | T,U → R | 双参映射 |
| `UnaryOperator<T>` | apply | T → T | 一元运算 |
| `Comparator<T>` | compare | T,T → int | 排序 |

### Lambda 本质

```
┌──────────────────────────────────────────────────────────┐
│                  Lambda 编译前后                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  源码:                                                    │
│    list.forEach(s -> System.out.println(s));             │
│                                                          │
│  编译后: 不是匿名内部类！                                 │
│    invokedynamic #invokeDynamic                          │
│      bootstrap: LambdaMetafactory.metafactory            │
│      实现方法: lambda$main$0 (合成静态方法)               │
│                                                          │
│  运行时:                                                  │
│    1. 首次调用 invokedynamic                             │
│    2. LambdaMetafactory 生成实现接口的类                 │
│    3. 缓存 CallSite，后续直接调用                        │
│                                                          │
│  特点:                                                    │
│  ├── 无额外 .class 文件（匿名内部类会有）                 │
│  ├── 首次解析有开销，之后接近直接调用                     │
│  └── 本质是「方法引用 + 函数式接口适配」                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点

- **Lambda 只能用于函数式接口**，是语法糖，不是匿名内部类
- **变量捕获**：只能引用 effectively final 的局部变量 / 参数
- **this 语义**：Lambda 内 this 指向外部类；匿名内部类 this 指向自身
- **类型推断**：可省略参数类型，由目标类型推断
- **@FunctionalInterface**：编译期检查是否只有一个抽象方法

### 面试答法

> "Lambda 是函数式编程的语法糖，必须用在只有一个抽象方法的函数式接口上，比如 Function、Consumer、Predicate。它不是匿名内部类，编译后通过 invokedynamic 和 LambdaMetafactory 生成实现，没有额外 class 文件。Lambda 可以捕获 effectively final 的局部变量，this 指向外部类。实际写 Stream、线程池任务、回调时非常常用。"

---

## Q2: Stream API 常用操作？并行流？（高频）

### Stream 处理模型

```
┌──────────────────────────────────────────────────────────┐
│                 Stream 处理流水线                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  创建源 → 中间操作(惰性，可多个) → 终端操作(触发计算)     │
│                                                          │
│  list.stream()                                           │
│    .filter(x -> x.getAge() > 18)   // 中间: filter       │
│    .map(User::getName)               // 中间: map         │
│    .sorted()                         // 中间: sorted      │
│    .limit(10)                        // 中间: limit       │
│    .collect(Collectors.toList());    // 终端: collect     │
│                                                          │
│  中间操作返回 Stream，惰性求值，可链式调用                 │
│  终端操作返回具体结果或 void，触发实际迭代                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 常用操作分类

| 类型 | 操作 | 说明 |
|------|------|------|
| 创建 | stream / parallelStream / of / iterate | 从集合或数组创建 |
| 中间 | filter / map / flatMap | 过滤、映射、扁平化 |
| 中间 | sorted / distinct / limit / skip | 排序去重截断 |
| 中间 | peek | 调试窥视（慎用） |
| 终端 | forEach / collect / count | 遍历、收集、计数 |
| 终端 | anyMatch / allMatch / noneMatch | 短路匹配 |
| 终端 | findFirst / findAny / reduce | 查找、归约 |
| 收集 | toList / toMap / groupingBy / partitioningBy | Collectors 工具 |

### 并行流

```
并行流原理:
  底层使用 ForkJoinPool.commonPool()
  将数据拆分成多个子任务并行处理，再合并结果

  ┌──────────┬──────────┬──────────┐
  │  数据块1  │  数据块2  │  数据块3  │
  │  线程1   │  线程2   │  线程3   │
  └────┬─────┴────┬─────┴────┬─────┘
       └──────────┼──────────┘
                  ▼
             合并结果 (reduce/collect)

适用: CPU 密集、数据量大、无状态、可拆分
不适用: 小数据量、IO 密集、有共享可变状态
```

### 面试关键点

- **Stream 只能遍历一次**，再次使用要重新创建
- **不要在 peek/forEach 中修改外部集合**，容易 ConcurrentModificationException
- **flatMap**：一对多映射后压平，如 `List<List<T>> → Stream<T>`
- **toMap 键冲突会抛 IllegalStateException**，需提供 merge 函数
- **并行流线程池是公共的**，业务中大量并行流可能互相影响；可用 `ForkJoinPool` 自定义
- **reduce**：`list.stream().reduce(0, Integer::sum)` 求和

```java
// 典型业务: 按部门分组求平均工资
Map<String, Double> avgSalary = employees.stream()
    .filter(e -> e.getStatus() == 1)
    .collect(Collectors.groupingBy(
        Employee::getDept,
        Collectors.averagingDouble(Employee::getSalary)
    ));

// toMap 避免 key 冲突
Map<Long, User> userMap = users.stream()
    .collect(Collectors.toMap(
        User::getId,
        Function.identity(),
        (oldVal, newVal) -> newVal  // 后者覆盖
    ));
```

### 面试答法

> "Stream 分创建、中间操作、终端操作。中间操作是惰性的，只有终端操作触发计算。常用 filter、map、flatMap、sorted、collect。并行流底层用 ForkJoinPool 把数据拆分并行处理，适合大数据量 CPU 密集场景；小数据或 IO 场景反而更慢，还会占用公共线程池。注意 Stream 只能消费一次，toMap 要处理 key 冲突。"

---

## Q3: Optional 正确用法？常见误用？

### 设计目的

Optional 是为了解决 NPE，表达「可能为空」的返回值，**不是用来替代所有 null**。

### 正确用法

```java
// 1. 作为返回值，替代可能返回 null 的方法
public Optional<User> findById(Long id) {
    return Optional.ofNullable(userMapper.selectById(id));
}

// 2. 安全取值链
String city = Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .orElse("unknown");

// 3. 条件消费
Optional.ofNullable(user)
    .filter(u -> u.getAge() >= 18)
    .ifPresent(u -> sendEmail(u));

// 4. orElseGet（延迟计算，推荐）vs orElse（立即计算）
String s = Optional.empty()
    .orElseGet(() -> heavyInit());  // 才会调用
    // .orElse(heavyInit());        // 不推荐：总是执行

// 5. orElseThrow
User u = opt.orElseThrow(() -> new BizException("用户不存在"));
```

### 常见误用

| 误用 | 问题 | 正确做法 |
|------|------|----------|
| 用 Optional 作字段/方法参数 | 反模式，序列化/语义混乱 | 仅作返回值 |
| `opt.get()` 不判空 | 一样 NPE | isPresent / orElse |
| 用 `isPresent` + `get` 当 if | 失去 Optional 意义 | ifPresent / map |
| 套很多层 `map` 再 get | 可读性差 | 拆步骤或提前判空 |
| `orElse(对象)` 执行重逻辑 | 总是执行 | orElseGet |
| 把所有 null 都包成 Optional | 过度设计 | 局部变量用普通判空即可 |

### 面试答法

> "Optional 主要用于方法返回值，表达可能为空的结果，避免调用方漏判 NPE。常用 map、filter、orElse、orElseGet、ifPresent。注意不要用 Optional 做字段或参数，不要无脑 get，orElse 里放重逻辑要用 orElseGet。Optional 不是为了消灭所有 null，而是让 API 的空值语义更清晰。"

---

## Q4: 方法引用有哪几种？

### 四种形式

| 类型 | 语法 | 等价 Lambda | 示例 |
|------|------|-------------|------|
| 静态方法 | `类名::静态方法` | `(a) -> 类.方法(a)` | `Integer::parseInt` |
| 实例方法(对象) | `对象::实例方法` | `(a) -> 对象.方法(a)` | `str::length` |
| 实例方法(类) | `类名::实例方法` | `(a,b) -> a.方法(b)` | `String::compareTo` |
| 构造方法 | `类名::new` | `(a) -> new 类(a)` | `ArrayList::new` |

```java
// 静态
list.stream().map(Integer::parseInt);
// 等价 map(s -> Integer.parseInt(s))

// 特定对象
String prefix = "id-";
list.stream().map(prefix::concat);

// 类的实例方法（第一个参数是接收者）
list.stream().sorted(String::compareTo);
// 等价 sorted((a, b) -> a.compareTo(b))

// 构造
List<User> users = ids.stream()
    .map(User::new)
    .collect(Collectors.toList());
```

### 面试关键点

- **方法引用是 Lambda 的简化**，不是新特性，编译机制相同
- **`类名::实例方法`** 容易混：第一个参数作为方法调用者
- **重载方法**可能导致推断歧义，需要显式 Lambda
- **构造引用**：`ClassName::new` 可对应无参 / 有参构造，看目标函数式接口

### 面试答法

> "方法引用是 Lambda 的简写，有四种：类名::静态方法、对象::实例方法、类名::实例方法、类名::new。比如 Integer::parseInt、str::length、String::compareTo、ArrayList::new。本质和 Lambda 一样，编译后也是 invokedynamic，只是让代码更简洁。"

---

## Q5: CompletableFuture vs Future？

### 对比

| 维度 | Future | CompletableFuture |
|------|--------|-------------------|
| 异步获取结果 | `get()` 阻塞 | get / getNow / join |
| 链式编排 | ❌ 不支持 | ✅ thenApply/thenCompose |
| 异常处理 | ExecutionException | exceptionally / handle |
| 主动完成 | ❌ | complete / completeExceptionally |
| 多任务组合 | ❌ | allOf / anyOf |
| 回调 | ❌ | whenComplete / thenAccept |

### 编排模型

```
┌──────────────────────────────────────────────────────────┐
│              CompletableFuture 流水线编排                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  CompletableFuture.supplyAsync(() -> queryUser(id))      │
│    .thenApply(user -> user.getDeptId())      // 转换      │
│    .thenCompose(deptId -> queryDept(deptId)) // 扁平化    │
│    .thenCombine(scoreFuture, (dept, score)   // 合并      │
│        -> buildResult(dept, score))                      │
│    .exceptionally(e -> defaultResult())      // 降级      │
│    .thenAccept(r -> log.info("done"));       // 消费      │
│                                                          │
│  thenApply:  同步转换，返回新值                           │
│  thenCompose: 类似 flatMap，嵌套 CompletableFuture 拍平   │
│  thenCombine: 两个异步结果合并                            │
│  allOf / anyOf: 等全部 / 任一完成                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

```java
// 实际：并行调用两个服务再合并
CompletableFuture<User> userF = CompletableFuture.supplyAsync(
    () -> userService.get(id), executor);
CompletableFuture<List<Order>> orderF = CompletableFuture.supplyAsync(
    () -> orderService.listByUser(id), executor);

CompletableFuture<UserDetail> result = userF.thenCombine(orderF,
    (user, orders) -> UserDetail.of(user, orders));
```

### 面试关键点

- **默认线程池是 ForkJoinPool.commonPool**，生产建议传自定义线程池
- **thenApply vs thenCompose**：后者用于返回 CompletableFuture 的异步依赖
- **exceptionally 只捕获上游异常**；`handle` 无论成功失败都执行
- **不要用 get() 无限期阻塞**，用 `get(timeout, unit)` 或 `orTimeout`（JDK9+）
- **串行依赖用 thenCompose / thenApply，并行用 allOf + join**

### 面试答法

> "Future 只能 get 阻塞取结果，没法链式编排和回调。CompletableFuture 支持 thenApply、thenCompose、thenCombine 做任务编排，exceptionally 做降级，allOf/anyOf 做聚合。适合多个 RPC 并行调用再合并的场景。注意默认用公共 ForkJoinPool，生产要传业务线程池；thenApply 是转换，thenCompose 是异步依赖拍平。"

---

## Q6: Java 8 默认方法 / 接口变化？

### 接口能力演进

| 能力 | Java 7 | Java 8+ |
|------|--------|---------|
| 抽象方法 | ✅ | ✅ |
| 默认方法 `default` | ❌ | ✅ |
| 静态方法 `static` | ❌ | ✅ |
| 私有方法 `private` | ❌ | ✅ (Java 9+) |
| 常量 `public static final` | ✅ | ✅ |

```java
public interface List<E> extends Collection<E> {
    // 抽象
    int size();

    // 默认方法：提供默认实现，实现类可覆盖
    default boolean isEmpty() {
        return size() == 0;
    }

    // 接口静态工具方法
    static <T> List<T> of(T... elements) {
        return Arrays.asList(elements);
    }

    // Java 9+：抽公共逻辑
    private static void checkIndex(int i, int size) {
        if (i < 0 || i >= size) throw new IndexOutOfBoundsException();
    }
}
```

### 为什么需要默认方法

```
问题: 接口新增方法 → 所有实现类都要改 → 源码不兼容

场景: Java 8 要给 Collection 加 stream()/forEach()
     → 数百个实现类无法一次性全改

解决: default 提供默认实现，旧实现类不改也能编译运行
     实现类需要时再覆盖

规则:
1. 类实现优先于接口默认方法 (Class wins)
2. 子接口默认方法优先于父接口
3. 冲突时必须显式覆盖，否则编译错误
```

### 面试关键点

- **默认方法不破坏向后兼容**，是接口演化的关键设计
- **菱形继承冲突**：两个接口默认方法同名，实现类必须 override 并 `接口.super.方法()`
- **static 方法不能被实现类继承/覆盖**
- **Comparator.comparing、Collection.stream 等都是默认方法的产物**
- **接口默认方法 ≠ 抽象类**：仍不能有实例字段（只能常量）

### 面试答法

> "Java 8 给接口加了 default 方法和 static 方法。default 让接口可以提供默认实现，新增方法时不用改所有实现类，保证了兼容性，比如 Collection.stream 就是 default。冲突时类实现优先于接口，子接口优先于父接口，多接口冲突必须显式覆盖。Java 9 还允许接口私有方法抽公共逻辑。接口仍然不能有实例字段，和抽象类定位不同。"

---

## Q7: 新时间 API LocalDate/LocalDateTime？与 Date/Calendar 对比？

### 新旧对比

| 维度 | Date / Calendar | java.time |
|------|-----------------|-----------|
| 线程安全 | ❌ | ✅ 不可变 |
| 设计 | 混杂（Date 含时间） | 职责分离 |
| 月份 | 0-based（坑） | 1-based |
| 时区 | 麻烦 | ZonedDateTime |
| 可读性 | 差 | 好 |
| 格式化 | SimpleDateFormat 非线程安全 | DateTimeFormatter 线程安全 |

### 新 API 体系

```
┌──────────────────────────────────────────────────────────┐
│                    java.time 体系                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  LocalDate      只有日期  2024-01-15                      │
│  LocalTime      只有时间  10:30:00                        │
│  LocalDateTime  日期+时间 2024-01-15T10:30:00             │
│  ZonedDateTime  带时区    2024-01-15T10:30+08:00[Asia/…] │
│  Instant        时间戳    UTC 机器时间                    │
│  Duration       时间段    基于秒/纳秒                     │
│  Period         日期段    基于年/月/日                    │
│                                                          │
│  转换:                                                    │
│    LocalDate.now()                                       │
│    LocalDateTime.of(date, time)                          │
│    instant = localDateTime.toInstant(ZoneOffset.UTC)     │
│    local = LocalDateTime.ofInstant(instant, zone)        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

```java
// 格式化（线程安全）
DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
LocalDateTime now = LocalDateTime.now();
String text = now.format(fmt);
LocalDateTime parsed = LocalDateTime.parse(text, fmt);

// 计算
LocalDate today = LocalDate.now();
LocalDate nextWeek = today.plusWeeks(1);
LocalDate firstDay = today.with(TemporalAdjusters.firstDayOfMonth());
long days = ChronoUnit.DAYS.between(today, nextWeek);

// 与 Date 互转
Date date = Date.from(localDateTime.toInstant(ZoneOffset.of("+8")));
LocalDateTime ldt = LocalDateTime.ofInstant(date.toInstant(), ZoneId.systemDefault());
```

### 面试关键点

- **LocalDateTime 等都是不可变对象**，所有 plus/with 返回新对象
- **格式化用 DateTimeFormatter**，不要用 SimpleDateFormat（非线程安全）
- **月份、星期从 1 开始**，避免 Date 的 0-based 坑
- **存储数据库**：JDBC 用 LocalDateTime；Instant 适合跨时区、日志
- **Duration vs Period**：前者精确到秒/纳秒，后者年/月/日

### 面试答法

> "Date 和 Calendar 可变、月份从 0 开始、SimpleDateFormat 非线程安全，所以 Java 8 推出了 java.time。LocalDate 只有日期，LocalDateTime 日期时间，ZonedDateTime 带时区，Instant 是时间戳。它们都是不可变且线程安全的，格式化用 DateTimeFormatter。实际项目里推荐统一用 LocalDateTime，和 Date 互转用 Instant 中转。"

---

## Q8: JVM 层面 Lambda 如何实现（invokedynamic）？

### 字节码视角

```
┌──────────────────────────────────────────────────────────┐
│              Lambda 的 invokedynamic 实现                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  编译产物:                                                │
│    1. 主类中 invokedynamic 指令                           │
│       指向 Bootstrap 方法:                                │
│       LambdaMetafactory.metafactory(...)                 │
│    2. 私有静态方法 lambda$main$0  (Lambda 实现体)         │
│    3. 不生成额外的内部类 .class 文件                      │
│                                                          │
│  首次执行:                                                │
│    1. JVM 调用 bootstrap → 生成实现函数式接口的类         │
│    2. 绑定 CallSite，缓存                                 │
│    3. 后续调用接近直接虚调用                              │
│                                                          │
│  匿名内部类:                                              │
│    生成 Outer$1.class，每次类加载/初始化                  │
│    Lambda: 无新类文件，首次 metafactory 生成              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 对比匿名内部类

| 维度 | Lambda | 匿名内部类 |
|------|--------|------------|
| class 文件 | 无额外文件 | 生成 Outer$1 等 |
| 实现机制 | invokedynamic + metafactory | 真实类 |
| this 指向 | 外部类 | 匿名类自身 |
| 性能 | 首次稍慢，之后快 | 稳定 |
| 可读性 | 高 | 啰嗦 |
| 可序列化 | 需额外处理 | 简单 |

### 面试关键点

- **invokedynamic（Java 7 引入）** 是动态语言支持的关键指令，lambda 复用它
- **LambdaMetafactory** 是 `java.lang.invoke` 下的引导方法
- **串行 vs 并行 Lambda** 的字节码不同实现形式（内部类形式 vs 内联）
- **方法引用** 同样走 invokedynamic，只是实现方法直接绑定已有方法
- **为什么不用匿名内部类**：类爆炸、初始化开销、this 语义混乱

### 面试答法

> "Lambda 编译后不是匿名内部类，而是 invokedynamic 指令，绑定到 LambdaMetafactory。第一次调用时 metafactory 生成实现函数式接口的类并缓存 CallSite，之后接近普通方法调用。Lambda 体变成类中的合成静态方法。好处是没有额外 class 文件，this 指向外部类，首次解析后性能更好。方法引用也是同样的机制，只是直接绑定已有方法。"

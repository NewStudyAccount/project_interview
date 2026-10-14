# 泛型与反射

## Q1: 什么是泛型？泛型擦除？（高频）

### 泛型的作用

```
┌──────────────────────────────────────────────────────────┐
│                      泛型的价值                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 编译期类型检查，避免 ClassCastException               │
│  2. 取出时无需强制转换                                    │
│  3. 提高代码复用与可读性                                  │
│                                                          │
│  List list = new ArrayList();                            │
│  list.add("a");                                          │
│  Integer i = (Integer) list.get(0); // 运行时才炸         │
│                                                          │
│  List<String> list = new ArrayList<>();                  │
│  list.add(1);        // 编译错误                          │
│  String s = list.get(0); // 无需强转                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 泛型擦除

Java 泛型是**伪泛型**：编译期检查，运行期擦除类型参数。

| 阶段 | 行为 |
|------|------|
| 编译期 | 校验类型，生成强制转换 |
| 编译后 | 类型参数被擦除为 Object 或上界 |
| 运行期 | 字节码中无泛型信息（除签名） |

```java
// 源码
public class Box<T> {
    private T value;
    public T get() { return value; }
    public void set(T value) { this.value = value; }
}

// 擦除后（等价）
public class Box {
    private Object value;
    public Object get() { return value; }
    public void set(Object value) { this.value = value; }
}

// 调用处编译器插入 checkcast
Box box = new Box();
box.set("str");
String s = (String) box.get(); // 擦除后字节码层面有强转
```

### 擦除带来的限制

| 限制 | 原因 | 应对 |
|------|------|------|
| 不能 `new T()` | 运行时无 T | 传 Class / 工厂 / Supplier |
| 不能 `new T[]` | 同上 | `Array.newInstance` 或 `Object[]` 强转 |
| 不能 instanceof T | 同上 | 比较 Class 或用通配符 |
| 不能基本类型作类型参数 | 不能擦成 int | 用 Integer |
| 不能 `T.class` | 无字面量 | 传 Class 对象 |
| 重载冲突 | 擦除后签名相同 | 改方法名 |

### 面试关键点

- **泛型信息在字节码的 Signature 属性中保留**，反射可读 `getGenericSuperclass`
- **桥接方法（bridge method）**：擦除后编译器生成，保证多态正确
- **PECS、通配符** 与擦除配合，见下一题
- **泛型类的静态成员不能用类的类型参数**，因为静态属于类

### 面试答法

> "Java 泛型是编译期语法糖，通过类型擦除实现：编译器做类型检查并插入强转，运行时类型参数擦成 Object 或上界。好处是兼容旧代码；限制是不能 new T()、不能 T[]、不能 instanceof T。桥接方法保证擦除后的多态。需要运行时类型时，一般传入 Class 对象或用反射读 Signature。"

---

## Q2: `<? extends T>` 和 `<? super T>` 区别？PECS 原则？（高频）

### 通配符对比

| 语法 | 含义 | 读（生产） | 写（消费） |
|------|------|------------|------------|
| `? extends T` | T 或其子类（上界） | ✅ 按 T 读 | ❌（null 除外） |
| `? super T` | T 或其父类（下界） | ❌（只能当 Object） | ✅ 写 T 或 T 子类 |
| `?` | 任意类型 | 当 Object | ❌ |

```
┌──────────────────────────────────────────────────────────┐
│                    PECS 原则                              │
│           Producer Extends, Consumer Super                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Producer (你从集合读，它是生产者) → extends              │
│    List<? extends Number> src = ...;                     │
│    Number n = src.get(0);        // ✅                   │
│    src.add(1);                   // ❌ 编译错误           │
│                                                          │
│  Consumer (你往集合写，它是消费者) → super                │
│    List<? super Integer> dest = ...;                     │
│    dest.add(1);                  // ✅                   │
│    Integer x = dest.get(0);      // ❌ 只能 Object        │
│                                                          │
│  经典: copy(List<? extends T> src, List<? super T> dest)  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

```java
// Collections.copy 的签名就是 PECS
public static <T> void copy(
        List<? super T> dest,   // 消费 T
        List<? extends T> src   // 生产 T
) {
    for (T t : src) {
        dest.add(t);
    }
}

// 实际：求和所有 Number 子类
public double sum(List<? extends Number> list) {
    double s = 0;
    for (Number n : list) {
        s += n.doubleValue();
    }
    return s;
}
```

### 为什么不直接 List\<Object\>？

| 场景 | `List<Object>` | `List<? extends Number>` |
|------|----------------|--------------------------|
| 能否接受 `List<Integer>` | ❌ | ✅ |
| 读取 | Object | Number |
| 语义 | 任意对象 | Number 的某种子类型 |

### 面试关键点

- **`List<Integer>` 不是 `List<Object>` 的子类**（泛型不变性）
- **通配符解决的是「类型参数协变/逆变」问题**
- **无界 `?` 只读不写**，相当于 `? extends Object`
- **方法返回值一般不使用通配符**（难以使用）
- **数组协变但不安全，泛型不变但安全**：`Object[] arr = new String[10]` 合法

### 面试答法

> "extends 是上界，适合只读生产者，写入会编译失败；super 是下界，适合写入消费者，读出来只能当 Object。记住 PECS：Producer Extends, Consumer Super。比如 Collections.copy 的 src 是 extends，dest 是 super。通配符解决的是泛型不变性问题，List<Integer> 不能赋给 List<Object>，但可以用 List<? extends Number> 接受。"

---

## Q3: 泛型数组为什么不能直接创建？

### 原因

```
┌──────────────────────────────────────────────────────────┐
│                 为什么不能 new T[] / new List<String>[10]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 数组是协变且运行时 reified 的（知道元素真实类型）      │
│     String[] strs = new String[10];                      │
│     strs[0] = 1;  // 运行时 ArrayStoreException          │
│                                                          │
│  2. 泛型是不变且类型擦除的，运行时不知道 T / String         │
│     无法生成正确的数组类型，也无法做 ArrayStore 检查       │
│                                                          │
│  3. 若允许 new List<String>[10]:                          │
│     Object[] objs = arr;                                 │
│     objs[0] = new ArrayList<Integer>(); // 静默成功       │
│     // 后续取出当 List<String> 用会炸                     │
│                                                          │
│  结论: 为保证类型安全，禁止创建泛型数组                    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 合法 / 非法对照

```java
// ❌ 非法
// new T[]
// new List<String>[]
// new E[10]

// ✅ 合法
List<String>[] arr = new List[10];          // 原生类型数组，有 unchecked 警告
List<?>[] arr2 = new List<?>[10];           // 通配符可以
String[] strs = new String[10];             // 具体类型可以

// 需要「泛型数组」时的替代：
// 1. 用 List<T> 而不是 T[]
// 2. 用 Array.newInstance + 强转
@SuppressWarnings("unchecked")
T[] array = (T[]) Array.newInstance(clazz, size);

// 3. 传入 T[] 现成数组（常见于 toArray）
T[] toArray(T[] a);
```

### 面试关键点

- **数组 reified（保留运行时元素类型），泛型 erased**，两者体系冲突
- **`new ArrayList<String>[10]` 编译错误；`new ArrayList[10]` 可以但不安全**
- **`toArray()` 两种形式**：无参返回 `Object[]`，带参尽量填入正确类型数组
- **可变参数 `T...` 本质是数组**，会有堆污染（heap pollution）警告

### 面试答法

> "不能直接创建泛型数组，是因为数组运行时保留真实元素类型且协变，而泛型会被擦除、类型不变。若允许 new List<String>[]，就可以通过 Object[] 引用塞入 List<Integer>，破坏类型安全。实际用 List 代替数组，或用 Array.newInstance 创建后再强转。通配符数组 List<?>[] 是允许的。"

---

## Q4: 反射原理？获取 Class 对象的几种方式？（高频）

### 反射原理

```
┌──────────────────────────────────────────────────────────┐
│                    Java 反射机制                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  .class 文件                                              │
│       │  类加载                                            │
│       ▼                                                  │
│  方法区中的 Class 对象 (元数据)                           │
│  ┌────────────────────────────┐                          │
│  │ Constructor[]              │                          │
│  │ Method[]                   │                          │
│  │ Field[]                    │                          │
│  │ Annotation[]               │                          │
│  └────────────────────────────┘                          │
│       │  运行时动态获取并调用                              │
│       ▼                                                  │
│  new 实例 / invoke 方法 / get/set 字段                    │
│                                                          │
│  核心: 在运行时解析类的结构，突破编译期确定性              │
│  入口: java.lang.Class                                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 获取 Class 的三种（四种）方式

```java
// 1. 类名.class（编译期安全，最推荐）
Class<String> c1 = String.class;

// 2. 对象.getClass()（运行时实际类型）
Class<? extends String> c2 = "hello".getClass();

// 3. Class.forName（全限定名，可配置，会触发静态初始化）
Class<?> c3 = Class.forName("java.lang.String");
Class<?> c3b = Class.forName("com.mysql.cj.jdbc.Driver"); // JDBC 驱动加载

// 4. 类加载器（较少直接用）
Class<?> c4 = ClassLoader.getSystemClassLoader()
        .loadClass("java.lang.String");

// 基本类型 / 数组
int.class;
int[].class;
void.class;
```

| 方式 | 是否初始化 | 场景 |
|------|------------|------|
| `Xxx.class` | 否 | 一般反射、注解 |
| `obj.getClass()` | 已初始化 | 已有实例 |
| `Class.forName` | **是**（默认） | JDBC、框架、配置类名 |
| `loadClass` | 否 | 自定义类加载 |

### 面试关键点

- **Class 对象在方法区（JDK8 前永久代，JDK8+ 元空间）**
- **一个类在同一个类加载器下只有一个 Class 对象**
- **forName 会执行静态代码块**；`forName(name, false, loader)` 可不初始化
- **反射可越过泛型检查**（擦除），也可读取泛型 Signature
- **Class、Constructor、Method、Field 都在 java.lang.reflect**

### 面试答法

> "反射是运行时动态获取类结构并调用的能力，核心入口是 Class 对象，它在类加载时创建，保存构造器、方法、字段等元数据。获取方式有类名.class、对象.getClass()、Class.forName、类加载器 loadClass。其中 forName 会触发类初始化，常用于 JDBC 驱动；.class 更安全且不初始化。框架里 IOC、AOP、序列化都依赖反射。"

---

## Q5: 反射性能为什么低？如何优化？

### 性能损耗来源

| 阶段 | 损耗 | 说明 |
|------|------|------|
| 访问检查 | 高 | setAccessible(false) 时每次校验权限 |
| 动态解析 | 中 | 运行时查找 Method/Field |
| 参数装箱 | 中 | 基本类型需装箱，Object[] 传参 |
| 无法内联 | 中 | JIT 难以内联动态调用 |
| 抛异常路径 | 高 | get/set 出错走异常 |

```
性能粗略对比 (数量级):
  直接调用      ████████  ~1x
  MethodHandle  ██████████ ~1-2x
  反射(缓存后)  ██████████████████ ~10-20x
  反射(每次找)  ████████████████████████ ~30-50x

  反射不是不能用，关键是别在热点路径反复 getMethod
```

### 优化手段

```java
// 1. 缓存 Class / Method / Field（最重要）
private static final Map<String, Method> CACHE = new ConcurrentHashMap<>();

Method m = CACHE.computeIfAbsent(name, k -> {
    try {
        Method method = clazz.getMethod(k, paramTypes);
        method.setAccessible(true); // 关闭访问检查
        return method;
    } catch (NoSuchMethodException e) {
        throw new RuntimeException(e);
    }
});
m.invoke(target, args);

// 2. setAccessible(true) 跳过安全检查
// 3. 使用 MethodHandle / LambdaMetafactory（JDK7/8+，更快）
// 4. 编译期生成代码替代反射：注解处理器、MapStruct、Javassist、ASM
// 5. 框架实践：Spring 的 CachedIntrospectionResults、反射结果缓存
// 6. 避免在循环中反复 getDeclaredMethod
```

### 面试关键点

- **反射慢在「每次查找 + 访问检查 + 装箱」，不是绝对不能用**
- **Spring/MyBatis 大量用反射但启动时缓存，运行期接近正常调用**
- **`setAccessible(true)` 在 JDK9+ 模块系统下可能被拒绝**（强封装）
- **热点路径能静态调用就静态**；工具类反射要加缓存
- **MethodHandle** 比反射更接近直接调用，可配合 LambdaMetafactory

### 面试答法

> "反射慢主要有三点：每次动态查找方法字段、安全访问检查、基本类型装箱。优化上最重要的是缓存 Method 对象并 setAccessible(true)，避免循环里反复 getMethod。再进一步可以用 MethodHandle 或编译期代码生成。Spring 这类框架启动时缓存反射元数据，所以运行时损耗可控。对性能敏感的热点路径尽量避免反射。"

---

## Q6: 动态代理：JDK 动态代理 vs CGLIB 原理与区别？（高频）

### 对比

| 维度 | JDK 动态代理 | CGLIB |
|------|--------------|-------|
| 要求 | 必须实现接口 | 不要求接口 |
| 实现 | `java.lang.reflect.Proxy` | 字节码生成（ASM） |
| 产物 | 实现接口的代理类 | 被代理类的子类 |
| 调用 | InvocationHandler | MethodInterceptor |
| final 方法 | 可代理（接口方法） | **不能**（无法重写） |
| 性能 | 调用稍慢，创建快 | 创建慢，调用可更快 |
| 依赖 | JDK 自带 | 需要 cglib/asm（Spring 内嵌） |

```
┌──────────────────────────────────────────────────────────┐
│              两种动态代理结构                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  JDK:                                                    │
│    Target implements UserService                         │
│    Proxy → 实现 UserService，持有 InvocationHandler       │
│    调用: proxy.add() → handler.invoke(proxy, method, args)│
│                                                          │
│  CGLIB:                                                  │
│    Target (普通类)                                        │
│    Proxy extends Target (生成子类)                        │
│    调用: proxy.add() → MethodInterceptor.intercept(...)  │
│    限制: final 类/方法无法代理                            │
│                                                          │
│  Spring AOP 选择:                                         │
│    有接口 → 默认 JDK 代理                                 │
│    无接口 → CGLIB                                        │
│    spring.aop.proxy-target-class=true → 强制 CGLIB       │
│    (Spring Boot 2.x 默认 CGLIB)                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

```java
// JDK 动态代理
UserService proxy = (UserService) Proxy.newProxyInstance(
    loader,
    new Class[]{UserService.class},
    (p, method, args) -> {
        before();
        Object result = method.invoke(target, args); // 调目标
        after();
        return result;
    }
);
```

### 面试关键点

- **JDK 代理只能代理接口方法**，类本身的方法调用不到
- **CGLIB 通过继承实现，final/static/private 方法不能代理**
- **自调用（this.method()）不走代理**，事务失效经典原因
- **代理类在运行时生成字节码，可能占用 Metaspace**
- **JDK 8+ 对 Proxy 有缓存，重复接口不会重复生成**

### 面试答法

> "动态代理分 JDK 和 CGLIB。JDK 基于接口，用 Proxy.newProxyInstance 生成实现接口的类，回调 InvocationHandler；CGLIB 基于 ASM 生成目标类的子类，回调 MethodInterceptor，不能代理 final 方法。Spring AOP 默认有接口用 JDK、无接口用 CGLIB，Spring Boot 默认强制 CGLIB。要注意自调用不走代理，这是 @Transactional 失效的常见原因。"

---

## Q7: 反射能破坏封装吗？setAccessible？

### 访问控制

```
┌──────────────────────────────────────────────────────────┐
│                 反射与封装性                               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Java 封装: private 字段/方法 类外不可直接访问             │
│  反射能力: Class.getDeclaredXxx 可拿到私有成员             │
│           setAccessible(true) 关闭访问检查                │
│           → 可以 get/set 私有字段、调用私有方法            │
│                                                          │
│  即: 反射可以「破坏」封装，但有边界                       │
│                                                          │
│  边界 / 现代限制:                                         │
│  ├── SecurityManager（历史，可禁反射）                    │
│  ├── JDK9 模块系统: 强封装 java.base 等                   │
│  │     未 opens 的包 setAccessible 会失败                 │
│  ├── 非 static 访问私有成员在不同模块可能拒绝             │
│  └── 生产代码不应依赖反射破坏封装                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

```java
class Secret {
    private String password = "123456";
    private String reveal() { return password; }
}

// 反射强行读取
Field f = Secret.class.getDeclaredField("password");
f.setAccessible(true);
String pwd = (String) f.get(new Secret()); // "123456"

Method m = Secret.class.getDeclaredMethod("reveal");
m.setAccessible(true);
String r = (String) m.invoke(new Secret());

// JDK9+ 模块未 opens 时，上述 setAccessible 可能抛
// InaccessibleObjectException
```

### 面试关键点

- **封装是编译期/语言层约束，反射是运行时后门**
- **框架（Spring、Jackson、ORM）需要 setAccessible 注入私有字段**
- **JDK 9+ 对 JDK 内部类强封装**，`--add-opens` 可临时打开
- **滥用反射破坏封装会导致维护困难、安全风险**
- **record、不可变对象 + 反射** 也要注意边界

### 面试答法

> "可以。反射能拿到 private 成员，setAccessible(true) 会关闭访问检查，从而读写私有字段、调用私有方法。这是框架能注入私有依赖的原因。但语言层封装和运行时反射是两层约束，JDK9 模块系统对未 opens 的包会拒绝 setAccessible。业务代码不应该依赖反射破坏封装，那是框架内部用的，滥用会有安全和维护问题。"

---

## Q8: 注解的原理？元注解？运行时注解如何解析？

### 注解本质

```
┌──────────────────────────────────────────────────────────┐
│                     注解原理                               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  @interface 声明 → 本质是继承 java.lang.Annotation 的接口 │
│  成员只能是: 基本类型/String/Class/enum/注解/它们的数组    │
│  默认值用 default                                         │
│                                                          │
│  生命周期 (RetentionPolicy):                              │
│    SOURCE   只在源码，编译后丢弃 (如 @Override)           │
│    CLASS    字节码中，默认，运行时不可见                  │
│    RUNTIME  运行时可反射读取 (如 @Autowired)              │
│                                                          │
│  解析方式:                                                │
│    1. 编译期: 注解处理器 (APT, 如 Lombok、MapStruct)      │
│    2. 运行期: 反射 getAnnotation / 扫描 classpath         │
│    3. 字节码期: ASM / Javassist 读取                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 元注解

| 元注解 | 作用 | 常用值 |
|--------|------|--------|
| `@Target` | 可标注的位置 | TYPE、METHOD、FIELD… |
| `@Retention` | 生命周期 | SOURCE / CLASS / RUNTIME |
| `@Documented` | 是否进 javadoc | — |
| `@Inherited` | 是否被子类继承 | 仅对 class 有效 |
| `@Repeatable` | 可重复标注 | Java 8+ |

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Cacheable {
    String key();
    int expire() default 60;
}

// 运行时解析
Method method = UserService.class.getMethod("getById", Long.class);
if (method.isAnnotationPresent(Cacheable.class)) {
    Cacheable ann = method.getAnnotation(Cacheable.class);
    String key = ann.key();
    int expire = ann.expire();
    // 做缓存逻辑
}
```

### 运行时注解解析流程（Spring 为例）

```
1. 启动扫描: ClassPathScanningCandidateComponentProvider
2. 读取类/方法/字段上的注解 (ASM 预筛 + 反射确认)
3. 组装 BeanDefinition / 拦截器链 / 配置
4. AOP 代理: 根据 @Transactional 等生成代理
5. 运行期方法调用进入代理 → 读注解 → 执行切面
```

### 面试关键点

- **注解不会改变业务逻辑**，必须有解析器（框架/处理器）才生效
- **@Inherited 只对类上的注解有效**，方法/字段注解不会继承
- **@Repeatable**：Java 8+，容器注解保存多个
- **注解 + APT** 可在编译期生成代码，零反射开销（Lombok）
- **注解 + 反射** 最灵活但有性能损耗（Spring 缓存注解元数据）

### 面试答法

> "注解本质是继承 Annotation 的接口，成员有类型限制。@Retention 决定 SOURCE、CLASS、RUNTIME 三种生命周期，只有 RUNTIME 才能反射读取。元注解有 Target、Retention、Inherited、Repeatable。运行时解析靠 getAnnotation，编译期靠注解处理器 APT。注解本身不干活，Spring 是扫描并缓存注解元数据，再生成代理或注入依赖。业务自定义注解一般 Retention=RUNTIME，配合拦截器或 AOP 使用。"

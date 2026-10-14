# Java 基础

## Q1: String / StringBuilder / StringBuffer 区别？String 不可变原因？（高频）

### 三者对比

| 维度 | String | StringBuilder | StringBuffer |
|------|--------|---------------|--------------|
| 可变性 | ❌ 不可变 | ✅ 可变 | ✅ 可变 |
| 线程安全 | ✅ (不可变) | ❌ | ✅ (synchronized) |
| 性能 | 拼接慢 | 最快 | 较快 |
| 底层 | `final char[]` / `byte[]` | `char[]` | `char[]` |
| 使用场景 | 常量、少量拼接 | 单线程大量拼接 | 多线程大量拼接 |

### String 不可变的原因

```
┌──────────────────────────────────────────────────────────┐
│                  String 不可变设计                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. final class，不能被继承                               │
│  2. 内部 value 数组被 final 修饰，引用不可变               │
│  3. 所有修改方法 (concat/replace) 都返回新对象             │
│  4. 不对外暴露修改内部状态的方法                           │
│                                                          │
│  好处:                                                    │
│  ├── 字符串常量池复用，节省内存                            │
│  ├── hashCode 可缓存，HashMap key 更快                    │
│  ├── 天然线程安全，可安全共享                              │
│  └── 安全性: 类加载路径、数据库连接串等不可被篡改          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点

- **JDK 9+ 底层改为 `byte[]` + coder**：Latin1 用 1 字节，UTF-16 用 2 字节，节省内存
- **编译器优化**：`String a = "a" + "b"` 编译期合并为 `"ab"`；`final String` 拼接也会合并
- **循环拼接陷阱**：循环内 `s += i` 每次生成新对象，必须用 StringBuilder
- **String.intern()**：将字符串放入常量池，返回常量池引用；JDK 7+ 常量池在堆中

```java
// 循环拼接：错误 vs 正确
// 错误：每次循环 new StringBuilder + toString，O(n^2) 空间
String s = "";
for (int i = 0; i < 10000; i++) {
    s += i;
}

// 正确
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append(i);
}
String result = sb.toString();
```

### 面试答法

> "String 是不可变的，底层 value 数组是 final 的，所有修改方法都返回新对象。这样设计的好处是可复用常量池、hashCode 可缓存、天然线程安全。可变字符串用 StringBuilder，单线程性能最好；多线程用 StringBuffer，方法加了 synchronized。循环里拼接一定要用 StringBuilder，不要用 `+=`。"

---

## Q2: ==、equals、hashCode 三者关系？重写 equals 必须重写 hashCode？（高频）

### 三者关系

| 操作 | 基本类型 | 引用类型 |
|------|----------|----------|
| `==` | 比较值 | 比较引用地址 |
| `equals()` | — | 默认同 `==`，可重写为值比较 |
| `hashCode()` | — | 返回哈希码，用于哈希容器定位 |

### 核心契约

```
┌──────────────────────────────────────────────────────────┐
│              equals / hashCode 契约                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. equals 相等  →  hashCode 必须相等                     │
│  2. hashCode 相等 →  equals 不一定相等 (哈希冲突)          │
│  3. 重写 equals 必须重写 hashCode                        │
│                                                          │
│  反例: 只重写 equals 不重写 hashCode                       │
│  ┌────────────────────────────────────────┐              │
│  │  HashMap 中 put(a) / get(b)             │              │
│  │  a.equals(b) == true                    │              │
│  │  但 a.hashCode() != b.hashCode()        │              │
│  │  → 落到不同桶，get 返回 null            │              │
│  └────────────────────────────────────────┘              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 规范写法

```java
public class User {
    private String name;
    private int age;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        User user = (User) o;
        return age == user.age && Objects.equals(name, user.name);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, age);
    }
}
```

### 面试关键点

- **`==` 对基本类型比值，对引用类型比地址**
- **String 重写了 equals**：内容比较；`new String("a") == new String("a")` 为 false
- **equals 默认实现就是 `==`**（Object 类）
- **Objects.equals** 可空安全，避免 NPE
- **hashCode 只是性能优化**：哈希桶定位后仍用 equals 确认

### 面试答法

> "`==` 对基本类型比值，对引用类型比地址。equals 默认也是比地址，但 String、Integer 等包装类重写成了值比较。Java 规定 equals 相等则 hashCode 必须相等，所以重写 equals 必须重写 hashCode。否则对象作为 HashMap 的 key 时，equals 相等但 hashCode 不同会落到不同桶，导致 get 找不到。实际用 Objects.equals 和 Objects.hash 更安全。"

---

## Q3: final 关键字用法？final 修饰引用 vs 对象？

### 三种用法

| 修饰目标 | 作用 | 说明 |
|----------|------|------|
| 变量 | 引用/值不可变 | 基本类型值不变，引用类型地址不变 |
| 方法 | 不可重写 | 可重载，不能 override |
| 类 | 不可继承 | 如 String、Integer |

### final 引用 vs final 对象

```
┌──────────────────────────────────────────────────────────┐
│            final 修饰引用类型的含义                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  final List<String> list = new ArrayList<>();            │
│                                                          │
│  list = new ArrayList<>();   // ❌ 编译错误，引用不可变   │
│  list.add("a");              // ✅ 对象内容可以变         │
│                                                          │
│  即:                                                      │
│  ├── final 保证的是「引用不能指向别的对象」                 │
│  └── 不保证「对象内部状态不可变」                          │
│                                                          │
│  想要真正的不可变:                                        │
│  1. final 修饰引用                                        │
│  2. 类本身不可变（无修改方法 / 防御性拷贝）                │
│  3. 不泄露 this                                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点

- **final 成员变量必须显式初始化或构造器赋值**（有默认值规则例外）
- **final 参数**：方法内不可重新赋值，常用于匿名内部类捕获
- **final 与不可变**：String 不可变靠的是 final + 无修改方法 + 不暴露内部数组
- **final 常量推荐**：`static final` 编译期常量会内联到使用处
- **final 方法**：早期为性能（内联），现代 JVM 已无必要，主要用于禁止重写

### 面试答法

> "final 修饰变量表示引用不能改，修饰方法表示不能重写，修饰类表示不能继承。需要注意 final 修饰对象引用时，引用地址不可变，但对象内部状态可以变。比如 final List 不能重新赋值，但可以 add。真正不可变对象还要类本身不提供修改方法，并做防御性拷贝。"

---

## Q4: static 关键字？静态代码块执行顺序？

### static 能修饰什么

| 修饰目标 | 含义 | 示例 |
|----------|------|------|
| 成员变量 | 类变量，所有实例共享 | `static int count` |
| 成员方法 | 类方法，不能访问实例成员 | `static void util()` |
| 代码块 | 类加载时执行一次 | `static { ... }` |
| 内部类 | 静态内部类，不持有外部类引用 | `static class Inner` |

### 类初始化顺序

```
┌──────────────────────────────────────────────────────────┐
│              类加载 / 实例化执行顺序                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 父类静态变量 / 静态代码块  (按书写顺序)                │
│  2. 子类静态变量 / 静态代码块  (按书写顺序)                │
│     ——— 以上在类加载时执行一次 ———                        │
│  3. 父类实例变量 / 实例代码块  (按书写顺序)                │
│  4. 父类构造方法                                        │
│  5. 子类实例变量 / 实例代码块  (按书写顺序)                │
│  6. 子类构造方法                                        │
│                                                          │
│  口诀: 静 > 实，父 > 子，变量/块 > 构造器                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

```java
class Parent {
    static { System.out.println("1. Parent static"); }
    { System.out.println("3. Parent instance"); }
    public Parent() { System.out.println("4. Parent ctor"); }
}

class Child extends Parent {
    static { System.out.println("2. Child static"); }
    { System.out.println("5. Child instance"); }
    public Child() { System.out.println("6. Child ctor"); }
}

// new Child() 输出:
// 1. Parent static
// 2. Child static
// 3. Parent instance
// 4. Parent ctor
// 5. Child instance
// 6. Child ctor
```

### 面试关键点

- **静态方法不能用 this / super / 实例变量**，不能被重写（可被隐藏）
- **静态代码块只执行一次**，构造方法每次 new 都执行
- **匿名内部类 / Lambda 中引用局部变量要求 effectively final**
- **static 不是单例**，只是类级别共享；单例还要控制实例化

### 面试答法

> "static 修饰的成员属于类，而不是实例。静态代码块在类加载时执行且只执行一次。创建对象时的顺序是：父类静态 → 子类静态 → 父类实例/构造 → 子类实例/构造。静态方法不能访问实例成员，也不能用 this。实际写常量用 static final，工具方法用 static，工具类还可以私有化构造器。"

---

## Q5: 异常体系？checked vs unchecked？try-catch-finally 执行顺序？（高频）

### 异常体系

```
┌──────────────────────────────────────────────────────────┐
│                    Java 异常体系                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│                     Throwable                            │
│                    /         \                           │
│               Error        Exception                     │
│            (不捕获)       /         \                    │
│                          /           \                   │
│                 IOException    RuntimeException          │
│                 SQLException   NullPointerException      │
│                 ...            IndexOutOfBounds...       │
│                 (checked)      (unchecked)               │
│                                                          │
│  checked:  编译期强制处理 (try-catch 或 throws)           │
│  unchecked: 编译期不强制，运行时抛出                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### checked vs unchecked

| 维度 | checked | unchecked |
|------|---------|-----------|
| 继承 | Exception（非 Runtime） | RuntimeException / Error |
| 编译检查 | 必须处理 | 不强制 |
| 代表 | IOException、SQLException | NPE、IndexOutOfBounds、ClassCast |
| 设计理念 | 可恢复，调用方应处理 | 程序 bug，不该捕获后忽略 |

### try-catch-finally 执行顺序

```java
public static int test() {
    try {
        return 1;
    } catch (Exception e) {
        return 2;
    } finally {
        return 3; // 覆盖 try 的 return！面试陷阱
    }
}
// 返回 3，不是 1
```

```
执行顺序:
1. 执行 try 块
2. 异常 → 匹配 catch → 执行 catch
3. 无论是否异常，执行 finally
4. finally 中的 return / 抛异常 会覆盖 try/catch 的返回值
5. try 中 return 会先暂存返回值，再执行 finally，再真正返回

注意:
- finally 一定会执行吗？不一定：
  System.exit(0) / 线程被杀死 / finally 本身异常
- 资源释放推荐 try-with-resources，而不是手动 finally close
```

### 面试关键点

- **不要捕获 Exception 后只打日志不处理**，也不要 catch Throwable
- **try-with-resources**：实现 AutoCloseable 的资源自动关闭，关闭顺序与声明相反
- **自定义异常**：业务异常继承 RuntimeException，减少 throws 噪音
- **异常链**：`throw new BizException("msg", e)` 保留原始 cause

### 面试答法

> "Java 异常都继承 Throwable，分 Error 和 Exception。Exception 又分 checked 和 unchecked：checked 编译期强制处理，比如 IOException；unchecked 不强制，比如 NPE，通常是程序 bug。try-catch-finally 中 finally 一定会执行，但如果 finally 里 return 会覆盖 try 的返回值，这是常见陷阱。资源释放用 try-with-resources 比手动 finally close 更安全。"

---

## Q6: Object 常用方法？wait/notify/equals/hashCode/toString/finalize

### Object 核心方法一览

| 方法 | 作用 | 是否可重写 |
|------|------|------------|
| `equals(Object)` | 逻辑相等比较 | ✅ 常用 |
| `hashCode()` | 哈希码，配合哈希容器 | ✅ 与 equals 成对 |
| `toString()` | 字符串表示 | ✅ 常用 |
| `getClass()` | 运行时类对象 | ❌ final |
| `clone()` | 浅拷贝 | ✅ 需实现 Cloneable |
| `wait()/notify()/notifyAll()` | 线程间通信 | ❌ final |
| `finalize()` | GC 前回调 | ✅ JDK9 已废弃 |

### wait / notify 机制

```
┌──────────────────────────────────────────────────────────┐
│               wait / notify 线程通信                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  等待方 (消费者)              通知方 (生产者)              │
│  ┌─────────────────┐        ┌─────────────────┐         │
│  │ synchronized(lock){│      │ synchronized(lock){│       │
│  │   while(条件不满足)│      │   改变条件         │       │
│  │     lock.wait(); │       │   lock.notify();  │       │
│  │   业务逻辑        │      │ }                  │       │
│  │ }                │        └─────────────────┘         │
│  └─────────────────┘                                     │
│                                                          │
│  规则:                                                    │
│  1. 必须在 synchronized 中调用 wait/notify                 │
│  2. 用 while 而不是 if 判断条件（虚假唤醒）                │
│  3. wait 释放锁并进入等待队列；notify 不释放锁             │
│  4. notifyAll 比 notify 更安全（避免叫醒错对象）           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点

- **equals 重写规范**：自反、对称、传递、一致、`x.equals(null) == false`
- **toString**：日志排查必备，IDE 一键生成；不要在 toString 里抛 NPE
- **clone 是浅拷贝**：引用类型字段共享，深拷贝需手动或序列化
- **finalize 已废弃（JDK9+ Deprecated）**：不可靠，可能不执行；资源释放用 try-with-resources 或 Cleaner

### 面试答法

> "Object 是所有类的父类。核心方法有 equals、hashCode、toString、getClass、wait/notify、clone、finalize。wait/notify 必须在 synchronized 中调用，wait 释放锁，条件判断要用 while 防虚假唤醒。equals 和 hashCode 要成对重写。clone 默认浅拷贝。finalize 已经废弃，不建议依赖它做资源清理。"

---

## Q7: 自动装箱拆箱？Integer 缓存池？

### 装箱 / 拆箱本质

```java
// 自动装箱：编译后实际是 Integer.valueOf(int)
Integer a = 100;   // 等价于 Integer a = Integer.valueOf(100);

// 自动拆箱：编译后实际是 intValue()
int b = a;         // 等价于 int b = a.intValue();
```

### Integer 缓存池

```
┌──────────────────────────────────────────────────────────┐
│                 Integer 缓存机制                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Integer.valueOf(int i):                                 │
│    if (i >= -128 && i <= 127)                            │
│        return IntegerCache.cache[i + 128];  // 复用       │
│    return new Integer(i);                   // 新对象     │
│                                                          │
│  Integer a = 127;  Integer b = 127;                      │
│  a == b  →  true   (缓存同一对象)                        │
│                                                          │
│  Integer c = 128;  Integer d = 128;                      │
│  c == d  →  false  (各自 new)                            │
│                                                          │
│  缓存范围: 默认 -128 ~ 127                               │
│  可通过 -XX:AutoBoxCacheMax=N 调整上限                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点与坑

| 场景 | 结果 | 原因 |
|------|------|------|
| `Integer a=127,b=127; a==b` | true | 缓存 |
| `Integer a=128,b=128; a==b` | false | 超出缓存 |
| `Integer a=null; int b=a` | NPE | 拆箱调用 intValue() |
| `Long` 比较用 `==` | 可能错 | 应用 equals |
| `Double/Float` 缓存 | 无 | 只缓存整型相关 |
| `Boolean` 缓存 | true/false | 全部缓存 |

### 面试答法

> "自动装箱就是编译器帮你调用 Integer.valueOf，拆箱调用 intValue。Integer 对 -128 到 127 做了缓存，这个范围内 valueOf 返回同一对象，所以 `==` 为 true，超出范围就 false。两个 Integer 比较应该用 equals。另外拆箱时如果引用是 null 会 NPE，集合泛型里装箱也比基本类型更耗内存。"

---

## Q8: 深拷贝 vs 浅拷贝？如何实现深拷贝？

### 对比

| 维度 | 浅拷贝 | 深拷贝 |
|------|--------|--------|
| 基本类型 | 复制值 | 复制值 |
| 引用类型 | 复制引用（共享对象） | 递归复制新对象 |
| Object.clone() | ✅ 默认浅拷贝 | ❌ 需手动 |
| 修改嵌套对象 | 原对象也会变 | 互不影响 |
| 性能 | 快 | 慢，可能递归很深 |

```
浅拷贝:
  原对象 A ──► Inner ──► 值
  拷贝 B  ──┘  (共享同一 Inner)

深拷贝:
  原对象 A ──► Inner1 ──► 值
  拷贝 B  ──► Inner2 ──► 值   (各自独立)
```

### 实现方式

```java
// 1. Cloneable + clone()：手动克隆引用字段
public class Address implements Cloneable {
    private String city;
    @Override
    protected Address clone() throws CloneNotSupportedException {
        return (Address) super.clone();
    }
}

public class User implements Cloneable {
    private String name;
    private Address address;

    @Override
    protected User clone() throws CloneNotSupportedException {
        User copy = (User) super.clone();
        copy.address = address.clone(); // 关键：克隆引用字段
        return copy;
    }
}

// 2. 序列化（通用，但慢）
public static <T extends Serializable> T deepCopy(T obj) throws Exception {
    ByteArrayOutputStream bos = new ByteArrayOutputStream();
    try (ObjectOutputStream oos = new ObjectOutputStream(bos)) {
        oos.writeObject(obj);
    }
    try (ObjectInputStream ois = new ObjectInputStream(
            new ByteArrayInputStream(bos.toByteArray()))) {
        return (T) ois.readObject();
    }
}

// 3. 手动 new + 属性拷贝（推荐，可控）
User copy = new User();
copy.setName(user.getName());
copy.setAddress(new Address(user.getAddress().getCity()));
```

### 面试关键点

- **String、包装类、不可变对象浅拷贝共享没问题**
- **clone() 要实现 Cloneable 接口**，否则抛 CloneNotSupportedException
- **构造器 / 工厂方法手动拷贝**最清晰，项目中最常用
- **JSON 反序列化**（fastjson/jackson）也常用来做深拷贝，注意循环引用

### 面试答法

> "浅拷贝复制对象本身，引用字段仍然共享；深拷贝会递归复制引用对象，两边完全独立。Object.clone 默认浅拷贝。深拷贝常见做法：一是 clone 方法里手动 clone 引用字段；二是序列化反序列化；三是手动 new 对象拷贝属性。业务代码里手动拷贝或 JSON 序列化更常见，clone 语法别扭且容易漏字段。"

# 集合框架

## Q1: HashMap 底层原理？

```
┌──────────────────────────────────────────────────────────┐
│                   HashMap 底层结构                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  JDK 8+: 数组 + 链表 + 红黑树                            │
│                                                          │
│  ┌───┬───┬───┬───┬───┬───┬───┬───┐                     │
│  │ 0 │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │  Node[] table      │
│  └───┴─┬─┴───┴─┬─┴───┴───┴───┴───┘                     │
│        │       │                                        │
│        ▼       ▼                                        │
│      ┌───┐   ┌───┐                                      │
│      │ K │   │ K │   链表 (长度<8)                      │
│      │ V │   │ V │                                      │
│      └─┬─┘   └─┬─┘                                      │
│        │       │                                        │
│        ▼       ▼                                        │
│      ┌───┐   ┌───┐                                      │
│      │ K │   │ K │                                      │
│      │ V │   │ V │                                      │
│      └───┘   └───┘                                      │
│                                                          │
│  当链表长度 ≥ 8 且数组长度 ≥ 64 → 转红黑树               │
│  当红黑树节点 ≤ 6 → 退化为链表                           │
│                                                          │
│  扩容: 容量 × 2, 阈值 × 2                               │
│  新位置 = 原位置 或 原位置 + 旧容量                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点

- **hash 扰动**：`(h = key.hashCode()) ^ (h >>> 16)` 高位参与运算减少碰撞
- **容量必须是 2 的幂**：`(n-1) & hash` 等价于 `hash % n`，位运算更快
- **为什么链表转红黑树阈值是 8**：泊松分布，链表长度达到 8 的概率约 0.00000006
- **线程不安全**：多线程 put 可能数据丢失，JDK 8 前还可能死循环（头插法）

### HashMap 核心源码

```java
// 计算 hash 值
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}

// put 流程
public V put(K key, V value) {
    return putVal(hash(key), key, value, false, true);
}

final V putVal(int hash, K key, V value, boolean onlyIfAbsent, boolean evict) {
    Node<K,V>[] tab; Node<K,V> p; int n, i;
    // 1. 表为空则初始化
    if ((tab = table) == null || (n = tab.length) == 0)
        n = (tab = resize()).length;
    // 2. 计算索引，桶为空直接放
    if ((p = tab[i = (n - 1) & hash]) == null)
        tab[i] = newNode(hash, key, value, null);
    else {
        Node<K,V> e; K k;
        // 3. 桶首节点就是要找的
        if (p.hash == hash && ((k = p.key) == key || (key != null && key.equals(k))))
            e = p;
        // 4. 红黑树节点
        else if (p instanceof TreeNode)
            e = ((TreeNode<K,V>)p).putTreeVal(this, tab, hash, key, value);
        // 5. 链表遍历
        else {
            for (int binCount = 0; ; ++binCount) {
                if ((e = p.next) == null) {
                    p.next = newNode(hash, key, value, null);
                    if (binCount >= TREEIFY_THRESHOLD - 1) // 8-1=7
                        treeifyBin(tab, hash); // 转红黑树
                    break;
                }
                if (e.hash == hash && ((k = e.key) == key || (key != null && key.equals(k))))
                    break;
                p = e;
            }
        }
        // 6. key 已存在，覆盖 value
        if (e != null) {
            V oldValue = e.value;
            if (!onlyIfAbsent || oldValue == null)
                e.value = value;
            return oldValue;
        }
    }
    ++modCount;
    // 7. 超过阈值，扩容
    if (++size > threshold)
        resize();
    return null;
}
```

---

## Q2: ConcurrentHashMap 怎么保证线程安全？

```
┌──────────────────────────────────────────────────────────┐
│              ConcurrentHashMap 演进                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  JDK 7: 分段锁 (Segment)                                │
│  ┌──────────────────────────────────┐                    │
│  │  Segment[0]  Segment[1]  ...     │                    │
│  │  ┌──────┐   ┌──────┐            │                    │
│  │  │ Hash │   │ Hash │            │                    │
│  │  │Entry │   │Entry │            │                    │
│  │  └──────┘   └──────┘            │                    │
│  │  并发度 = Segment 数量           │                    │
│  └──────────────────────────────────┘                    │
│                                                          │
│  JDK 8+: CAS + synchronized                              │
│  ┌──────────────────────────────────┐                    │
│  │  数组初始化: CAS 设置             │                    │
│  │  链表头插入: CAS                  │                    │
│  │  链表/红黑树: synchronized(头节点)│                    │
│  │  扩容: 多线程协助迁移             │                    │
│  └──────────────────────────────────┘                    │
│                                                          │
│  关键改进:                                                │
│  ├── 锁粒度更细: 只锁一个桶 (Node)                      │
│  ├── 放弃分段: Segment 保留但不使用                      │
│  ├── size() 计算: baseCount + CounterCell[] 分散竞争     │
│  └── 扩容: transferIndex 分配迁移区间，多线程协助        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### JDK 7 vs JDK 8 对比

| 维度 | JDK 7 | JDK 8 |
|------|-------|-------|
| 数据结构 | Segment + HashEntry | Node + 红黑树 |
| 锁机制 | 分段锁 (ReentrantLock) | CAS + synchronized |
| 锁粒度 | 段 (默认16段) | 桶 (单个Node) |
| 查询遍历 | 两次 hash 定位 | 一次 hash 定位 |
| 扩容 | 单线程 | 多线程协助 |
| size 计算 | 不加锁 (弱一致性) | baseCount + CounterCell |

---

## Q3: ArrayList vs LinkedList？

| 维度 | ArrayList | LinkedList |
|------|-----------|------------|
| 底层结构 | 动态数组 | 双向链表 |
| 随机访问 | O(1) | O(n) |
| 头部插入 | O(n) (需要移动) | O(1) |
| 尾部插入 | O(1) 均摊 | O(1) |
| 内存占用 | 连续内存 | 每个节点额外指针 |
| 缓存友好 | 好 (局部性) | 差 (内存分散) |

### 面试答法

> "实际开发中，绝大多数场景用 ArrayList。因为 CPU 缓存对连续内存友好，随机访问快。LinkedList 只在头部频繁插入/删除的场景有优势，但这种场景用 ArrayDeque 更好。"

---

## Q4: HashMap、Hashtable、ConcurrentHashMap 的区别？

| 维度 | HashMap | Hashtable | ConcurrentHashMap |
|------|---------|-----------|-------------------|
| 线程安全 | ❌ | ✅ (全表锁) | ✅ (分段/CAS) |
| null key/value | 允许 | 不允许 | 不允许 |
| 性能 | 高 | 低 | 高 |
| 继承关系 | AbstractMap | Dictionary | AbstractMap |
| 推荐使用 | 单线程 | 不推荐 | 多线程 |

---

## Q5: fail-fast 和 fail-safe 的区别？

| 维度 | fail-fast | fail-safe |
|------|-----------|-----------|
| 代表 | HashMap, ArrayList | ConcurrentHashMap, CopyOnWriteArrayList |
| 机制 | modCount 检测 | 遍历副本或弱一致性 |
| 异常 | ConcurrentModificationException | 不抛异常 |
| 场景 | 单线程迭代时修改 | 多线程安全迭代 |

```java
// fail-fast 示例
Map<String, String> map = new HashMap<>();
for (Map.Entry<String, String> entry : map.entrySet()) {
    if ("key".equals(entry.getKey())) {
        map.remove(entry.getKey()); // 抛出 ConcurrentModificationException
    }
}

// 正确做法
Iterator<Map.Entry<String, String>> it = map.entrySet().iterator();
while (it.hasNext()) {
    Map.Entry<String, String> entry = it.next();
    if ("key".equals(entry.getKey())) {
        it.remove(); // 安全删除
    }
}
```

---

## Q6: TreeMap / TreeSet 底层？红黑树？

```
┌──────────────────────────────────────────────────────────┐
│              TreeMap / TreeSet 底层                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  TreeMap: 基于红黑树 (自平衡二叉搜索树)                  │
│  TreeSet: 内部持有 TreeMap，value 是固定的 PRESENT       │
│                                                          │
│        ┌───┐                                             │
│        │ 8 │  黑                                         │
│        └─┬─┘                                             │
│     ┌────┴────┐                                          │
│   ┌─┴─┐     ┌─┴─┐                                       │
│   │ 4 │红   │ 12│红                                      │
│   └─┬─┘     └─┬─┘                                       │
│   ┌─┴─┐     ┌─┴─┐                                       │
│   │ 3 │黑   │ 9 │黑   ...                                │
│   └───┘     └───┘                                        │
│                                                          │
│  红黑树规则:                                             │
│  ├── 节点非红即黑                                       │
│  ├── 根节点黑、叶子(NIL)黑                              │
│  ├── 红节点的子节点必须黑                               │
│  └── 任一节点到 NIL 路径黑节点数相同 → 平衡             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### TreeMap 特性

| 特性 | 说明 |
|------|------|
| 排序 | 按 key 自然序或 Comparator |
| 复杂度 | get/put/remove 均为 O(logN) |
| null key | 不允许（自然序），Comparator 可自定义 |
| 线程安全 | 否，可用 `Collections.synchronizedSortedMap` |
| 范围查询 | `subMap` / `headMap` / `tailMap` / `firstKey` / `lastKey` |

### 面试答法

> "TreeMap 底层是**红黑树**，保证有序且增删查都是 O(logN)。TreeSet 就是 value 占位的 TreeMap。需要排序或范围查询时用它；只要无序存储，HashMap/HashSet 性能更好。"

---

## Q7: ConcurrentHashMap JDK8 为什么放弃分段锁？size() 怎么算？（高频）

### 为什么放弃分段锁

| 原因 | 说明 |
|------|------|
| 锁粒度仍不够细 | 段内冲突仍会串行，默认 16 段并发度有限 |
| 内存开销 | Segment 数组 + 链式 HashEntry，冗余结构多 |
| 扩容低效 | JDK7 扩容锁整段，JDK8 可多线程协同迁移桶 |
| CAS 成熟 | 桶头节点 CAS + 空桶 CAS + synchronized 低开销 |
| 遍历两次定位 | JDK7 先定位 Segment 再定位桶，JDK8 一次 hash |

### JDK8 锁策略

```
┌──────────────────────────────────────────────────────────┐
│           ConcurrentHashMap JDK8 锁细节                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  put 流程:                                               │
│  ├── 表空 → CAS 初始化 Node[]                            │
│  ├── 桶空 → CAS 放首节点 (无锁)                         │
│  ├── 桶头 hash == MOVED → 协助扩容                       │
│  ├── 否则 synchronized(桶头节点) 链表/红黑树插入         │
│  └── 扩容 → transfer，多线程按 transferIndex 认领区间   │
│                                                          │
│  size() 计算:                                            │
│  ├── baseCount: 无竞争时 CAS 累加                       │
│  ├── CounterCell[]: 竞争激烈时分散累加 (类 LongAdder)   │
│  └── sum = baseCount + Σ CounterCell.value              │
│                                                          │
│  注意: size() 是弱一致性的，可能不是精确瞬时值          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试答法

> "JDK8 放弃分段锁，是因为 Segment 并发度有限、内存开销大、扩容要锁整段。改成 **CAS + synchronized 锁桶头**，空桶直接 CAS，冲突时只锁一个 Node，扩容还能多线程协助。size() 用 baseCount + CounterCell[] 分散竞争（类似 LongAdder），最后求和，是弱一致快照，不保证绝对精确。"

---

## Q8: CopyOnWriteArrayList 原理与适用场景？

### 写时复制原理

```java
// CopyOnWriteArrayList#add 核心逻辑
public boolean add(E e) {
    final ReentrantLock lock = this.lock;
    lock.lock();                    // 写操作加锁
    try {
        Object[] elements = getArray();
        int len = elements.length;
        Object[] newElements = Arrays.copyOf(elements, len + 1);
        newElements[len] = e;
        setArray(newElements);      // 写入新数组，volatile 可见
        return true;
    } finally {
        lock.unlock();
    }
}

// 迭代器遍历的是旧数组快照，不会抛 CME
public E get(int index) {
    return getArray()[index];       // 读无锁
}
```

| 维度 | 说明 |
|------|------|
| 读 | 无锁，O(1)，遍历的是快照 |
| 写 | ReentrantLock + 复制整个数组，O(N) |
| 内存 | 写放大，旧数组直到 GC 才回收 |
| 一致性 | 最终一致，读可能读到旧数据 |

### 适用场景

- **读多写极少**：配置列表、白名单、监听器注册表
- **不适合**：频繁写、实时一致性要求高、大数组场景

### 面试答法

> "CopyOnWriteArrayList 是**写时复制**：写加锁复制整个数组，读无锁走旧数组快照。适合读多写极少、能容忍读到旧数据的场景，比如路由规则、监听器列表。频繁写或数组很大时复制开销高，不要用。"

---

## Q9: PriorityQueue / Deque / ArrayDeque 底层？

| 集合 | 底层 | 特点 | 典型用途 |
|------|------|------|----------|
| PriorityQueue | Object[] 堆（小顶堆） | 无界、非线程安全、无 null | 任务调度、TopK |
| Deque | 接口 | 双端队列抽象 | 栈/队列统一 API |
| ArrayDeque | 循环数组 | 双端 O(1) 坞摊，比 LinkedList 快 | 代替 Stack / LinkedList 作队列 |
| LinkedList | 双向链表 | 也实现 Deque | 兼容旧代码 |

### PriorityQueue 要点

- 默认小顶堆：`siftUp` / `siftDown` 维护堆序
- 不保证遍历有序，**只有 `poll()` 顺序出队才有序**
- 构造时可传 Comparator 定制排序
- 扩容：旧数组长度 < 64 时翻倍，否则 1.5 倍

### ArrayDeque 要点

- 循环数组，`head` / `tail` 指针，扩容 2 的幂
- **不允许 null**（避免与「队列空」歧义）
- 作栈用 `push/pop`，作队列用 `addLast/pollFirst`
- JDK 官方推荐替代 `Stack`（Stack 继承 Vector，方法全加锁）

### 面试答法

> "PriorityQueue 是数组实现的**二叉堆**，出队有序、遍历无序，适合 TopK。ArrayDeque 是循环数组双端队列，性能优于 LinkedList，也是官方推荐的 Stack 替代品。队列/栈场景优先 ArrayDeque，需要出堆排序才用 PriorityQueue。"

---

## Q10: 集合遍历时删除元素的正确姿势？fail-fast 源码？

### 三种正确姿势

```java
List<String> list = new ArrayList<>(List.of("a", "b", "c"));

// 1. Iterator.remove（推荐）
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if ("b".equals(it.next())) {
        it.remove(); // 同步 modCount，不会 CME
    }
}

// 2. JDK8+ removeIf
list.removeIf("b"::equals);

// 3. 先收集再删除
list.removeAll(Collections.singleton("b"));
```

### fail-fast 源码机制

```java
// ArrayList.Itr#checkForComodification
final void checkForComodification() {
    if (modCount != expectedModCount)
        throw new ConcurrentModificationException();
}

// iterator() 创建 Itr 时快照
int expectedModCount = modCount;

// 集合自身的 add/remove 会 ++modCount
// 直接调 list.remove() 导致 modCount != expectedModCount
// 下次 next() 时抛出 CME
```

| 方式 | 是否安全 | 原因 |
|------|----------|------|
| `list.remove()` | ❌ | 改的是集合 modCount，迭代器不知情 |
| `it.remove()` | ✅ | 迭代器同步更新 expectedModCount |
| `removeIf` | ✅ | 内部统一走迭代器删除 |
| fori + remove(i) | ⚠️ | 不抛 CME，但索引偏移会漏元素 |

### 面试答法

> "遍历时删除要用 **Iterator.remove() 或 removeIf**，不能直接 list.remove()。fail-fast 依赖 modCount：创建迭代器时记录 expectedModCount，每次 next 检查是否被外部修改，不一致就抛 CME。fori 删除不抛异常但会漏元素，也不安全。"

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

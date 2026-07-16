# 二叉树

## Q1: 什么是二叉树？有哪些类型？

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          二叉树基本类型                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  满二叉树 (Full)              完全二叉树 (Complete)         平衡二叉树 (AVL)  │
│                                                                             │
│        1                           1                           1           │
│       / \                         / \                         / \           │
│      2   3                       2   3                       2   3          │
│     / \ / \                     / \ /                       / \ /           │
│    4  5 6  7                   4  5 6                      4  5 6           │
│                                                                             │
│  每层都满                   除最后一层外都满，             左右子树高度差      │
│  叶子在同一层               且最后一层左对齐               ≤ 1               │
│                                                                             │
│  二叉搜索树 (BST)                                                      堆   │
│                                                                             │
│        5                                                          最大堆:   │
│       / \                                                            9      │
│      3   7                                                          / \     │
│     / \ / \                                                        7   8    │
│    2  4 6  8                                                      / \ / \   │
│                                                                  3  6 4  5  │
│  左 < 根 < 右                                                   父 ≥ 子     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 节点定义

```java
public class TreeNode {
    int val;
    TreeNode left;
    TreeNode right;

    TreeNode(int val) {
        this.val = val;
    }
}
```

### 基本性质

| 性质 | 公式 |
|------|------|
| 第 i 层最多节点数 | 2^(i-1) |
| 深度为 k 的树最多节点 | 2^k - 1 |
| 叶子节点数 n₀ | n₀ = n₂ + 1 (n₂为度为2的节点) |
| 完全二叉树父节点 | parent = (i-1) / 2 |
| 完全二叉树左孩子 | left = 2i + 1 |
| 完全二叉树右孩子 | right = 2i + 2 |

---

## Q2: 二叉树的遍历方式？

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          四种遍历方式                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│         1                                                                   │
│        / \                                                                  │
│       2   3                                                                 │
│      / \                                                                    │
│     4   5                                                                   │
│                                                                             │
│  前序 (Pre-order):  根 → 左 → 右    1, 2, 4, 5, 3                          │
│  中序 (In-order):   左 → 根 → 右    4, 2, 5, 1, 3                          │
│  后序 (Post-order): 左 → 右 → 根    4, 5, 2, 3, 1                          │
│  层序 (Level-order): 逐层从左到右    1, 2, 3, 4, 5                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 递归实现

```java
// 前序遍历
public void preorder(TreeNode root) {
    if (root == null) return;
    System.out.print(root.val + " ");  // 访问根
    preorder(root.left);                // 遍历左子树
    preorder(root.right);               // 遍历右子树
}

// 中序遍历
public void inorder(TreeNode root) {
    if (root == null) return;
    inorder(root.left);
    System.out.print(root.val + " ");
    inorder(root.right);
}

// 后序遍历
public void postorder(TreeNode root) {
    if (root == null) return;
    postorder(root.left);
    postorder(root.right);
    System.out.print(root.val + " ");
}
```

### 迭代实现 (使用栈)

```java
// 前序遍历 - 迭代
public List<Integer> preorderTraversal(TreeNode root) {
    List<Integer> result = new ArrayList<>();
    if (root == null) return result;

    Deque<TreeNode> stack = new ArrayDeque<>();
    stack.push(root);

    while (!stack.isEmpty()) {
        TreeNode node = stack.pop();
        result.add(node.val);

        // 先右后左入栈，这样左子节点先出栈
        if (node.right != null) stack.push(node.right);
        if (node.left != null) stack.push(node.left);
    }
    return result;
}

// 中序遍历 - 迭代
public List<Integer> inorderTraversal(TreeNode root) {
    List<Integer> result = new ArrayList<>();
    Deque<TreeNode> stack = new ArrayDeque<>();
    TreeNode curr = root;

    while (curr != null || !stack.isEmpty()) {
        // 一直向左走到底
        while (curr != null) {
            stack.push(curr);
            curr = curr.left;
        }
        curr = stack.pop();
        result.add(curr.val);
        curr = curr.right;
    }
    return result;
}
```

### 层序遍历 (BFS)

```java
public List<List<Integer>> levelOrder(TreeNode root) {
    List<List<Integer>> result = new ArrayList<>();
    if (root == null) return result;

    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root);

    while (!queue.isEmpty()) {
        int size = queue.size();
        List<Integer> level = new ArrayList<>();

        for (int i = 0; i < size; i++) {
            TreeNode node = queue.poll();
            level.add(node.val);

            if (node.left != null) queue.offer(node.left);
            if (node.right != null) queue.offer(node.right);
        }
        result.add(level);
    }
    return result;
}
```

### 面试关键点

- **前序**：常用于序列化、复制树
- **中序**：BST 中序遍历是有序数组
- **后序**：常用于计算树的高度、释放资源
- **层序**：按层处理、求树的宽度

---

## Q3: 如何求二叉树的高度/深度？

```java
// 递归 - 后序思想
public int maxDepth(TreeNode root) {
    if (root == null) return 0;
    int left = maxDepth(root.left);
    int right = maxDepth(root.right);
    return Math.max(left, right) + 1;
}

// 迭代 - 层序遍历
public int maxDepthBFS(TreeNode root) {
    if (root == null) return 0;

    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root);
    int depth = 0;

    while (!queue.isEmpty()) {
        int size = queue.size();
        depth++;
        for (int i = 0; i < size; i++) {
            TreeNode node = queue.poll();
            if (node.left != null) queue.offer(node.left);
            if (node.right != null) queue.offer(node.right);
        }
    }
    return depth;
}
```

---

## Q4: 如何判断平衡二叉树？

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          平衡二叉树判断                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│     平衡                不平衡                                                │
│       1                   1                                                 │
│      / \                 /                                                  │
│     2   3               2                                                   │
│    / \                 /                                                    │
│   4   5               4                                                     │
│                      /                                                      │
│                     5  高度差 > 1                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```java
// 方法一：自底向上 (推荐，O(n))
public boolean isBalanced(TreeNode root) {
    return height(root) != -1;
}

private int height(TreeNode node) {
    if (node == null) return 0;

    int left = height(node.left);
    if (left == -1) return -1;  // 左子树不平衡

    int right = height(node.right);
    if (right == -1) return -1; // 右子树不平衡

    if (Math.abs(left - right) > 1) return -1; // 当前节点不平衡

    return Math.max(left, right) + 1;
}
```

---

## Q5: 二叉搜索树 (BST) 的操作？

### 查找

```java
public TreeNode searchBST(TreeNode root, int val) {
    if (root == null || root.val == val) return root;

    if (val < root.val) return searchBST(root.left, val);
    return searchBST(root.right, val);
}
```

### 插入

```java
public TreeNode insertIntoBST(TreeNode root, int val) {
    if (root == null) return new TreeNode(val);

    if (val < root.val) {
        root.left = insertIntoBST(root.left, val);
    } else {
        root.right = insertIntoBST(root.right, val);
    }
    return root;
}
```

### 删除 (最复杂)

```java
public TreeNode deleteNode(TreeNode root, int key) {
    if (root == null) return null;

    if (key < root.val) {
        root.left = deleteNode(root.left, key);
    } else if (key > root.val) {
        root.right = deleteNode(root.right, key);
    } else {
        // 找到要删除的节点
        // 情况1: 叶子节点或只有一个子节点
        if (root.left == null) return root.right;
        if (root.right == null) return root.left;

        // 情况2: 有两个子节点
        // 找右子树的最小节点（后继）
        TreeNode successor = findMin(root.right);
        root.val = successor.val;
        root.right = deleteNode(root.right, successor.val);
    }
    return root;
}

private TreeNode findMin(TreeNode node) {
    while (node.left != null) {
        node = node.left;
    }
    return node;
}
```

---

## Q6: 如何判断对称二叉树？

```
     对称                   不对称
       1                      1
      / \                    / \
     2   2                  2   2
    / \ / \                    / \
   3  4 4  3                  3   3
```

```java
// 递归
public boolean isSymmetric(TreeNode root) {
    if (root == null) return true;
    return isMirror(root.left, root.right);
}

private boolean isMirror(TreeNode left, TreeNode right) {
    if (left == null && right == null) return true;
    if (left == null || right == null) return false;

    return left.val == right.val
        && isMirror(left.left, right.right)
        && isMirror(left.right, right.left);
}

// 迭代
public boolean isSymmetricIterative(TreeNode root) {
    if (root == null) return true;

    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root.left);
    queue.offer(root.right);

    while (!queue.isEmpty()) {
        TreeNode left = queue.poll();
        TreeNode right = queue.poll();

        if (left == null && right == null) continue;
        if (left == null || right == null) return false;
        if (left.val != right.val) return false;

        queue.offer(left.left);
        queue.offer(right.right);
        queue.offer(left.right);
        queue.offer(right.left);
    }
    return true;
}
```

---

## Q7: 最近公共祖先 (LCA)

```
         3
        / \
       5   1
      / \ / \
     6  2 0  8
       / \
      7   4

LCA(5, 1) = 3
LCA(5, 4) = 5
```

```java
// BST 的最近公共祖先
public TreeNode lowestCommonAncestorBST(TreeNode root, TreeNode p, TreeNode q) {
    if (root == null) return null;

    if (p.val < root.val && q.val < root.val) {
        return lowestCommonAncestorBST(root.left, p, q);
    }
    if (p.val > root.val && q.val > root.val) {
        return lowestCommonAncestorBST(root.right, p, q);
    }
    return root; // p 和 q 在两侧，当前节点就是 LCA
}

// 普通二叉树的最近公共祖先
public TreeNode lowestCommonAncestor(TreeNode root, TreeNode p, TreeNode q) {
    if (root == null || root == p || root == q) return root;

    TreeNode left = lowestCommonAncestor(root.left, p, q);
    TreeNode right = lowestCommonAncestor(root.right, p, q);

    if (left != null && right != null) return root; // p, q 分布在两侧
    return left != null ? left : right;
}
```

---

## Q8: 二叉树的序列化与反序列化

```java
public class Codec {

    // 前序遍历序列化
    public String serialize(TreeNode root) {
        StringBuilder sb = new StringBuilder();
        serializeHelper(root, sb);
        return sb.toString();
    }

    private void serializeHelper(TreeNode node, StringBuilder sb) {
        if (node == null) {
            sb.append("null,");
            return;
        }
        sb.append(node.val).append(",");
        serializeHelper(node.left, sb);
        serializeHelper(node.right, sb);
    }

    // 反序列化
    public TreeNode deserialize(String data) {
        String[] tokens = data.split(",");
        Queue<String> queue = new LinkedList<>(Arrays.asList(tokens));
        return deserializeHelper(queue);
    }

    private TreeNode deserializeHelper(Queue<String> queue) {
        String val = queue.poll();
        if ("null".equals(val)) return null;

        TreeNode node = new TreeNode(Integer.parseInt(val));
        node.left = deserializeHelper(queue);
        node.right = deserializeHelper(queue);
        return node;
    }
}
```

---

## Q9: 二叉树的常见应用场景

| 场景 | 数据结构 | 说明 |
|------|----------|------|
| 文件系统 | 多叉树 | 目录和文件的层级结构 |
| DOM 树 | 多叉树 | HTML 文档结构 |
| 数据库索引 | B+ 树 | MySQL InnoDB 引擎 |
| 堆排序 | 完全二叉树 | 优先队列、Top K 问题 |
| 表达式树 | 二叉树 | 编译器语法分析 |
| 哈夫曼编码 | 哈夫曼树 | 数据压缩 |
| 决策树 | 二叉树/多叉树 | 机器学习分类 |
| 红黑树 | 自平衡 BST | Java TreeMap/HashMap |
| 字典树 (Trie) | 多叉树 | 自动补全、拼写检查 |
| 线段树 | 二叉树 | 区间查询问题 |

### 实际应用示例

#### 1. 表达式求值

```
表达式: (3 + 5) * 2

表达式树:
        *
       / \
      +   2
     / \
    3   5

前序遍历: * + 3 5 2  (前缀表达式)
中序遍历: 3 + 5 * 2  (中缀表达式)
后序遍历: 3 5 + 2 *  (后缀表达式/逆波兰)
```

#### 2. 堆 - 优先队列

```java
// Java 内置优先队列 (最小堆)
PriorityQueue<Integer> minHeap = new PriorityQueue<>();

// 最大堆
PriorityQueue<Integer> maxHeap = new PriorityQueue<>(Collections.reverseOrder());

// Top K 问题示例
public int findKthLargest(int[] nums, int k) {
    PriorityQueue<Integer> minHeap = new PriorityQueue<>();
    for (int num : nums) {
        minHeap.offer(num);
        if (minHeap.size() > k) {
            minHeap.poll(); // 移除最小的
        }
    }
    return minHeap.peek(); // 堆顶就是第 K 大
}
```

#### 3. BST 在 Java 中的应用

```java
// TreeMap 底层是红黑树 (自平衡 BST)
TreeMap<Integer, String> map = new TreeMap<>();
map.put(3, "three");
map.put(1, "one");
map.put(4, "four");

// 有序遍历
for (Map.Entry<Integer, String> entry : map.entrySet()) {
    System.out.println(entry.getKey() + ": " + entry.getValue());
}
// 输出: 1, 3, 4 (有序)

// 快速查找范围
SortedMap<Integer, String> sub = map.subMap(1, 4); // [1, 4)
```

---

## Q10: 面试高频变体题

### 1. 路径总和

```java
// 判断是否存在根到叶子路径和等于 target
public boolean hasPathSum(TreeNode root, int targetSum) {
    if (root == null) return false;

    // 叶子节点
    if (root.left == null && root.right == null) {
        return root.val == targetSum;
    }

    return hasPathSum(root.left, targetSum - root.val)
        || hasPathSum(root.right, targetSum - root.val);
}
```

### 2. 翻转二叉树

```java
public TreeNode invertTree(TreeNode root) {
    if (root == null) return null;

    TreeNode left = invertTree(root.left);
    TreeNode right = invertTree(root.right);

    root.left = right;
    root.right = left;
    return root;
}
```

### 3. 二叉树展开为链表 (前序)

```java
// 原地展开，right 指针当 next
public void flatten(TreeNode root) {
    if (root == null) return;

    flatten(root.left);
    flatten(root.right);

    TreeNode right = root.right;
    root.right = root.left;
    root.left = null;

    // 找到新的右子树的末尾
    TreeNode curr = root;
    while (curr.right != null) {
        curr = curr.right;
    }
    curr.right = right;
}
```

### 4. 从中序与后序遍历构造二叉树

```java
public TreeNode buildTree(int[] inorder, int[] postorder) {
    Map<Integer, Integer> inMap = new HashMap<>();
    for (int i = 0; i < inorder.length; i++) {
        inMap.put(inorder[i], i);
    }
    return build(inorder, 0, inorder.length - 1,
                 postorder, 0, postorder.length - 1, inMap);
}

private TreeNode build(int[] in, int inStart, int inEnd,
                       int[] post, int postStart, int postEnd,
                       Map<Integer, Integer> inMap) {
    if (inStart > inEnd || postStart > postEnd) return null;

    TreeNode root = new TreeNode(post[postEnd]);
    int rootIndex = inMap.get(root.val);
    int leftSize = rootIndex - inStart;

    root.left = build(in, inStart, rootIndex - 1,
                      post, postStart, postStart + leftSize - 1, inMap);
    root.right = build(in, rootIndex + 1, inEnd,
                       post, postStart + leftSize, postEnd - 1, inMap);
    return root;
}
```

---

## 面试答法总结

> "二叉树的核心是递归思想。大多数二叉树问题都可以分解为：处理当前节点 + 递归处理左右子树。遍历方式的选择取决于问题类型：
> - 需要在处理子树前操作 → 前序
> - 需要利用子树结果 → 后序
> - BST 需要有序 → 中序
> - 按层处理 → BFS"

### 时间复杂度速查

| 操作 | BST (平均) | BST (最坏) | 平衡树 |
|------|-----------|-----------|--------|
| 查找 | O(log n) | O(n) | O(log n) |
| 插入 | O(log n) | O(n) | O(log n) |
| 删除 | O(log n) | O(n) | O(log n) |
| 遍历 | O(n) | O(n) | O(n) |

**注意**：BST 最坏情况退化为链表，所以需要自平衡树 (AVL、红黑树)。

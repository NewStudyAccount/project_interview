# MyBatis

## Q1: #{} 和 ${} 的区别？

| 维度 | #{} | ${} |
|------|-----|-----|
| 底层实现 | PreparedStatement | Statement |
| SQL 注入 | ✅ 安全 (参数化) | ❌ 不安全 (字符串拼接) |
| 使用场景 | 参数传递 | 表名、列名、ORDER BY |
| 性能 | 可预编译缓存 | 每次重新编译 |

```java
// #{} 安全 (推荐)
@Select("SELECT * FROM user WHERE id = #{id}")
User selectById(@Param("id") Long id);
// 实际执行: SELECT * FROM user WHERE id = ?

// ${} 不安全 (仅用于动态表名/列名)
@Select("SELECT * FROM ${tableName} WHERE id = #{id}")
User selectFromTable(@Param("tableName") String tableName,
                     @Param("id") Long id);
// 实际执行: SELECT * FROM user WHERE id = ?
```

---

## Q2: MyBatis 一级缓存和二级缓存？

```
┌──────────────────────────────────────────────────────────┐
│                  MyBatis 缓存机制                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  一级缓存 (SqlSession 级别):                             │
│  ├── 默认开启                                            │
│  ├── 同一个 SqlSession 内有效                            │
│  ├── 执行 update/insert/delete 后自动清空               │
│  └── Spring 集成后，每次请求通常新建 SqlSession          │
│      → 一级缓存基本无效                                  │
│                                                          │
│  二级缓存 (Mapper 级别):                                 │
│  ├── 需手动开启: <cache/> 或 @CacheNamespace            │
│  ├── 同一个 Mapper 下的所有 SqlSession 共享              │
│  ├── SqlSession 关闭/提交后才写入二级缓存               │
│  └── 问题:                                            │
│      ├── 多表关联查询时，一个表更新不会清空其他表缓存   │
│      └── 分布式环境下不一致                             │
│                                                          │
│  生产建议: 关闭二级缓存，用 Redis 做缓存层               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 开启二级缓存

```xml
<!-- Mapper.xml -->
<cache
    eviction="LRU"
    flushInterval="60000"
    size="512"
    readOnly="true"/>
```

```java
// 注解方式
@CacheNamespace(eviction = LruCache.class, flushInterval = 60000)
public interface UserMapper {
    // ...
}
```

---

## Q3: MyBatis 动态 SQL？

| 标签 | 作用 |
|------|------|
| `<if>` | 条件判断 |
| `<choose>/<when>/<otherwise>` | 多条件分支 (类似 switch) |
| `<where>` | 自动处理 WHERE 和 AND/OR |
| `<set>` | 自动处理 SET 和逗号 |
| `<trim>` | 自定义前缀/后缀 |
| `<foreach>` | 遍历集合 |
| `<sql>/<include>` | SQL 片段复用 |

### 示例

```xml
<select id="findUsers" resultType="User">
    SELECT * FROM user
    <where>
        <if test="name != null and name != ''">
            AND name LIKE CONCAT('%', #{name}, '%')
        </if>
        <if test="status != null">
            AND status = #{status}
        </if>
        <if test="ids != null and ids.size() > 0">
            AND id IN
            <foreach collection="ids" item="id" open="(" separator="," close=")">
                #{id}
            </foreach>
        </if>
    </where>
    <choose>
        <when test="orderBy == 'name'">
            ORDER BY name ASC
        </when>
        <when test="orderBy == 'createTime'">
            ORDER BY create_time DESC
        </when>
        <otherwise>
            ORDER BY id DESC
        </otherwise>
    </choose>
</select>
```

---

## Q4: MyBatis 插件机制（Interceptor）？

```
┌──────────────────────────────────────────────────────────┐
│              MyBatis 插件执行流程                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  MyBatis 四大对象:                                       │
│  ├── Executor          (执行器)                          │
│  ├── StatementHandler  (语句处理器)                      │
│  ├── ParameterHandler  (参数处理器)                      │
│  └── ResultSetHandler  (结果集处理器)                    │
│                                                          │
│  插件原理: 责任链模式 + 动态代理                         │
│                                                          │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐               │
│  │Plugin3  │──▶│Plugin2  │──▶│Plugin1  │──▶ 原始对象    │
│  │(代理)   │   │(代理)   │   │(代理)   │               │
│  └─────────┘   └─────────┘   └─────────┘               │
│                                                          │
│  自定义插件:                                             │
│  @Intercepts({                                          │
│      @Signature(                                         │
│          type = StatementHandler.class,                  │
│          method = "prepare",                             │
│          args = {Connection.class, Integer.class}        │
│      )                                                   │
│  })                                                      │
│  public class MyPlugin implements Interceptor {          │
│      @Override                                           │
│      public Object intercept(Invocation invocation)      │
│          throws Throwable {                              │
│          // 前置处理                                     │
│          Object result = invocation.proceed();           │
│          // 后置处理                                     │
│          return result;                                  │
│      }                                                   │
│  }                                                      │
│                                                          │
│  典型应用: PageHelper 分页插件                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q5: MyBatis 执行流程？

```
┌──────────────────────────────────────────────────────────┐
│              MyBatis 执行流程                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 加载配置文件 (mybatis-config.xml + Mapper.xml)       │
│     └── 解析为 Configuration 对象                        │
│                                                          │
│  2. 创建 SqlSessionFactory                               │
│     └── DefaultSqlSessionFactory                        │
│                                                          │
│  3. 获取 SqlSession                                      │
│     └── DefaultSqlSession                               │
│                                                          │
│  4. 获取 Mapper 代理对象                                 │
│     └── MapperProxyFactory 创建 JDK 动态代理             │
│                                                          │
│  5. 调用 Mapper 方法                                     │
│     └── MapperProxy.invoke()                            │
│         └── MapperMethod.execute()                      │
│                                                          │
│  6. 执行 SQL                                             │
│     └── Executor (Simple/Reuse/Batch)                   │
│         └── StatementHandler                            │
│             ├── PreparedStatementHandler (预编译)        │
│             └── SimpleStatementHandler (直接执行)        │
│                                                          │
│  7. 参数处理                                             │
│     └── ParameterHandler.setParameters()                │
│                                                          │
│  8. 结果集映射                                           │
│     └── ResultSetHandler.handleResultSets()             │
│         └── 反射创建对象, 设置属性                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

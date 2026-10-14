# 权限系统设计

## 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                    权限系统架构                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────┐     ┌─────────────────────────────────────┐    │
│  │ 前端  │────▶│ 网关 / 过滤器链                     │    │
│  │ 菜单  │     │ 认证(Authentication)                │    │
│  │ 按钮  │     │ 鉴权(Authorization)                 │    │
│  └──────┘     └──────────────┬──────────────────────┘    │
│                              │                           │
│                              ▼                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │                权限中心服务                       │    │
│  │  ├── 用户中心 (User)                             │    │
│  │  ├── 角色中心 (Role)                             │    │
│  │  ├── 资源中心 (Menu / API / Button)              │    │
│  │  ├── 规则引擎 (数据权限 / 表达式)                │    │
│  │  └── 会话中心 (JWT / Redis Token)                │    │
│  └──────────────────────┬───────────────────────────┘    │
│                         │                                │
│           ┌─────────────┼─────────────┐                  │
│           ▼             ▼             ▼                  │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│     │  Redis   │  │  MySQL   │  │ 业务服务  │             │
│     │  Token   │  │  权限表  │  │ 注解鉴权  │             │
│     │  权限缓存│  │  用户表  │  │ 数据过滤  │             │
│     └──────────┘  └──────────┘  └──────────┘             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q1: RBAC 权限模型？RBAC0/1/2？（高频）

### 核心思想

RBAC（Role-Based Access Control）：用户不直接绑权限，而是通过**角色**间接获得权限。

```
用户 (User) ──N:M──▶ 角色 (Role) ──N:M──▶ 权限 (Permission)
```

### RBAC 分级对比

| 级别 | 名称 | 能力 | 适用 |
|------|------|------|------|
| RBAC0 | 基础模型 | 用户-角色-权限，最简 | 小系统 |
| RBAC1 | 角色分层 | 角色继承（上级角色含下级权限） | 有职级的组织 |
| RBAC2 | 约束模型 | 职责分离、角色互斥、基数约束 | 金融/合规场景 |
| RBAC3 | 统一模型 | RBAC1 + RBAC2 | 复杂企业系统 |

### 常见约束（RBAC2）

- **互斥角色**：出纳与会计不能是同一人
- **角色上限**：一人最多兼任 N 个角色
- **先决条件**：必须先有「实习编辑」才能授「正式编辑」
- **静态/动态职责分离**：激活会话时互斥 / 授权时互斥

### 面试答法

> "RBAC 核心是**用户-角色-权限**三层解耦，用户通过角色拿到权限，避免人和权限直接绑定爆炸。RBAC0 最基础；RBAC1 加角色继承，适合职级；RBAC2 加互斥、基数等约束，适合金融合规。绝大多数后台系统 RBAC0/1 就够了，权限缓存进 Redis 即可。"

---

## Q2: 权限系统表结构怎么设计？

### 表结构（SQL）

```sql
-- 用户表
CREATE TABLE sys_user (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    username    VARCHAR(64)  NOT NULL COMMENT '登录名',
    password    VARCHAR(128) NOT NULL COMMENT '密码(BCrypt)',
    nickname    VARCHAR(64)  DEFAULT NULL,
    dept_id     BIGINT       DEFAULT NULL COMMENT '部门(数据权限用)',
    tenant_id   BIGINT       NOT NULL DEFAULT 0 COMMENT '租户ID',
    status      TINYINT      NOT NULL DEFAULT 1 COMMENT '1正常 0禁用',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_username_tenant (username, tenant_id)
) COMMENT '用户表';

-- 角色表
CREATE TABLE sys_role (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_code   VARCHAR(64)  NOT NULL COMMENT '角色编码 ROLE_ADMIN',
    role_name   VARCHAR(64)  NOT NULL COMMENT '角色名称',
    parent_id   BIGINT       DEFAULT 0  COMMENT '上级角色(RBAC1继承)',
    data_scope  TINYINT      DEFAULT 1  COMMENT '数据权限范围 1全部 2本部门 3本部门及以下 4仅本人 5自定义',
    tenant_id   BIGINT       NOT NULL DEFAULT 0,
    status      TINYINT      NOT NULL DEFAULT 1,
    UNIQUE KEY uk_role_code_tenant (role_code, tenant_id)
) COMMENT '角色表';

-- 权限/资源表
CREATE TABLE sys_permission (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    parent_id   BIGINT       DEFAULT 0,
    perm_type   TINYINT      NOT NULL COMMENT '1菜单 2按钮 3接口',
    perm_code   VARCHAR(128) NOT NULL COMMENT 'sys:user:add / GET /api/user',
    perm_name   VARCHAR(64)  NOT NULL,
    path        VARCHAR(256) DEFAULT NULL COMMENT '路由或API路径',
    method      VARCHAR(16)  DEFAULT NULL COMMENT 'GET/POST/PUT/DELETE',
    sort_order  INT          DEFAULT 0,
    status      TINYINT      NOT NULL DEFAULT 1,
    UNIQUE KEY uk_perm_code (perm_code)
) COMMENT '权限资源表';

-- 用户-角色
CREATE TABLE sys_user_role (
    id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    UNIQUE KEY uk_user_role (user_id, role_id)
) COMMENT '用户角色关联';

-- 角色-权限
CREATE TABLE sys_role_permission (
    id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id BIGINT NOT NULL,
    perm_id BIGINT NOT NULL,
    UNIQUE KEY uk_role_perm (role_id, perm_id)
) COMMENT '角色权限关联';

-- 数据权限规则（行级，可选）
CREATE TABLE sys_role_data_scope (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id      BIGINT NOT NULL,
    dept_id      BIGINT NOT NULL COMMENT '可见部门',
    UNIQUE KEY uk_role_dept (role_id, dept_id)
) COMMENT '角色自定义数据范围';
```

### 设计要点

| 要点 | 说明 |
|------|------|
| 多租户 | 每张权限相关表带 `tenant_id`，逻辑隔离 |
| 角色编码 | 用 `ROLE_XXX` / `sys:user:add` 风格，便于 SpEL/注解 |
| 资源粒度 | 菜单、按钮、API 统一一张表用 `perm_type` 区分 |
| 关联表 | 用户↔角色、角色↔权限均多对多，单独建表 |
| 数据范围 | 放在角色上（`data_scope`），比放用户上更易维护 |

---

## Q3: Spring Security / Shiro / JWT 如何落地鉴权？（高频）

### 框架对比

| 维度 | Spring Security | Shiro | JWT |
|------|-----------------|-------|-----|
| 与 Spring 融合 | 原生，过滤器链完整 | 轻量，需手动集成 | 无状态令牌，本身不是框架 |
| 学习成本 | 高 | 低 | 中 |
| 会话 | 默认 Session，可改无状态 | Session / 自定义 | 无状态 |
| 分布式 | Session + Redis 或 JWT | 需自行扩展 | 天然适合 |
| 适用 | Spring Boot 全家桶 | 轻量/非 Spring 项目 | 微服务、前后端分离 |

### JWT 落地流程

```
┌──────────────────────────────────────────────────────────┐
│                 JWT 鉴权流程                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  登录:                                                   │
│  用户名密码 ──▶ 认证服务 ──▶ 签发 JWT                    │
│                              (header.payload.signature)  │
│                              payload: userId, roles, exp │
│                                                          │
│  请求:                                                   │
│  携带 Authorization: Bearer <token>                      │
│      │                                                   │
│      ▼                                                   │
│  网关 / Filter:                                          │
│  1. 校验签名与过期时间                                   │
│  2. 解析出用户、角色、权限                               │
│  3. 放入 SecurityContext / ThreadLocal                   │
│  4. 注解鉴权 @PreAuthorize("hasRole('ADMIN')")           │
│                                                          │
│  登出:                                                   │
│  ├── 短 token: Redis 黑名单 / 版本号                     │
│  └── 长 token: 签发 refresh token 定期轮换               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Spring Security 关键配置片段

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity   // 开启 @PreAuthorize
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/auth/login", "/auth/refresh").permitAll()
                .anyRequest().authenticated())
            .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}

// 方法级鉴权
@PreAuthorize("hasAuthority('sys:user:delete')")
public void deleteUser(Long id) { ... }
```

### 面试答法

> "前后端分离 + 微服务选 **JWT 无状态**：登录签发 token，网关统一校验，服务内用 `@PreAuthorize` 做接口鉴权。Spring Security 负责过滤器链和方法安全，Shiro 适合轻量项目。JWT 吊销难，所以要用 Redis 黑名单或短 token + refresh token；权限变更时重建 SecurityContext。"

---

## Q4: 前端按钮级权限如何控制？

### 方案对比

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| 菜单树下发 | 登录后返回有权限的菜单/按钮 | 简单直观 | 按钮隐藏不等于后端安全 |
| 权限码指令 | `v-if="has('sys:user:add')"` | 灵活 | 需维护权限码 |
| 自定义指令 | `v-permission="'sys:user:add'"` | 侵入小 | 仅显示控制 |
| 路由守卫 | 动态路由 + 未授权跳 404 | 防误入页面 | 仍需后端校验 |

```vue
<!-- Vue 按钮级权限示例 -->
<a-button v-if="hasPerm('sys:user:add')" @click="onAdd">新增</a-button>

<script setup>
const perms = usePerms() // 登录后缓存的权限码集合
const hasPerm = (code) => perms.value.includes(code)
</script>
```

```java
// 后端接口仍必须校验（防绕过前端）
@PreAuthorize("hasAuthority('sys:user:add')")
@PostMapping("/user")
public Result add(@RequestBody UserDTO dto) { ... }
```

### 面试关键点

- **前端控制只是体验，后端必须再次鉴权**（防抓包、防直接调 API）
- 权限码与后端 `@PreAuthorize` 使用同一套编码（如 `sys:user:add`）
- 权限变更后刷新缓存 / 重新拉取菜单，必要时强制重新登录

### 面试答法

> "按钮级权限用**权限码**控制：登录后拉取 `sys:user:add` 这类权限码集合，用 `v-if` 或自定义指令隐藏按钮。但隐藏不等于安全，所有写接口在后端还要 `hasAuthority` 校验，前后端共用同一套权限码。"

---

## Q5: 数据权限（行级）怎么做？

### 问题本质

功能权限决定「能不能点」，数据权限决定「能看到哪些行」。

```
┌──────────────────────────────────────────────────────────┐
│                   数据权限范围                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  全部数据      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  超级管理员         │
│  本部门及以下  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░  部门经理           │
│  本部门        ▓▓▓▓░░░░░░░░░░░░░░░░  部门成员           │
│  仅本人        ▓░░░░░░░░░░░░░░░░░░░  普通员工           │
│  自定义        ▓▓░░▓▓░░░░▓▓░░░░░░░░  指定部门/人        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 常见实现

| 方案 | 思路 | 适用 |
|------|------|------|
| SQL 拼接 | MyBatis 拦截器追加 `dept_id IN (...)` | 单体、通用 |
| 注解 + AOP | `@DataScope(deptAlias="d")` 自动拼条件 | Spring 项目 |
| 行级安全 | MySQL 8 / PostgreSQL RLS | 数据库层兜底 |
| 冗余字段 | 订单冗余 `dept_id` / `owner_id` | 分库分表后 |
| ES / 索引 | 查询时带 filter | 搜索场景 |

```java
// MyBatis 拦截器伪代码：根据 data_scope 改写 SQL
// data_scope=2 (本部门) → AND dept_id = #{currentDeptId}
// data_scope=3 (本部门及以下) → AND dept_id IN (递归子部门)
// data_scope=4 (仅本人) → AND owner_id = #{currentUserId}
```

### 面试答法

> "数据权限在角色上定义范围（全部/本部门/本部门及以下/仅本人/自定义），查询时用 **MyBatis 拦截器或 AOP 注解** 把条件拼进 SQL。字段上要有 `dept_id`、`owner_id` 可过滤列；分库分表后靠冗余字段。敏感接口再叠加审计日志。"

---

## Q6: 多租户权限如何设计？

### 多租户模型

| 模式 | 隔离方式 | 优点 | 缺点 |
|------|----------|------|------|
| 独立数据库 | 一租户一库 | 隔离最强、可定制 | 成本高、运维重 |
| 共享库独立 Schema | 一租户一 Schema | 较好隔离 | 连接管理复杂 |
| 共享表 + tenant_id | 行级隔离（主流） | 成本低、运维简单 | 必须处处过滤 |

### 权限侧设计要点

```
┌──────────────────────────────────────────────────────────┐
│                 多租户权限隔离                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  租户 A (tenant_id=1)                                    │
│  ├── 自有用户 / 角色 / 菜单配置                          │
│  ├── 独立管理员 (租户超管)                               │
│  └── 可选开通功能模块 (套餐)                             │
│                                                          │
│  租户 B (tenant_id=2)                                    │
│  ├── 完全隔离的用户角色树                                │
│  └── 角色编码允许重复，按 tenant_id 区分                 │
│                                                          │
│  平台层                                                   │
│  ├── 租户管理、计费、套餐                                │
│  └── 运维角色 (跨租户只读审计)                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 落地手段

- **强制 tenant_id**：拦截器/ThreadLocal 写入，SQL 自动追加 `tenant_id = ?`
- **唯一键加租户**：`UNIQUE(username, tenant_id)`，角色编码同理
- **缓存隔离**：Redis key 加租户前缀 `perm:{tenantId}:{userId}`
- **超级管理员**：平台角色可跨租户，业务角色严格单租户
- **防止横向越权**：JWT 中必须含 tenant_id，接口层校验资源归属

### 面试答法

> "多租户主流是**共享库 + tenant_id 行隔离**：所有权限表带租户字段，唯一键联合 tenant_id，SQL 层拦截器自动拼租户条件，缓存 key 加租户前缀。角色和菜单按租户自建，平台管理员单独建模。关键是防横向越权——token 必须绑定租户，服务端校验资源属于当前租户。"

---

## 表结构总览（ER 简图）

```
┌──────────┐       ┌────────────┐       ┌──────────────┐
│ sys_user │──M:N──│ sys_role   │──M:N──│sys_permission│
└────┬─────┘       └─────┬──────┘       └──────────────┘
     │                   │
     │                   ├──── data_scope (全部/部门/本人)
     │                   └──── parent_id (角色继承 RBAC1)
     │
     └── dept_id (数据权限过滤字段)
```

---

## 面试总结

### 权限系统要点

| 维度 | 方案 | 技术 |
|------|------|------|
| 模型 | RBAC 用户-角色-权限 | RBAC0/1/2 |
| 存储 | 用户/角色/权限/关联表 + tenant_id | MySQL |
| 认证 | JWT / Session + Redis | Spring Security |
| 鉴权 | 注解 + 表达式 + 网关预检 | @PreAuthorize |
| 按钮 | 权限码下发 + 前端指令 | Vue/React |
| 数据 | 范围字段 + SQL 拦截器 | MyBatis Interceptor |
| 多租户 | tenant_id 隔离 + 独立角色树 | 强制过滤 |

### 面试关键点

- **模型选型**：普通后台 RBAC0/1，有合规约束再上 RBAC2
- **安全底线**：前端隐藏 ≠ 安全，后端接口必须二次鉴权
- **性能**：权限结果缓存 Redis，变更时失效；避免每次请求查全表
- **越权**：水平越权（改 ID 看别人数据）靠归属校验，垂直越权靠权限码
- **扩展**：角色继承、数据范围、多租户可先留字段，避免后期推倒重来

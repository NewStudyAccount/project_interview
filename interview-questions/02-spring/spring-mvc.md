# Spring MVC

## Q1: Spring MVC 请求处理流程？DispatcherServlet 核心？（高频）

```
┌──────────────────────────────────────────────────────────┐
│              Spring MVC 请求处理流程                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Client                                                   │
│    │  HTTP Request                                        │
│    ▼                                                      │
│  ┌────────────────┐                                       │
│  │  Filter 链     │  编码 / 跨域 / 安全 / 日志            │
│  └───────┬────────┘                                       │
│          ▼                                                │
│  ┌────────────────┐                                       │
│  │DispatcherServlet│  前端控制器 (核心枢纽)                │
│  └───────┬────────┘                                       │
│          │                                                │
│  ① HandlerMapping ──▶ 找到 Handler (Controller 方法)      │
│          │                                                │
│  ② HandlerAdapter ──▶ 执行 Handler                        │
│          │                                                │
│  ③ 参数绑定 ──▶ HttpMessageConverter / DataBinder         │
│          │                                                │
│  ④ 业务逻辑 (Service / DAO)                               │
│          │                                                │
│  ⑤ 返回 ModelAndView / @ResponseBody                     │
│          │                                                │
│  ⑥ ViewResolver ──▶ 解析视图 (页面场景)                   │
│          │            或直接写响应 (REST 场景)             │
│          ▼                                                │
│  HTTP Response                                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### DispatcherServlet 源码核心

```java
// FrameworkServlet#doGet/doPost → processRequest
// DispatcherServlet#doDispatch 是真正的核心
protected void doDispatch(HttpServletRequest request,
                          HttpServletResponse response) throws Exception {
    // 1. 通过 HandlerMapping 找到 Handler
    mappedHandler = getHandler(processedRequest);
    // 2. 通过 HandlerAdapter 执行 Handler
    HandlerAdapter ha = getHandlerAdapter(mappedHandler.getHandler());
    // 3. 执行拦截器 preHandle
    if (!mappedHandler.applyPreHandle(processedRequest, response)) {
        return;
    }
    // 4. 真正调用 Controller 方法
    mv = ha.handle(processedRequest, response, mappedHandler.getHandler());
    // 5. 执行拦截器 postHandle
    mappedHandler.applyPostHandle(processedRequest, response, mv);
    // 6. 渲染视图 / 写响应
    processDispatchResult(processedRequest, response, mappedHandler, mv, ex);
}
```

### 面试答法

> "Spring MVC 的核心是 DispatcherServlet，它是一个前端控制器。请求进来后：先由 HandlerMapping 根据 URL 找到对应的 Handler；再由 HandlerAdapter 统一执行（因为 Controller 写法很多）；方法参数通过 HttpMessageConverter 和 DataBinder 做绑定；返回值如果是对象就序列化为 JSON，如果是 ModelAndView 就交给 ViewResolver 解析视图后渲染。整个过程还有拦截器的 preHandle / postHandle / afterCompletion 生命周期。"

---

## Q2: 核心组件有哪些？HandlerMapping / HandlerAdapter / ViewResolver

| 组件 | 作用 | 常见实现 |
|------|------|----------|
| DispatcherServlet | 前端控制器，调度整个流程 | DispatcherServlet |
| HandlerMapping | URL → Handler 映射 | RequestMappingHandlerMapping |
| HandlerAdapter | 统一调用不同写法的 Handler | RequestMappingHandlerAdapter |
| HandlerInterceptor | 请求前后拦截（AOP 切面） | 自定义 Interceptor |
| HandlerExceptionResolver | 异常解析 | ExceptionHandlerExceptionResolver |
| ViewResolver | 逻辑视图名 → 物理视图 | InternalResourceViewResolver |
| HttpMessageConverter | 报文 ↔ Java 对象互转 | Jackson / Fastjson |

### HandlerAdapter 为什么存在？

```
┌──────────────────────────────────────────────────────────┐
│                 为什么需要 HandlerAdapter                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Handler 写法有多种:                                      │
│  ├── @RequestMapping 标注的方法                           │
│  ├── 实现 Controller 接口的类                             │
│  ├── 实现 HttpRequestHandler 的类                         │
│  └── Servlet 本身也可以当 Handler                         │
│                                                          │
│  如果 DispatcherServlet 里写 if-else 判断类型再调用，     │
│  每增加一种 Handler 就要改 DispatcherServlet (违反开闭)    │
│                                                          │
│  HandlerAdapter 用适配器模式统一:                         │
│  ha.handle(...) → 无论哪种 Handler 都走同一入口            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点

> "HandlerMapping 负责找，HandlerAdapter 负责调，ViewResolver 负责渲染。HandlerAdapter 本质上是适配器模式，让 DispatcherServlet 不用关心 Handler 的具体写法。现在 REST 接口为主，ViewResolver 用得少了，但 MVC 模式里仍然是标配。"

---

## Q3: @RequestMapping / @PathVariable / @RequestParam / @RequestBody 区别？

| 注解 | 作用 | 数据来源 | 示例 |
|------|------|----------|------|
| @RequestMapping | 映射 URL 到方法 | 路径本身 | `@RequestMapping("/users")` |
| @GetMapping / @PostMapping 等 | 限定 HTTP 方法的快捷方式 | 路径 + Method | `@GetMapping("/{id}")` |
| @PathVariable | 提取 URL 路径变量 | URI 模板 | `/users/{id}` → `id` |
| @RequestParam | 提取查询参数 / 表单字段 | query / form | `?page=1` → `page` |
| @RequestBody | 提取请求体并反序列化 | request body | JSON → DTO |
| @RequestHeader | 提取请求头 | header | `Authorization` |
| @CookieValue | 提取 Cookie | cookie | `sessionId` |
| @ModelAttribute | 绑定表单对象 / 放入模型 | form / query | 传统 MVC 表单 |

### 代码示例

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    // 路径变量 + 查询参数
    @GetMapping("/{id}")
    public UserDTO get(@PathVariable("id") Long id,
                       @RequestParam(value = "detail", defaultValue = "false")
                       boolean detail) {
        return userService.get(id, detail);
    }

    // JSON 请求体
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public UserDTO create(@RequestBody @Valid UserCreateReq req) {
        return userService.create(req);
    }

    // 混合: 路径变量 + 请求体 + 请求头
    @PutMapping("/{id}")
    public UserDTO update(@PathVariable Long id,
                          @RequestBody @Valid UserUpdateReq req,
                          @RequestHeader("X-Request-Id") String traceId) {
        return userService.update(id, req, traceId);
    }
}
```

### 面试答法

> "@RequestMapping 是把 URL 映射到方法，可以限定 method、consumes、produces。@PathVariable 取路径里的变量，@RequestParam 取查询参数或表单字段，@RequestBody 把 JSON/XML 请求体反序列化成对象。注意 @RequestBody 一个方法只能有一个，@RequestParam 可以多个；表单提交用 @RequestParam 或 @ModelAttribute，JSON 提交必须用 @RequestBody。"

---

## Q4: 拦截器 Interceptor vs 过滤器 Filter 区别？（高频）

| 维度 | Filter | Interceptor |
|------|--------|-------------|
| 规范 | Servlet 规范 (javax/jakarta.servlet) | Spring MVC 规范 |
| 作用范围 | 所有请求 (含静态资源、非 Spring 管理的) | 只拦 Handler (Controller) |
| 实现方式 | 实现 Filter 接口 | 实现 HandlerInterceptor |
| 注册方式 | @WebFilter / FilterRegistrationBean | WebMvcConfigurer#addInterceptors |
| 能否拿到 Handler | ❌ | ✅ (handler 参数) |
| 能否拿到 ModelAndView | ❌ | ✅ (postHandle) |
| 执行顺序 | 先于 DispatcherServlet | DispatcherServlet 内部 |
| 典型用途 | 编码、跨域、安全、XSS | 登录校验、权限、日志、限流 |

### 执行顺序图

```
┌──────────────────────────────────────────────────────────┐
│              Filter 与 Interceptor 执行顺序                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Request                                                  │
│    │                                                      │
│    ▼                                                      │
│  Filter.doFilter (前置)          ← 编码 / CORS / 鉴权     │
│    │                                                      │
│    ▼                                                      │
│  DispatcherServlet                                       │
│    │                                                      │
│    ▼                                                      │
│  Interceptor.preHandle           ← 登录校验 / 权限        │
│    │                                                      │
│    ▼                                                      │
│  Controller 方法执行             ← 业务逻辑               │
│    │                                                      │
│    ▼                                                      │
│  Interceptor.postHandle          ← 修改 ModelAndView      │
│    │                                                      │
│    ▼                                                      │
│  视图渲染 (如果有)                                       │
│    │                                                      │
│    ▼                                                      │
│  Interceptor.afterCompletion     ← 清理资源 / 访问日志    │
│    │                                                      │
│    ▼                                                      │
│  Filter.doFilter (后置)                                  │
│    │                                                      │
│    ▼                                                      │
│  Response                                                 │
│                                                          │
│  ⚠️ preHandle 返回 false 时:                             │
│  ├── 后续 Interceptor 和 Controller 不执行                │
│  └── 已执行 preHandle 的拦截器 会触发 afterCompletion     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 代码示例

```java
// Filter: 登录 Token 解析
@Component
public class AuthFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse res,
                         FilterChain chain) throws IOException, ServletException {
        HttpServletRequest request = (HttpServletRequest) req;
        String token = request.getHeader("Authorization");
        // 解析 token 放入 request attribute，供后续使用
        chain.doFilter(req, res);  // 必须放行
    }
}

// Interceptor: 权限校验
@Component
public class PermissionInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) throws Exception {
        // 只拦 Controller 方法
        if (!(handler instanceof HandlerMethod)) {
            return true;
        }
        // 自定义注解鉴权
        HandlerMethod hm = (HandlerMethod) handler;
        if (hm.hasMethodAnnotation(RequireRole.class)) {
            // 校验角色...
        }
        return true;  // false 则中断
    }

    @Override
    public void postHandle(HttpServletRequest request,
                           HttpServletResponse response,
                           Object handler,
                           ModelAndView modelAndView) {
        // 可修改 ModelAndView
    }

    @Override
    public void afterCompletion(HttpServletRequest request,
                                HttpServletResponse response,
                                Object handler, Exception ex) {
        // 无论成功失败都会执行，类似 finally
    }
}

// 注册拦截器
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new PermissionInterceptor())
                .addPathPatterns("/api/**")
                .excludePathPatterns("/api/login", "/api/public/**");
    }
}
```

### 面试答法

> "Filter 是 Servlet 规范，作用于所有请求，拿不到 Handler 信息；Interceptor 是 Spring MVC 的，只拦 Controller，能拿到 Handler 方法和 ModelAndView。Filter 适合编码、跨域、安全这类和框架无关的事；Interceptor 适合登录校验、权限、日志这类需要感知业务方法的事。执行顺序是 Filter 先进入，DispatcherServlet 里再走 Interceptor。生产上常见组合是：Filter 做 Token 解析和 XSS，Interceptor 做细粒度权限。"

---

## Q5: 全局异常处理？@ControllerAdvice / @ExceptionHandler？

```
┌──────────────────────────────────────────────────────────┐
│                 全局异常处理机制                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Controller 抛出异常                                      │
│       │                                                  │
│       ▼                                                  │
│  HandlerExceptionResolver 依次尝试:                      │
│  ├── ExceptionHandlerExceptionResolver                  │
│  │     └─▶ @ExceptionHandler + @ControllerAdvice         │
│  ├── ResponseStatusExceptionResolver                    │
│  │     └─▶ @ResponseStatus 注解                          │
│  └── DefaultHandlerExceptionResolver                    │
│        └─▶ Spring 内置异常 (404/405/400 等)              │
│                                                          │
│  @ExceptionHandler 匹配规则:                             │
│  1. 先找当前 Controller 内的 @ExceptionHandler           │
│  2. 再找 @ControllerAdvice 中的                          │
│  3. 按异常类型最接近匹配 (类似 catch 顺序)               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 代码示例

```java
// 统一响应体
@Data
public class ApiResponse<T> {
    private int code;
    private String message;
    private T data;

    public static <T> ApiResponse<T> ok(T data) { ... }
    public static <T> ApiResponse<T> fail(int code, String msg) { ... }
}

// 全局异常处理器
@RestControllerAdvice
public class GlobalExceptionHandler {

    // 业务异常
    @ExceptionHandler(BusinessException.class)
    public ApiResponse<Void> handleBusiness(BusinessException e) {
        return ApiResponse.fail(e.getCode(), e.getMessage());
    }

    // 参数校验异常
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResponse<Void> handleValid(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(f -> f.getField() + ": " + f.getDefaultMessage())
                .collect(Collectors.joining("; "));
        return ApiResponse.fail(400, msg);
    }

    // 兜底
    @ExceptionHandler(Exception.class)
    public ApiResponse<Void> handleOther(Exception e) {
        log.error("系统异常", e);
        return ApiResponse.fail(500, "系统繁忙，请稍后重试");
    }
}
```

### 面试关键点

> "用 @RestControllerAdvice + @ExceptionHandler 做全局异常处理。匹配顺序是先本类后全局，异常类型按最接近匹配。业务异常返回业务码，参数校验异常提取 FieldError，未知异常记日志并返回通用提示，不把堆栈暴露给前端。"

---

## Q6: RESTful API 设计要点？

### URL 与方法约定

| 操作 | HTTP 方法 | URL | 状态码 |
|------|-----------|-----|--------|
| 查询列表 | GET | /api/users | 200 |
| 查询详情 | GET | /api/users/{id} | 200 |
| 创建 | POST | /api/users | 201 + Location |
| 全量更新 | PUT | /api/users/{id} | 200 |
| 局部更新 | PATCH | /api/users/{id} | 200 |
| 删除 | DELETE | /api/users/{id} | 204 |

### 设计原则

```
┌──────────────────────────────────────────────────────────┐
│                  RESTful 设计要点                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 资源用名词复数，不用动词                              │
│     ✅ GET /api/users                                    │
│     ❌ GET /api/getUsers                                  │
│                                                          │
│  2. 层级表达从属关系                                      │
│     ✅ GET /api/users/{id}/orders                         │
│                                                          │
│  3. 用 HTTP 方法表达动作                                  │
│     ✅ DELETE /api/users/{id}                             │
│     ❌ POST /api/deleteUser                               │
│                                                          │
│  4. 用查询参数做过滤、分页、排序                          │
│     GET /api/users?status=active&page=1&size=20          │
│     &sort=createTime,desc                                │
│                                                          │
│  5. 版本控制                                              │
│     路径: /api/v1/users  (直观，推荐)                     │
│     Header: Accept: application/vnd.api.v1+json          │
│                                                          │
│  6. 状态码语义化                                          │
│     200 成功 / 201 创建 / 204 无内容                      │
│     400 参数错误 / 401 未认证 / 403 无权限                │
│     404 不存在 / 409 冲突 / 422 语义错误                  │
│     500 服务器内部错误                                    │
│                                                          │
│  7. 错误响应统一结构                                      │
│     { "code": 40001, "message": "...", "traceId": "..." }│
│                                                          │
│  8. 幂等性                                                │
│     GET/PUT/DELETE 天然幂等，POST 不幂等                  │
│     重复提交: 用幂等键 (Idempotency-Key) / 唯一约束       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试答法

> "REST 核心是把一切看成资源，用 URL 定位资源，用 HTTP 方法表达操作。列表查询用 GET + 分页参数，创建用 POST 返回 201，更新用 PUT/PATCH，删除用 DELETE 返回 204。注意幂等性设计：PUT 和 DELETE 必须幂等，POST 创建可以用幂等键或数据库唯一约束防重复。错误响应给统一 JSON 结构，带上业务码和 traceId 方便排查。"

---

## Q7: Spring MVC 如何支持异步？DeferredResult / Callable？

```
┌──────────────────────────────────────────────────────────┐
│                 Spring MVC 异步处理                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  同步模式 (默认):                                         │
│  Tomcat 线程 ──▶ 处理请求 ──▶ 等待结果 ──▶ 写响应        │
│  ⚠️ 高延迟接口会占满线程池                                │
│                                                          │
│  异步模式:                                                │
│  Tomcat 线程 ──▶ 返回 Callable/DeferredResult ──▶ 释放   │
│                      │                                   │
│                      ▼ (其他线程/事件)                    │
│                 设置结果 ──▶ 再分配线程写响应             │
│                                                          │
│  三种方式:                                                │
│  ├── Callable<T>          方法返回 Callable              │
│  │     └─▶ Spring 自己在线程池执行，适合简单异步          │
│  ├── DeferredResult<T>    外部设置结果                   │
│  │     └─▶ 适合 MQ 回调、远程调用、长轮询                │
│  └── ResponseBodyEmitter / SSE / WebSocket               │
│        └─▶ 流式响应、服务端推送                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 代码示例

```java
// 方式 1: Callable — 简单异步，Spring 自动调度
@GetMapping("/async/callable")
public Callable<String> callable() {
    return () -> {
        Thread.sleep(1000);  // 模拟耗时调用
        return "ok";
    };
}

// 方式 2: DeferredResult — 由外部事件完成
@GetMapping("/async/deferred")
public DeferredResult<String> deferred() {
    DeferredResult<String> result = new DeferredResult<>(5000L);  // 超时 5s
    result.onTimeout(() -> result.setErrorResult("timeout"));
    result.onError(e -> result.setErrorResult("error"));
    // 提交给 MQ 消费者 / 线程池 / Future 回调
    asyncService.doSomething(value -> result.setResult(value));
    return result;
}

// 方式 3: SSE 服务端推送
@GetMapping(value = "/sse", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public ResponseBodyEmitter sse() {
    ResponseBodyEmitter emitter = new ResponseBodyEmitter();
    executor.execute(() -> {
        try {
            for (int i = 0; i < 10; i++) {
                emitter.send("event: tick\ndata: " + i + "\n\n");
                Thread.sleep(1000);
            }
            emitter.complete();
        } catch (Exception e) {
            emitter.completeWithError(e);
        }
    });
    return emitter;
}
```

### 面试关键点

> "Spring MVC 异步的核心是把请求处理线程尽快还给容器。Callable 适合简单后台计算；DeferredResult 适合和 MQ、第三方回调、长轮询结合，由外部线程 setResult；SSE / WebSocket 适合服务端推送。注意要配置 Tomcat 异步超时和线程池参数，否则高并发下异步反而拖垮容器。"

---

## Q8: 参数绑定原理？HttpMessageConverter？

```
┌──────────────────────────────────────────────────────────┐
│                 参数绑定与消息转换                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  HandlerAdapter 调用前:                                   │
│  HandlerMethodArgumentResolver 组合解析每个参数           │
│                                                          │
│  常见 Resolver:                                           │
│  ├── RequestParamMethodArgumentResolver                   │
│  │     └─▶ @RequestParam / Map / Model 等                 │
│  ├── PathVariableMethodArgumentResolver                   │
│  │     └─▶ @PathVariable                                  │
│  ├── RequestResponseBodyMethodProcessor                   │
│  │     └─▶ @RequestBody → HttpMessageConverter            │
│  ├── ServletModelAttributeMethodProcessor                 │
│  │     └─▶ 表单对象 / 无注解的 POJO (表单绑定)            │
│  └── RequestHeaderMethodArgumentResolver                  │
│        └─▶ @RequestHeader                                 │
│                                                          │
│  HttpMessageConverter 职责:                               │
│  ├── read:  HTTP 请求体  → Java 对象                     │
│  └── write: Java 对象    → HTTP 响应体                   │
│                                                          │
│  常用 Converter:                                          │
│  ├── MappingJackson2HttpMessageConverter (JSON)          │
│  ├── StringHttpMessageConverter                          │
│  ├── ByteArrayHttpMessageConverter                       │
│  ├── FormHttpMessageConverter (表单)                     │
│  └── ResourceHttpMessageConverter (文件)                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 内容协商

```yaml
# application.yml
spring:
  mvc:
    contentnegotiation:
      favor-parameter: true      # ?format=json
      media-types:
        json: application/json
        xml: application/xml
```

```java
// 自定义 Converter
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {
    @Override
    public void extendMessageConverters(
            List<HttpMessageConverter<?>> converters) {
        // 把 Fastjson / 自定义 Converter 放在 Jackson 前面
        converters.add(0, new FastJsonHttpMessageConverter());
    }
}
```

### 面试答法

> "参数绑定由 HandlerMethodArgumentResolver 体系完成：@RequestParam 走 RequestParam 解析器，@RequestBody 走 RequestResponseBodyMethodProcessor，它会委托 HttpMessageConverter 把 JSON 反序列化成对象。HttpMessageConverter 是双向的，既负责读请求体也负责写响应体。常见的是 Jackson 的 MappingJackson2HttpMessageConverter，也可以通过 extendMessageConverters 替换或新增 Converter。"

---

## Q9: 静态资源处理？

### 默认规则

| 配置 | 说明 |
|------|------|
| `spring.web.resources.static-locations` | 静态资源目录 (默认 classpath:/static 等) |
| `spring.mvc.static-path-pattern` | 静态资源 URL 前缀 (默认 `/**`) |
| ResourceHttpRequestHandler | 默认静态资源处理器 |
| welcome page | `static/index.html` 自动成为欢迎页 |

### 自定义静态资源映射

```java
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // /static/** 映射到本地目录
        registry.addResourceHandler("/static/**")
                .addResourceLocations("file:/data/uploads/",
                                      "classpath:/static/")
                .setCachePeriod(3600);  // 缓存 1 小时

        // 版本化静态资源 (浏览器缓存友好)
        registry.addResourceHandler("/assets/**")
                .addResourceLocations("classpath:/assets/")
                .resourceChain(true)
                .addResolver(new VersionResourceResolver()
                        .addContentVersionStrategy("/**"));
    }

    // 如果只想让 Controller 处理 /api/**，静态资源单独放
    // 注意: addPathPatterns 会影响拦截器，不影响资源映射
}
```

### 静态资源与 DispatcherServlet 的关系

```
┌──────────────────────────────────────────────────────────┐
│              静态资源如何被处理                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  DispatcherServlet 默认映射 "/" (不是 "/*")              │
│  │                                                       │
│  ├─▶ 先按 HandlerMapping 找 Controller                   │
│  │     找不到 ↓                                           │
│  ├─▶ ResourceHttpRequestHandler 处理静态资源             │
│  │     找不到 ↓                                           │
│  └─▶ 404                                                  │
│                                                          │
│  常见坑:                                                  │
│  ├── 优先级: SimpleUrlHandlerMapping 默认优先级较低      │
│  │     RequestMappingHandlerMapping 优先找 Controller     │
│  ├── 和 Controller 路径冲突时以 Controller 为准          │
│  └── 前端路由 (SPA) 需配置 forward 到 index.html         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 面试关键点

> "Spring Boot 默认把 classpath:/static、/public、/resources 下的文件当静态资源，URL 前缀是 /**。可以通过 addResourceHandlers 自定义映射到本地磁盘或 CDN，并配置缓存头。DispatcherServlet 映射的是 /，所以静态资源会先走 Controller 匹配，匹配不到才交给 ResourceHttpRequestHandler。生产环境静态资源一般走 Nginx/CDN，应用服务器只保留接口。"

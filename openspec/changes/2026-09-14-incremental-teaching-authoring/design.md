## Context

当前运行时的来源是 published artifact，而 `quality.py` 只在离线升级脚本中执行。原脚本无论内容是否变化都会遍历并新增全部主题 revision；`TeachingArtifactStore.published()` 又按目录最大 revision 读取，使未被索引激活的中间产物也可能成为运行时内容。

## Goals / Non-Goals

**Goals:**

- 修改一个主题的解释或绘图规则后，重启并打开该案例即可看到通过校验的新正式版本。
- 未改变主题只做一次内存比较，零文件写入；不扫描或重建其他主题。
- 新版本失败时，运行时继续使用 `index.json` 指向的旧 published revision。
- 保持 draft、reviewed、published、审计记录和编译快照的既有发布语义。

**Non-Goals:**

- 不提供绕过校验的预览目录或运行时 draft fallback。
- 不自动发布讲义来源变化；source hash 不一致仍按既有规则拒绝。
- 不在打包安装目录、测试默认窗口或自定义 artifact root 中隐式写文件。

## Decisions

### 1. 按当前主题惰性同步

案例加载和工作区案例恢复在解析 bundle 前同步当前 `topic_id`。这使成本与用户正在打开的一个案例相关，而不是与全部章节数量相关；`quality.py` 仍在进程重启后重新导入，因此代码改动会自然生效。

### 2. 规范化 artifact digest 判断变化

质量适配器先作用于当前索引 revision，使用忽略循环 digest 字段的 `artifact_digest` 比较。相同直接返回 `unchanged`，不创建 draft、审核、审计、snapshot 或索引写入。

### 3. 索引是发布激活边界

当 store 存在 `index.json` 时，`published()` 只读取该主题的 `published_revision`（兼容旧行的 `revision`）。增量服务完成全部静态校验、编译、draft/reviewed/published 写入和 snapshot 后，最后原子 upsert 索引。未索引的新文件不会被运行时选中。

### 4. 正式入口显式启用

`MainWindow` 默认不启用 authoring，正式 `main.py` 显式打开；服务还要求当前目录是 Git 源码 checkout、讲义存在且 store 是仓库内置路径。这样开发运行直接生效，同时避免测试或打包安装产生隐式资源写入。

### 5. 搜索索引不编译场景

目录搜索只需要解释文本。模型初始化时复用一个 `TeachingArtifactStore`，直接读取 indexed published explanation；store 按索引文件时间戳和大小缓存解析结果。构建搜索索引不得调用 `resolve_bundle()` 或视觉编译器。

## Risks / Trade-offs

- [Risk] 校验在 GUI 加载线程执行。→ 只处理当前主题；unchanged 路径不编译、不写盘，完整校验仅在代码确实改变该主题时运行一次。
- [Risk] published 文件已写但索引切换失败。→ 文件保持未激活，运行时仍读旧索引；下一次同步可重新尝试，不会展示半发布版本。
- [Risk] 第 4–8 章使用 reviewed fallback。→ 索引指向但缺少 published 文件时返回空，让既有 fallback 继续接管；绝不改读未索引 revision。
- [Risk] 缓存隐藏外部索引更新。→ 每次读取比较 `mtime_ns` 与文件大小，本进程写索引后主动失效缓存。

## Migration Plan

1. 增加索引驱动的 published 读取和单主题原子 upsert。
2. 增加增量 authoring 服务并接入案例加载/恢复。
3. 将批量升级脚本改为复用同一服务。
4. 运行 store、bundle、加载、恢复、质量和可视化编译回归；验证 OpenSpec。

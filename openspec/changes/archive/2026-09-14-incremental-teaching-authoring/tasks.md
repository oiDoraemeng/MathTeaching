## 1. 发布边界

- [x] 1.1 让存在 `index.json` 的 store 严格按索引 revision 读取 published artifact
- [x] 1.2 增加单主题索引 upsert，并保留已有行元数据与稳定排序
- [x] 1.3 增加测试证明未索引的新 revision 不会被运行时读取

## 2. 增量 authoring

- [x] 2.1 比较当前主题 refine 前后的规范化 digest，未变化零写入
- [x] 2.2 对变化主题执行 schema、来源、数学、引用、contract 和 compiler 全部校验
- [x] 2.3 校验成功后生成 draft、reviewed、published、snapshot，最后激活索引
- [x] 2.4 校验失败返回可诊断结果并保持旧 published revision

## 3. 运行时与脚本

- [x] 3.1 正式应用入口显式启用源码 checkout 的单主题同步
- [x] 3.2 案例打开和工作区恢复在 bundle 解析前同步当前主题
- [x] 3.3 批量升级脚本复用同一增量服务并报告 unchanged/rejected/published
- [x] 3.4 目录搜索索引直接读取 published explanation，禁止全主题 bundle 编译并复用 store 索引缓存

## 4. 验证与提交

- [x] 4.1 运行教学 store、authoring、bundle、案例加载和工作区恢复测试
- [x] 4.2 运行相关线性代数质量、编译和内容校验回归
- [x] 4.3 通过 OpenSpec 严格校验，并按功能范围提交代码与规范

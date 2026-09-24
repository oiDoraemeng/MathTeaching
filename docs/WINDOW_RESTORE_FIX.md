# 窗口最小化恢复后内容空白问题修复方案

## 问题描述

在 Windows 平台上，程序窗口最小化后恢复时出现以下问题：
- 窗口弹出但内容全白（或停留在最小化前的画面）
- 窗口无法交互，看似"卡死"
- 有时拖动窗口边缘或调整尺寸后恢复正常
- 特别影响 WebEngine 内容的显示

## 根本原因

Qt 内部的 `WA_Mapped` 状态标记窗口是否已被"映射到屏幕"。在 Windows 从最小化恢复时：
1. 操作系统通知 Qt 窗口即将显示
2. 但 Qt 可能未正确设置 `WA_Mapped` 标志
3. Qt 认为窗口仍处于"未映射"状态
4. 跳过绘制流程，造成界面空白

## 解决方案

### 1. 核心修复：设置 WA_Mapped 属性

**文件：** `ui/designer_window.py`  
**类：** `_WindowRestoreFilter`

在窗口事件过滤器中添加对 `Show` 事件和 `WindowStateChange` 事件的处理：

```python
def eventFilter(self, watched: QObject, event: QEvent) -> bool:
    # 🔑 核心修复：在窗口即将显示时设置 WA_Mapped 属性
    if event.type() == QEvent.Type.Show:
        if isinstance(watched, QWidget):
            watched.setAttribute(Qt.WidgetAttribute.WA_Mapped)

    if event.type() == QEvent.Type.WindowStateChange:
        if isinstance(event, QWindowStateChangeEvent):
            if (event.oldState() & Qt.WindowState.WindowMinimized) and not watched.isMinimized():
                # 在恢复时也确保 WA_Mapped 标志被正确设置
                if isinstance(watched, QWidget):
                    watched.setAttribute(Qt.WidgetAttribute.WA_Mapped)
                self._restore_timer.start(300)
    return False
```

**原理：**
- 显式设置 `Qt::WA_Mapped` 强制告诉 Qt："这个窗口现在是可见且已映射的"
- 确保 Qt 的窗口映射状态与操作系统实际状态同步
- 触发 Qt 的绘制系统（如 paintEvent）正常工作

### 2. 辅助方案：改进 WebEngine 表面重建

**文件：** `ui/web_surface.py`  
**函数：** `rebuild_web_surface()`

改进方法：
- **方法1（优先）**：使用 `hide()` + `processEvents()` + `show()` 序列
  - 强制 Qt 销毁并重建原生窗口表面
  - 在每个关键步骤后调用 `processEvents()` 确保事件队列立即处理
  
- **方法2（降级）**：resize 触发几何变化
  - 改变幅度从 1px 提升到 10px
  - 确保 Chromium 能检测到变化

### 3. 增强重试机制

**文件：** `ui/designer_window.py`  
**方法：** `_schedule_web_surface_retries()`

改进：
- 从单次重试改为 **3 次递增延迟重试**：400ms、800ms、1200ms
- 覆盖 Windows 恢复动画的不同阶段
- 提高至少一次命中正确时机的概率

## 测试验证

运行测试脚本：

```bash
python test_window_restore_fix.py
```

**测试步骤：**
1. 窗口正常显示 WebEngine 内容（紫色渐变背景 + 实时时钟）
2. 点击"最小化窗口"按钮
3. 点击任务栏图标恢复窗口
4. **预期结果**：WebEngine 内容立即可见且可交互，时钟继续更新
5. 点击"检查 WA_Mapped 状态"按钮验证修复效果
6. 拖动窗口边缘确认响应正常

**调试输出：**
- 每次 Show 事件触发时输出 WA_Mapped 设置日志
- 每次窗口状态恢复时输出 WA_Mapped 状态
- 每次表面重建尝试的日志

## 适用平台

| 平台 | 常见性 | 修复有效性 |
|------|--------|-----------|
| Windows | ✅ 高频 | ⭐⭐⭐⭐⭐ |
| Linux (X11) | ⚠️ 偶发 | ⭐⭐⭐ |
| Linux (Wayland) | ❓ 较少 | ⭐⭐ |
| macOS | ❌ 极少 | 通常不需要 |

## 注意事项

1. **不要滥用 `setAttribute(Qt::WA_Mapped)`**
   - 仅在 Show 事件和 WindowStateChange 事件中设置
   - 不要在构造函数或其他地方随意调用

2. **这不是内存泄漏或死锁**
   - 程序仍在运行，只是 GUI 渲染被阻断
   - 可通过日志输出验证逻辑是否执行

3. **与 `WA_DontShowOnScreen` 冲突**
   - 若使用了 `WA_DontShowOnScreen`（如截图工具）
   - 则不应设置 `WA_Mapped`

## 参考资料

- CSDN 文章：《Qt 窗口最小化后恢复时出现假死问题的解决方案》
- Qt 文档：[Qt::WidgetAttribute](https://doc.qt.io/qt-6/qt.html#WidgetAttribute-enum)
- Qt 文档：[QWidget::showEvent()](https://doc.qt.io/qt-6/qwidget.html#showEvent)

## 修改的文件

1. `ui/designer_window.py` - 添加 WA_Mapped 设置到 `_WindowRestoreFilter`
2. `ui/web_surface.py` - 改进 `rebuild_web_surface()` 函数
3. `test_window_restore_fix.py` - 创建测试验证脚本

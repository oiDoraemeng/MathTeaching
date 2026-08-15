/**
 * MathLive / Qt WebChannel 桥接控件共用的工具函数。
 *
 * mathlive.html、inline_formula_overlay.html 与 formula_preview.html
 * 会在各自初始化脚本之前加载本文件。
 */
'use strict';

window.MathLiveBridge = (() => {

  function formulaHeight(field, minHeight) {
    const content = field.shadowRoot?.querySelector('[part=content]');
    return Math.max(
      minHeight,
      Math.ceil(field.scrollHeight || 0),
      Math.ceil(content?.scrollHeight || 0),
      Math.ceil(content?.getBoundingClientRect().height || 0),
    );
  }

  function createHeightReporter(field, bridge, minHeight) {
    let scheduled = false;
    const report = () => {
      scheduled = false;
      bridge.contentHeightChanged(formulaHeight(field, minHeight));
    };
    const schedule = () => {
      if (scheduled) return;
      scheduled = true;
      // 字体和 Shadow DOM 的重排时机不同，帧回调与短定时器共同保证高度最终会同步。
      requestAnimationFrame(report);
      setTimeout(report, 30);
    };
    const observeContent = () => {
      const content = field.shadowRoot?.querySelector('[part=content]');
      if (content) {
        new ResizeObserver(schedule).observe(content);
      }
    };
    return { report, schedule, observeContent };
  }

  function createNativeToolbarAction(field, part, action, label, activate) {
    const source = field.shadowRoot?.querySelector(`[part=${part}]`);
    if (!source) return null;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'mathlive-native-action';
    button.dataset.action = action;
    button.setAttribute('aria-label', label);
    button.title = label;
    button.innerHTML = source.innerHTML;
    let handledPointerDown = false;
    button.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      handledPointerDown = true;
      activate(button);
    }, true);
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (handledPointerDown) {
        handledPointerDown = false;
        return;
      }
      activate(button);
    }, true);
    return button;
  }

  function installKeyboardToolbarActions(field, callbacks) {
    let observer;
    const install = () => {
      const keyboard = window.mathVirtualKeyboard?.element;
      if (!keyboard) return;
      if (!observer) {
        observer = new MutationObserver(install);
        observer.observe(keyboard, { childList: true, subtree: true });
      }
      const toolbar = keyboard.querySelector('.MLK__toolbar');
      const toolbarActions = toolbar?.querySelector('.ML__edit-toolbar.right');
      if (!toolbarActions) return;
      let actions = toolbarActions.querySelector('.mathlive-native-actions');
      if (!actions) {
        actions = document.createElement('div');
        actions.className = 'mathlive-native-actions';
        toolbarActions.append(actions);
      }
      if (!actions.querySelector('[data-action=toggle-keyboard]')) {
        // 复用 MathLive 原生按钮图标，同时把行为交给 Qt 侧提供的回调。
        const keyboardAction = createNativeToolbarAction(
          field, 'virtual-keyboard-toggle', 'toggle-keyboard',
          'Show or hide virtual keyboard',
          () => callbacks.toggleKeyboard(),
        );
        if (keyboardAction) actions.append(keyboardAction);
      }
      if (!actions.querySelector('[data-action=mathlive-menu]')) {
        const menuAction = createNativeToolbarAction(
          field, 'menu-toggle', 'mathlive-menu', 'MathLive menu',
          (button) => {
            const menu = field._mathfield.menu;
            if (menu.state !== 'closed') { menu.hide(); return; }
            const rect = button.getBoundingClientRect();
            field._mathfield.showMenu({ location: { x: rect.left, y: rect.bottom } });
          },
        );
        if (menuAction) actions.append(menuAction);
      }
    };
    return install;
  }

  return {
    formulaHeight,
    createHeightReporter,
    createNativeToolbarAction,
    installKeyboardToolbarActions,
  };

})();

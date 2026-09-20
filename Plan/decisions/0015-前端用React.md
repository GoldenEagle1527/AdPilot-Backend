# ADR 0015：前端使用 React

状态：accepted

关闭 Q-FE-1。许可证：React 为 MIT，符合 [0013](0013-公司研发规范.md)。

## 决定

前端框架为 **React**。脚手架须能按 `frontend/src/modules/<business-id>` 拆页面。推荐官方 Vite + React（Vite 为 MIT），不强制 UI 组件库；若加组件库须再核许可证。

## 后果

本仓不维护前端工程与前端计划。调用方栈不在本仓落地。


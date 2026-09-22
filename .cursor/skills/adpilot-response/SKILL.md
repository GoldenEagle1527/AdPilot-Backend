---
name: adpilot-response
description: AdPilot 后端统一响应格式。写或改任何 HTTP 接口、异常处理、分页返回时用。
---

# 响应只走 `app.core.envelope`

不要自己拼 dict，不要自己造 JSONResponse，不要再出现 `ok` / `error` / `msg`。

```python
from app.core.envelope import ApiError, Envelope, success
```

## 成功

```python
@router.get("/xxx", response_model=Envelope[XxxData])
async def get_xxx() -> dict[str, Any]:
    """一句话说明。"""
    return success(data)
```

出参固定 `{"code": 200, "message": "成功", "data": ...}`。成功只用 HTTP 200，不用 201 / 204。

## 失败

抛 `ApiError(HTTP 状态, "给人看的一句话")`，别的不用管，全局处理器会收成同一套信封。

```python
raise ApiError(404, "部门不存在")
```

- `code` 恒等于 HTTP 状态，**不要**自定义 `NOT_FOUND` 这类字符串码；要区分场景就写在 `message` 里。
- 业务失败 400/409，未登录 401，没权限 403，不存在 404，校验失败 422，自身 bug 500，下游挂 503。
- 禁止 HTTP 200 里包业务失败。
- 校验失败交给 Pydantic，别手写 422；未捕获异常别自己 try 兜，全局处理器出 500 且不外泄堆栈。

## 分页

用 `app.core.pagination` 的 `page_data`，列表字段对外叫 `list`：

```json
{ "code": 200, "message": "成功", "data": { "list": [], "total": 0, "page": 1, "page_size": 20 } }
```

入参 `page` 从 1 起、`page_size` 默认 20 上限 100。空结果是 `list: []` + `total: 0`，不要把 `data` 设成 null。不分页的树用 `data: {"items": [...]}`。

## 改动后

改了对外形状，同一 PR 里改 `Plan/modules/<id>/contracts/` 的契约、变更历史和 `最新表.md`。测试走 `python run_tests.py`。

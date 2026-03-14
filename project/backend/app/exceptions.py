"""Unified business exceptions with error codes and bilingual messages."""

from __future__ import annotations


class BizError(Exception):
    """Base business exception that carries a numeric code and bilingual user-facing message."""

    def __init__(self, code: int, message: str, http_status: int = 400, message_en: str = ""):
        self.code = code
        self.message = message
        self.message_en = message_en or message
        self.http_status = http_status
        super().__init__(message)


# ── Auth 401xx ──────────────────────────────────────────────────────
INVALID_CREDENTIALS = lambda: BizError(40101, "用户名或密码错误", 401, "Invalid username or password")
INVALID_TOKEN       = lambda: BizError(40102, "无效的认证令牌", 401, "Invalid authentication token")        # noqa: E222
ACCOUNT_DISABLED    = lambda: BizError(40103, "账号已被禁用", 403, "Account has been disabled")          # noqa: E222
INVALID_REFRESH     = lambda: BizError(40104, "无效的刷新令牌", 401, "Invalid refresh token")        # noqa: E222
USER_NOT_FOUND      = lambda: BizError(40105, "用户不存在", 401, "User not found")            # noqa: E222

# ── Bad Request 400xx ───────────────────────────────────────────────
PARAM_ERROR         = lambda m="参数错误", m_en="Parameter error": BizError(40001, m, 400, m_en)          # noqa: E222
EMAIL_REGISTERED    = lambda: BizError(40002, "该邮箱已被注册", 400, "Email already registered")        # noqa: E222
USERNAME_REGISTERED = lambda: BizError(40003, "该用户名已被注册", 400, "Username already registered")

# ── Forbidden 403xx ─────────────────────────────────────────────────
PERMISSION_DENIED   = lambda r="": BizError(40301, f"权限不足: {r}" if r else "权限不足", 403, f"Permission denied: {r}" if r else "Permission denied")  # noqa: E222

# ── Validation 422xx ────────────────────────────────────────────────
VALIDATION_ERROR    = lambda d="": BizError(42200, f"参数验证错误: {d}" if d else "参数验证错误", 422, f"Validation error: {d}" if d else "Validation error")  # noqa: E222

# ── Server 500xx ────────────────────────────────────────────────────
INTERNAL_ERROR      = lambda: BizError(50000, "服务器内部错误", 500, "Internal server error")         # noqa: E222

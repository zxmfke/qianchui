"""Simple i18n utility for backend error messages."""

from fastapi import Request

# Error message keys -> (zh, en)
ERROR_MESSAGES: dict[str, tuple[str, str]] = {
    # Auth
    "invalid_credentials": ("用户名或密码错误", "Invalid username or password"),
    "user_not_found": ("用户不存在", "User not found"),
    "account_disabled": ("账号已被禁用", "Account is disabled"),
    "token_expired": ("Token已过期", "Token expired"),
    "invalid_token": ("无效的Token", "Invalid token"),
    "invalid_refresh": ("无效的刷新令牌", "Invalid refresh token"),
    "email_registered": ("邮箱已注册", "Email already registered"),
    "username_exists": ("用户名已存在", "Username already exists"),
    "provide_username_or_email": ("请提供用户名或邮箱", "Please provide username or email"),
    # General
    "resource_not_found": ("资源未找到", "Resource not found"),
    "internal_error": ("服务器内部错误", "Internal server error"),
    "param_error": ("请求参数错误", "Invalid request parameters"),
    "access_denied": ("无权限访问", "Access denied"),
    "permission_denied": ("权限不足", "Permission denied"),
    "validation_error": ("参数验证错误", "Validation error"),
    # Training
    "diagnosis_failed": ("诊断失败，请重试", "Diagnosis failed, please retry"),
    "submit_failed": ("提交失败", "Submit failed"),
}


def get_error_message(key: str, lang: str = "zh") -> str:
    """Return localized error message by key and language."""
    if key not in ERROR_MESSAGES:
        zh, en = ERROR_MESSAGES.get("internal_error", ("服务器内部错误", "Internal server error"))
        return en if lang == "en" else zh
    zh, en = ERROR_MESSAGES[key]
    return en if lang == "en" else zh


def get_lang(request: Request) -> str:
    """Extract language from Accept-Language header. Returns 'en' or 'zh'."""
    accept = request.headers.get("accept-language", "zh")
    return "en" if "en" in accept.lower() else "zh"


# Map BizError codes to i18n keys for conversion
BIZ_ERROR_CODE_TO_KEY: dict[int, str] = {
    40101: "invalid_credentials",
    40102: "invalid_token",
    40103: "account_disabled",
    40104: "invalid_refresh",
    40105: "user_not_found",
    40001: "param_error",
    40002: "email_registered",
    40003: "username_exists",
    40301: "permission_denied",
    42200: "validation_error",
    50000: "internal_error",
}

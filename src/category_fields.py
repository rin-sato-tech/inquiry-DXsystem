from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CategoryField:
    """カテゴリ別追加項目の定義。"""

    key: str
    label: str
    field_type: str = "text"
    options: tuple[str, ...] = ()


CATEGORY_FIELDS: dict[str, list[CategoryField]] = {
    "PC・システム": [
        CategoryField("pc_asset_id", "PC管理番号"),
        CategoryField("occurred_at", "発生時刻"),
        CategoryField("error_detail", "エラー内容", field_type="text_area"),
        CategoryField("reboot_done", "再起動有無", field_type="select", options=("未確認", "実施済み", "未実施")),
    ],
    "アカウント・権限": [
        CategoryField("target_system", "対象システム"),
        CategoryField("target_folder", "対象フォルダ・対象機能"),
        CategoryField("required_permission", "必要な権限"),
        CategoryField("approver", "承認者"),
    ],
    "勤怠・労務": [
        CategoryField("target_date", "対象日", field_type="date"),
        CategoryField("before_time", "修正前時刻"),
        CategoryField("after_time", "修正後時刻"),
        CategoryField("reason", "理由", field_type="text_area"),
    ],
    "経費・請求": [
        CategoryField("amount", "金額"),
        CategoryField("business_partner", "取引先"),
        CategoryField("target_month", "対象月"),
        CategoryField("attachment_exists", "添付書類有無", field_type="select", options=("未確認", "あり", "なし")),
    ],
    "備品・設備": [
        CategoryField("item_name", "備品名・設備名"),
        CategoryField("quantity", "数量"),
        CategoryField("purpose", "利用目的", field_type="text_area"),
        CategoryField("desired_date", "希望日", field_type="date"),
    ],
}


def get_category_fields(category: str) -> list[CategoryField]:
    """カテゴリに対応する追加項目定義を返す。"""

    return CATEGORY_FIELDS.get(category, [])


def format_additional_info(category: str, values: dict[str, Any]) -> str:
    """
    カテゴリ別追加情報をDB保存用の複数行テキストに整形する。

    例:
    PC管理番号: PC-014
    発生時刻: 2026-07-01 09:30
    エラー内容: 販売管理システム起動時に認証エラー
    再起動有無: 実施済み
    """

    fields = get_category_fields(category)
    label_by_key = {field.key: field.label for field in fields}

    lines: list[str] = []

    for key, value in values.items():
        label = label_by_key.get(key, key)

        if value is None:
            text = ""
        else:
            text = str(value).strip()

        if text:
            lines.append(f"{label}: {text}")

    return "\n".join(lines)
"""Search query builder for FS Link Manager"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class SearchField(Enum):
    """検索対象フィールド"""
    NAME = "name"
    PATH = "path"
    TAGS = "tags"
    ALL = "all"  # すべてのフィールド


class SearchOperator(Enum):
    """検索演算子"""
    CONTAINS = "LIKE"  # 部分一致
    EQUALS = "="       # 完全一致
    STARTS_WITH = "LIKE"  # 前方一致
    ENDS_WITH = "LIKE"    # 後方一致


@dataclass
class SearchFilter:
    """検索フィルター条件"""
    field: SearchField
    operator: SearchOperator
    value: str
    case_sensitive: bool = False

    def to_sql(self) -> Tuple[str, List[str]]:
        """SQL WHERE句とパラメータに変換"""
        # フィールド名
        if self.field == SearchField.ALL:
            fields = ["name", "path", "tags"]
        else:
            fields = [self.field.value]

        # 演算子に応じた値の変換
        if self.operator == SearchOperator.CONTAINS:
            param_value = f"%{self.value}%"
        elif self.operator == SearchOperator.STARTS_WITH:
            param_value = f"{self.value}%"
        elif self.operator == SearchOperator.ENDS_WITH:
            param_value = f"%{self.value}"
        else:  # EQUALS
            param_value = self.value

        # WHERE句の構築
        conditions = []
        params = []
        for field in fields:
            if self.operator in (SearchOperator.CONTAINS, SearchOperator.STARTS_WITH, SearchOperator.ENDS_WITH):
                conditions.append(f"{field} LIKE ?")
            else:
                conditions.append(f"{field} = ?")
            params.append(param_value)

        where_clause = " OR ".join(conditions)
        return where_clause, params


class SearchQueryBuilder:
    """検索クエリビルダー"""

    def __init__(self):
        self.filters: List[SearchFilter] = []
        self.order_by: str = "position"
        self.order_direction: str = "ASC"

    def add_filter(
        self,
        field: SearchField,
        value: str,
        operator: SearchOperator = SearchOperator.CONTAINS,
        case_sensitive: bool = False
    ) -> 'SearchQueryBuilder':
        """フィルター条件を追加（メソッドチェーン対応）"""
        self.filters.append(SearchFilter(field, operator, value, case_sensitive))
        return self

    def simple_search(self, query: str) -> 'SearchQueryBuilder':
        """簡易検索（全フィールド部分一致）"""
        if query.strip():
            self.add_filter(SearchField.ALL, query.strip(), SearchOperator.CONTAINS)
        return self

    def set_order(self, field: str, direction: str = "ASC") -> 'SearchQueryBuilder':
        """ソート順を設定"""
        self.order_by = field
        self.order_direction = direction.upper()
        return self

    def build(self) -> Tuple[str, List[str]]:
        """SQLクエリとパラメータを生成"""
        # 基本クエリ
        base_query = "SELECT id, name, path, tags, position, added_at FROM links"

        # WHERE句の構築
        if not self.filters:
            # フィルターなし
            query = f"{base_query} ORDER BY {self.order_by} {self.order_direction};"
            return query, []

        # フィルター条件を結合（AND条件）
        where_conditions = []
        all_params = []
        for filter_obj in self.filters:
            condition, params = filter_obj.to_sql()
            if len(self.filters) > 1:
                where_conditions.append(f"({condition})")
            else:
                where_conditions.append(condition)
            all_params.extend(params)

        where_clause = " AND ".join(where_conditions)
        query = f"{base_query} WHERE {where_clause} ORDER BY {self.order_by} {self.order_direction};"

        return query, all_params

    def clear(self) -> 'SearchQueryBuilder':
        """フィルター条件をクリア"""
        self.filters.clear()
        return self

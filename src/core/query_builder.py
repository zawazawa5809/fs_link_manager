"""Search query builder for FS Link Manager"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class SearchField(Enum):
    """Search target fields."""
    NAME = "name"
    PATH = "path"
    TAGS = "tags"
    ALL = "all"  # All fields


class SearchOperator(Enum):
    """Search operators for filtering."""
    CONTAINS = "LIKE"      # Partial match
    EQUALS = "="           # Exact match
    STARTS_WITH = "LIKE"   # Prefix match
    ENDS_WITH = "LIKE"     # Suffix match


@dataclass
class SearchFilter:
    """Search filter condition.

    Attributes:
        field: Target search field
        operator: Comparison operator
        value: Search value
        case_sensitive: Whether to perform case-sensitive search
    """
    field: SearchField
    operator: SearchOperator
    value: str
    case_sensitive: bool = False

    def to_sql(self) -> Tuple[str, List[str]]:
        """Convert filter to SQL WHERE clause and parameters.

        Returns:
            Tuple of (WHERE clause string, parameter list)
        """
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
    """SQL query builder for link search operations.

    Provides fluent interface for constructing parameterized SQL queries
    with support for multiple filters and ordering.
    """

    def __init__(self) -> None:
        """Initialize query builder with default settings."""
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
        """Add filter condition (supports method chaining).

        Args:
            field: Target field for filtering
            value: Search value
            operator: Comparison operator (default: CONTAINS)
            case_sensitive: Enable case-sensitive search

        Returns:
            Self for method chaining
        """
        self.filters.append(SearchFilter(field, operator, value, case_sensitive))
        return self

    def simple_search(self, query: str) -> 'SearchQueryBuilder':
        """Perform simple search across all fields.

        Args:
            query: Search query string

        Returns:
            Self for method chaining
        """
        if query.strip():
            self.add_filter(SearchField.ALL, query.strip(), SearchOperator.CONTAINS)
        return self

    def set_order(self, field: str, direction: str = "ASC") -> 'SearchQueryBuilder':
        """Set result ordering.

        Args:
            field: Field name to order by
            direction: Sort direction ("ASC" or "DESC")

        Returns:
            Self for method chaining
        """
        self.order_by = field
        self.order_direction = direction.upper()
        return self

    def build(self) -> Tuple[str, List[str]]:
        """Build SQL query and parameters.

        Returns:
            Tuple of (SQL query string, parameter list)
        """
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

    def filter_by_tags(
        self,
        tags: List[str],
        match_mode: str = "OR"
    ) -> 'SearchQueryBuilder':
        """タグによるフィルタリング

        Args:
            tags: フィルタ対象タグリスト
            match_mode: "OR"(いずれか一致) or "AND"(全て一致)

        Returns:
            Self(メソッドチェーン)
        """
        if not tags:
            return self

        if match_mode == "OR":
            # いずれかのタグを含む(OR条件)
            # 複数のフィルタを追加すると、SearchFilterのto_sqlメソッドで
            # OR条件として結合される
            for tag in tags:
                self.add_filter(
                    SearchField.TAGS,
                    tag,
                    SearchOperator.CONTAINS
                )
        else:  # AND
            # 全てのタグを含む
            # 現在の実装では完全なAND実装は複雑なため、Phase2で対応
            # 暫定的にOR条件として動作
            for tag in tags:
                self.add_filter(
                    SearchField.TAGS,
                    tag,
                    SearchOperator.CONTAINS
                )

        return self

    def clear(self) -> 'SearchQueryBuilder':
        """Clear all filter conditions.

        Returns:
            Self for method chaining
        """
        self.filters.clear()
        return self

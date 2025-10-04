"""Translation management for FS Link Manager"""

import json
from pathlib import Path
from typing import Dict, Optional, ClassVar
from PySide6.QtCore import QObject, Signal, QSettings


class Translator(QObject):
    """国際化対応の翻訳マネージャー"""

    _instance: ClassVar[Optional['Translator']] = None
    language_changed = Signal(str)  # 言語変更シグナル

    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初期化（一度のみ実行）"""
        if hasattr(self, '_initialized'):
            return

        super().__init__()
        self.translations: Dict[str, Dict] = {}
        self.current_language: str = 'ja_JP'
        self._initialized = True
        self._load_translations()

    def _load_translations(self):
        """翻訳ファイルを読み込み"""
        i18n_dir = Path(__file__).parent

        for trans_file in i18n_dir.glob("*.json"):
            try:
                with open(trans_file, 'r', encoding='utf-8') as f:
                    lang_code = trans_file.stem
                    self.translations[lang_code] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"翻訳ファイル読み込みエラー {trans_file}: {e}")

    def restore_language(self, lang_code: str):
        """外部から指定された言語を復元"""
        if lang_code in self.translations:
            self.current_language = lang_code
        else:
            self.current_language = "ja_JP"

    def set_language(self, lang_code: str):
        """言語を設定"""
        if lang_code not in self.translations:
            raise ValueError(f"Unknown language: {lang_code}")

        self.current_language = lang_code
        self.language_changed.emit(lang_code)

    def get(self, key_path: str, **kwargs) -> str:
        """
        翻訳テキストを取得

        Args:
            key_path: ドット区切りのキーパス (例: "toolbar.add_tooltip")
            **kwargs: プレースホルダー置換用のパラメータ

        Returns:
            翻訳されたテキスト
        """
        keys = key_path.split('.')
        data = self.translations.get(self.current_language, {})

        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return f"[{key_path}]"  # キーが見つからない場合

        if data is None:
            return f"[{key_path}]"

        # プレースホルダー置換
        if kwargs:
            try:
                return str(data).format(**kwargs)
            except KeyError:
                return str(data)

        return str(data)

    def get_available_languages(self) -> list:
        """利用可能な言語のリストを取得"""
        return list(self.translations.keys())

    def get_language_name(self, lang_code: str) -> str:
        """言語コードから表示名を取得"""
        lang_names = {
            'ja_JP': '日本語',
            'en_US': 'English'
        }
        return lang_names.get(lang_code, lang_code)


# グローバル関数（簡易アクセス用）
_translator = None

def tr(key_path: str, **kwargs) -> str:
    """翻訳テキストを取得する簡易関数"""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator.get(key_path, **kwargs)

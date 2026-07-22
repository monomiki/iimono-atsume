from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from src.types import Candidate, Recommendation


class MarkdownReporter:
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir

    def write(self, run_date: str, candidates_count: int, duplicates: List[Tuple[Candidate, str]], recommendations: List[Recommendation], saved: List[Recommendation]) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.reports_dir / f"{run_date}.md"
        high = saved[:5]
        discoveries = [rec for rec in saved if rec.candidate.discovery][:5]
        exclusion_counts: Dict[str, int] = {}
        for _, reason in duplicates:
            exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
        lines = [
            "# AIデイリー収集レポート",
            f"日付: {run_date}",
            "",
            "## 今日の概要",
            "",
            f"- 収集候補数: {candidates_count}",
            f"- 重複除外数: {len(duplicates)}",
            f"- 評価対象数: {len(recommendations)}",
            f"- Raindrop保存数: {len(saved)}",
            "",
            "## 特におすすめ",
            "",
        ]
        if not high:
            lines.append("- 高精度候補はありませんでした。")
        for idx, rec in enumerate(high, 1):
            lines.extend(self._rec_block(idx, rec))
        lines.extend(["", "## 新規発見", ""])
        if not discoveries:
            lines.append("- 新規発見枠の採用はありませんでした。")
        for idx, rec in enumerate(discoveries, 1):
            lines.extend(
                [
                    f"### {idx}. {rec.candidate.title}",
                    "",
                    f"- 関連する既存カテゴリ: {rec.category}",
                    "- 新しく広がりそうな分野: 既存カテゴリ同士の中間領域",
                    f"- 推薦理由: {' / '.join(rec.reasons)}",
                    "",
                ]
            )
        lines.extend(["## 除外傾向", ""])
        if exclusion_counts:
            for reason, count in sorted(exclusion_counts.items(), key=lambda item: item[1], reverse=True):
                lines.append(f"- {reason}: {count}件")
        else:
            lines.append("- 重複やミラーURLによる除外はありませんでした。")
        lines.extend(
            [
                "",
                "## 学習した変化",
                "",
                "- フィードバック履歴をスコア補正へ反映しました。",
                "- 同一作者・同一カテゴリに偏りすぎないよう採用数を調整しました。",
                f"- 生成時刻: {datetime.now().isoformat(timespec='seconds')}",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    @staticmethod
    def _rec_block(idx: int, rec: Recommendation) -> List[str]:
        return [
            f"### {idx}. {rec.candidate.title}",
            "",
            f"- URL: {rec.candidate.url}",
            f"- 発見元: {rec.candidate.source}",
            f"- 推薦スコア: {rec.score}",
            f"- 推定カテゴリ: {rec.category}",
            f"- 推薦理由: {' / '.join(rec.reasons)}",
            f"- 既存ライブラリとの差分: {' / '.join(rec.novelty)}",
            "",
        ]


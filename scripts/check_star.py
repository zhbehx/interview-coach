#!/usr/bin/env python3
"""检查一段面试回答（STAR 故事）的完整度：四要素、数字、空话、口述时长。

用法：
    python scripts/check_star.py story.txt
    python scripts/check_star.py story.txt --strict     # 缺任一要素则退出码 1
    python scripts/check_star.py story.txt --json

退出码：0 正常；--strict 下缺要素时 1；文件错误 2。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SIGNALS = {
    "S": ["当时", "那会", "去年", "上个季度", "季度初", "刚接手", "入职第", "那时候", "年初", "我们团队", "在做"],
    "T": ["我要", "目标是", "被要求", "负责把", "任务是", "指标是", "deadline", "期限", "必须在", "KPI", "要把"],
    "A": ["我先", "然后", "接着", "最后", "具体", "做了", "拉了", "写了", "拆成", "定了", "找了", "改成", "一共三", "一是", "第二步"],
    "R": ["从", "到", "提升", "下降", "降低", "覆盖", "省", "增长", "缩短", "上线", "留存", "转化"],
}

EMPTY_TALK = ["提升了", "优化了", "推动了", "加强了", "赋能", "闭环", "效果不错", "领导满意", "比较顺利", "做得挺好"]
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|个|人|家|次|天|周|月|年|小时|万|千|元|倍|分|条|版)?")
CPS = 4.5  # 中文口播速度：字/秒


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[。；;\n!?！？]", text) if s.strip()]


def analyze(text: str) -> dict:
    hits = {k: [w for w in words if w.lower() in text.lower()] for k, words in SIGNALS.items()}
    missing = [k for k, v in hits.items() if not v]

    numbers = NUMBER_RE.findall(text)
    sents = sentences(text)

    empty = []
    for s in sents:
        if any(w in s for w in EMPTY_TALK) and not NUMBER_RE.search(s):
            empty.append(s[:80])

    # 结果句是否带数字：R 要素出现但全程无数字 = 结果不可核验
    result_quantified = bool(numbers) and "R" not in missing

    chars = len(re.sub(r"\s", "", text))
    seconds = round(chars / CPS)
    penalty = len(missing) * 20 + len(empty) * 5
    score = max(0, 100 - penalty)
    if not result_quantified:
        score = max(0, score - 10)

    return {
        "missing": missing,
        "signals": {k: v[:5] for k, v in hits.items()},
        "number_count": len(numbers),
        "numbers": numbers[:12],
        "result_quantified": result_quantified,
        "empty_talk": empty,
        "chars": chars,
        "est_seconds": seconds,
        "score": score,
    }


LABEL = {"S": "S 情境", "T": "T 任务", "A": "A 行动", "R": "R 结果"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="检查 STAR 故事完整度")
    ap.add_argument("file", help="故事文本文件")
    ap.add_argument("--strict", action="store_true", help="缺要素时退出码 1")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    p = Path(args.file)
    if not p.is_file():
        print(f"找不到文件：{p}", file=sys.stderr)
        return 2

    text = p.read_text(encoding="utf-8-sig")
    r = analyze(text)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("STAR 完整度：")
        for k in "STAR":
            mark = "缺" if k in r["missing"] else "有"
            sig = "、".join(r["signals"][k]) or "—"
            print(f"  [{mark}] {LABEL[k]}   信号词：{sig}")
        print(f"\n数字：{r['number_count']} 个 {('、'.join(r['numbers'])) or ''}")
        print(f"结果可核验：{'是' if r['result_quantified'] else '否（有结果表述但没有数字）'}")
        print(f"口述时长：约 {r['est_seconds']} 秒（{r['chars']} 字）")
        if r["empty_talk"]:
            print("\n空话句（有评价、无事实）：")
            for s in r["empty_talk"]:
                print(f"  - {s}")
        print(f"\n评分：{r['score']}/100")
        if r["missing"]:
            print("补法：S 缺→补时间/业务规模；T 缺→补你的那份任务与期限；"
                  "A 缺→补 2–3 个具体动作顺序；R 缺→补从 A 到 B 的数字。")
        if r["est_seconds"] > 150:
            print("提示：超过 150 秒，主故事压到 90–120 秒，细节留给追问。")

    if args.strict and r["missing"]:
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))

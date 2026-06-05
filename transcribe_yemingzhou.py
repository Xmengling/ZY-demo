# -*- coding: utf-8 -*-
"""Transcribe long audio with DashScope Paraformer and export timestamped text."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

AUDIO_PATH = Path(r"c:\Users\XXM\Desktop\起诉材料\2026年05月22日 叶明舟师兄讲三个鼻炎音频.m4a")
OUT_DIR = Path(r"c:\Users\XXM\Desktop")
OUT_BASE = OUT_DIR / "2026年05月22日 叶明舟师兄讲三个鼻炎音频_转写"
WAV_PATH = OUT_DIR / "_tmp_yemingzhou_16k.wav"
CHUNK_DIR = OUT_DIR / "_tmp_yemingzhou_chunks"
CHUNK_SECONDS = 600  # 10 min per chunk for stable API calls

ENV_PATH = Path(r"D:\AI\demo\ai-medical-consultant\backend\.env")


def load_api_key() -> str:
    if os.environ.get("DASHSCOPE_API_KEY"):
        return os.environ["DASHSCOPE_API_KEY"]
    if ENV_PATH.is_file():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("未找到 DASHSCOPE/OPENAI API Key")


def ms_to_ts(ms: int) -> str:
    total = max(0, int(ms)) // 1000
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def run_ffmpeg(args: list[str]) -> None:
    env_path = os.environ.get("Path", "")
    for base in [
        r"C:\Program Files\ffmpeg\bin",
        r"C:\ffmpeg\bin",
    ]:
        if Path(base, "ffmpeg.exe").exists() and base not in env_path:
            os.environ["Path"] = base + ";" + env_path
            break
    proc = subprocess.run(
        ["ffmpeg", *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "ffmpeg failed")[-2000:])


def ensure_wav() -> Path:
    if WAV_PATH.exists() and WAV_PATH.stat().st_size > 0:
        return WAV_PATH
    print("正在转换音频为 16kHz mono wav ...")
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(AUDIO_PATH),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(WAV_PATH),
        ]
    )
    return WAV_PATH


def split_wav(wav: Path) -> list[Path]:
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    pattern = CHUNK_DIR / "part_%03d.wav"
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(wav),
            "-f",
            "segment",
            "-segment_time",
            str(CHUNK_SECONDS),
            "-reset_timestamps",
            "1",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(pattern),
        ]
    )
    parts = sorted(CHUNK_DIR.glob("part_*.wav"))
    if not parts:
        raise RuntimeError("音频分片失败")
    print(f"已分片 {len(parts)} 段，每段约 {CHUNK_SECONDS // 60} 分钟")
    return parts


def transcribe_chunk(file_path: Path, offset_ms: int, api_key: str) -> list[dict]:
    from dashscope.audio.asr import Recognition

    class _Cb:
        def on_open(self):
            pass

        def on_complete(self):
            pass

        def on_error(self, result):
            pass

        def on_close(self):
            pass

        def on_event(self, result):
            pass

    rec = Recognition(
        model="paraformer-realtime-v2",
        callback=_Cb(),
        format="wav",
        sample_rate=16000,
    )
    os.environ["DASHSCOPE_API_KEY"] = api_key
    import dashscope

    dashscope.api_key = api_key

    result = rec.call(
        str(file_path),
        timestamp_alignment_enabled=True,
        disfluency_removal_enabled=False,
    )
    if result.status_code != 200:
        raise RuntimeError(f"转写失败 {file_path.name}: {result.message}")

    sentences = result.get_sentence()
    if isinstance(sentences, dict):
        sentences = [sentences]

    out: list[dict] = []
    for s in sentences or []:
        if not s or not s.get("text"):
            continue
        begin = int(s.get("begin_time") or 0) + offset_ms
        end = int(s.get("end_time") or begin) + offset_ms
        out.append({"begin": begin, "end": end, "text": s["text"].strip()})
    return out


def try_batch_transcription(api_key: str) -> list[dict] | None:
    """Try async file transcription if file:// is supported."""
    from http import HTTPStatus

    from dashscope.audio.asr import Transcription

    import dashscope

    dashscope.api_key = api_key
    file_url = AUDIO_PATH.resolve().as_uri()
    print(f"尝试批量转写: {file_url}")
    try:
        task = Transcription.async_call(
            model="paraformer-v2",
            file_urls=[file_url],
            language_hints=["zh"],
            timestamp_alignment_enabled=True,
        )
        if task.status_code != HTTPStatus.OK:
            print("批量转写不可用:", task.message)
            return None
        resp = Transcription.wait(task=task.output.task_id)
        if resp.status_code != HTTPStatus.OK:
            print("批量转写等待失败:", resp.message)
            return None
        results = resp.output.results
        if not results:
            return None
        url = results[0].get("transcription_url")
        if not url:
            return None
        raw = urllib.request.urlopen(url, timeout=120).read().decode("utf-8")
        data = json.loads(raw)
        transcripts = data.get("transcripts") or data.get("Transcripts") or []
        if not transcripts:
            return None
        sentences: list[dict] = []
        for item in transcripts:
            for s in item.get("sentences") or []:
                sentences.append(
                    {
                        "begin": int(s.get("begin_time", 0)),
                        "end": int(s.get("end_time", 0)),
                        "text": (s.get("text") or "").strip(),
                    }
                )
        return sentences or None
    except Exception as e:
        print("批量转写异常，改分片模式:", e)
        return None


def merge_paragraphs(sentences: list[dict], gap_ms: int = 1500) -> list[dict]:
    if not sentences:
        return []
    merged: list[dict] = []
    cur = dict(sentences[0])
    for s in sentences[1:]:
        if s["begin"] - cur["end"] <= gap_ms:
            cur["end"] = max(cur["end"], s["end"])
            cur["text"] = cur["text"] + s["text"]
        else:
            merged.append(cur)
            cur = dict(s)
    merged.append(cur)
    return merged


def format_outputs(sentences: list[dict]) -> tuple[str, str, str]:
    lines_ts: list[str] = []
    lines_srt: list[str] = []
    plain_parts: list[str] = []

    for i, s in enumerate(sentences, 1):
        b, e, text = s["begin"], s["end"], s["text"]
        if not text:
            continue
        lines_ts.append(f"[{ms_to_ts(b)} - {ms_to_ts(e)}] {text}")
        plain_parts.append(text)

        def srt_time(ms: int) -> str:
            ms = max(0, int(ms))
            h, rem = divmod(ms, 3600000)
            m, rem = divmod(rem, 60000)
            sec, milli = divmod(rem, 1000)
            return f"{h:02d}:{m:02d}:{sec:02d},{milli:03d}"

        lines_srt.extend(
            [
                str(i),
                f"{srt_time(b)} --> {srt_time(e)}",
                text,
                "",
            ]
        )

    paragraphs = merge_paragraphs(sentences, gap_ms=2000)
    lines_para: list[str] = []
    for p in paragraphs:
        lines_para.append(f"[{ms_to_ts(p['begin'])} - {ms_to_ts(p['end'])}]")
        lines_para.append(p["text"])
        lines_para.append("")

    md = [
        "# 2026年05月22日 叶明舟师兄讲三个鼻炎音频 · 语音转写",
        "",
        f"- 源文件：`{AUDIO_PATH.name}`",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 分段正文（带时间戳）",
        "",
        *lines_para,
        "",
        "## 句级时间戳",
        "",
        *lines_ts,
    ]
    return "\n".join(md), "\n".join(lines_ts), "\n".join(lines_srt)


def main() -> None:
    if not AUDIO_PATH.is_file():
        raise FileNotFoundError(AUDIO_PATH)

    api_key = load_api_key()
    sentences = try_batch_transcription(api_key)

    if not sentences:
        wav = ensure_wav()
        parts = split_wav(wav)
        sentences = []
        for idx, part in enumerate(parts):
            offset_ms = idx * CHUNK_SECONDS * 1000
            print(f"转写分片 {idx + 1}/{len(parts)}: {part.name}")
            chunk_sents = transcribe_chunk(part, offset_ms, api_key)
            sentences.extend(chunk_sents)
            print(f"  获得 {len(chunk_sents)} 句")

    sentences = [s for s in sentences if s.get("text")]
    sentences.sort(key=lambda x: x["begin"])
    if not sentences:
        raise RuntimeError("未识别到任何文本")

    md, txt, srt = format_outputs(sentences)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUT_BASE.with_suffix(".md")
    txt_path = OUT_BASE.with_suffix(".txt")
    srt_path = OUT_BASE.with_suffix(".srt")
    md_path.write_text(md, encoding="utf-8")
    txt_path.write_text(txt, encoding="utf-8")
    srt_path.write_text(srt, encoding="utf-8")

    print("完成!")
    print("Markdown:", md_path)
    print("纯文本:", txt_path)
    print("SRT字幕:", srt_path)
    print("总句数:", len(sentences))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise

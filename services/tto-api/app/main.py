import os
import re
import logging
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="TTO API - Thai Token Optimizer", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

TTO_CLI_PATH = os.getenv("TTO_CLI_PATH", "")
MAX_INPUT_LENGTH = int(os.getenv("TTO_MAX_INPUT_LENGTH", "32000"))


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\t', '  ', text)
    text = re.sub(r' {3,}', '  ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def _preserve_blocks(text: str) -> tuple[str, list]:
    blocks = []
    placeholder_base = "___BLOCK_{i}___"

    def replace_block(m):
        idx = len(blocks)
        blocks.append(m.group(0))
        return placeholder_base.format(i=idx)

    protected = re.sub(r'```[\s\S]*?```', replace_block, text)
    protected = re.sub(r'`[^`]+`', replace_block, protected)
    return protected, blocks


def _restore_blocks(text: str, blocks: list) -> str:
    for i, block in enumerate(blocks):
        text = text.replace(f"___BLOCK_{i}___", block)
    return text


def _trim_long_lines(text: str, max_len: int = 500) -> str:
    lines = text.split('\n')
    result = []
    for line in lines:
        if len(line) > max_len and not line.startswith('```'):
            result.append(line[:max_len] + ' ...[truncated]')
        else:
            result.append(line)
    return '\n'.join(result)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _fallback_optimize(text: str) -> dict:
    original_length = len(text)

    protected, blocks = _preserve_blocks(text)
    normalized = _normalize_whitespace(protected)
    trimmed = _trim_long_lines(normalized)
    restored = _restore_blocks(trimmed, blocks)

    optimized_length = len(restored)
    reduction = round((1 - optimized_length / max(1, original_length)) * 100, 1)

    warnings = []
    if original_length > MAX_INPUT_LENGTH:
        warnings.append(f"Input exceeds {MAX_INPUT_LENGTH} chars — consider splitting")
    if reduction > 30:
        warnings.append("Significant reduction — verify no important content was trimmed")

    return {
        "original_length": original_length,
        "optimized_length": optimized_length,
        "estimated_reduction_percent": reduction,
        "original_tokens": _estimate_tokens(text),
        "optimized_tokens": _estimate_tokens(restored),
        "optimized_text": restored,
        "warnings": warnings,
    }


class OptimizeRequest(BaseModel):
    text: str
    preserve_commands: bool = True
    preserve_thai: bool = True


class NormalizeRequest(BaseModel):
    text: str


class SummarizeRequest(BaseModel):
    text: str
    max_length: Optional[int] = 2000
    focus: Optional[str] = None


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "tto-api",
        "version": "0.1.0",
        "tto_cli": "available" if TTO_CLI_PATH else "fallback",
    }


@app.post("/optimize")
async def optimize(req: OptimizeRequest):
    if not req.text:
        return {"optimized_text": "", "original_length": 0, "optimized_length": 0,
                "estimated_reduction_percent": 0, "warnings": []}

    if TTO_CLI_PATH:
        logger.info("TTO CLI available at %s — adapter not yet implemented, using fallback", TTO_CLI_PATH)

    result = _fallback_optimize(req.text)
    logger.info("Optimized: %d -> %d chars (%.1f%% reduction)",
                result["original_length"], result["optimized_length"],
                result["estimated_reduction_percent"])
    return result


@app.post("/normalize")
async def normalize(req: NormalizeRequest):
    if not req.text:
        return {"normalized_text": "", "original_length": 0, "normalized_length": 0}

    original_length = len(req.text)
    protected, blocks = _preserve_blocks(req.text)
    normalized = _normalize_whitespace(protected)
    restored = _restore_blocks(normalized, blocks)

    return {
        "original_length": original_length,
        "normalized_length": len(restored),
        "normalized_text": restored,
    }


@app.post("/summarize-context")
async def summarize_context(req: SummarizeRequest):
    if not req.text:
        return {"summary": "", "original_length": 0}

    result = _fallback_optimize(req.text)
    text = result["optimized_text"]

    if len(text) > req.max_length:
        text = text[: req.max_length] + "\n...[context truncated for token efficiency]"

    return {
        "summary": text,
        "original_length": result["original_length"],
        "summary_length": len(text),
        "estimated_reduction_percent": result["estimated_reduction_percent"],
        "warnings": result["warnings"],
    }

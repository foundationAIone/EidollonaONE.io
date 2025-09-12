"""Adapters for populating ChainMetricsEngine from common RPC / API responses.

These are intentionally light-weight and avoid external dependencies. Each adapter
returns domain dataclasses (`BlockSample`, `MempoolSample`, `NodeHealth`) suitable
for ingestion via `ChainMetricsEngine`.

Usage Example (EVM):
    block_json = eth_getBlockByNumber(...)
    block_sample = evm_block_from_rpc(block_json, prev_timestamp=prev_ts)
    engine.add_block(block_sample)

Usage Example (Bitcoin):
    mem_info = getmempoolinfo()
    fee_hist  = fetch_fee_histogram()  # user-defined
    mp_sample = utxo_mempool_from_rpc(mem_info, fee_hist)
    engine.add_mempool(mp_sample)
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
import time

from .chain_metrics import (
    BlockSample,
    MempoolSample,
    NodeHealth,
)

# ---------------------------------------------------------------------------
# EVM / Ethereum-like
# ---------------------------------------------------------------------------


def _hex_to_int(x: Optional[str]) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x, 16)
    except Exception:
        return None


def evm_block_from_rpc(
    block: Dict[str, Any], prev_timestamp: Optional[float]
) -> BlockSample:
    """Convert eth_getBlockByNumber JSON (with transactions omitted) into BlockSample.

    Expects keys: number, timestamp, gasUsed, gasLimit, baseFeePerGas (post London),
    transactions (list) or tx count via `len(block['transactions'])` when tx objects provided.
    """
    ts = _hex_to_int(block.get("timestamp")) or int(time.time())
    height = _hex_to_int(block.get("number")) or 0
    gas_used = float(_hex_to_int(block.get("gasUsed")) or 0)
    gas_limit = float(_hex_to_int(block.get("gasLimit")) or 0)
    base_fee_raw = block.get("baseFeePerGas")
    base_fee = (
        float(_hex_to_int(base_fee_raw)) / 1e9 if base_fee_raw is not None else None
    )  # gwei
    txs_obj = block.get("transactions") or []
    tx_count = (
        len(txs_obj)
        if isinstance(txs_obj, list)
        else int(block.get("transactionCount", 0))
    )

    block_time = float(ts - prev_timestamp) if prev_timestamp else 0.0

    return BlockSample(
        height=height,
        timestamp=float(ts),
        block_time_sec=block_time,
        tx_count=tx_count,
        gas_used=gas_used,
        gas_limit=gas_limit,
        base_fee=base_fee,
        priority_fee_median=None,  # can be filled if separate distribution known
    )


def evm_mempool_from_fee_hist(
    fee_hist: List[Tuple[float, int]], gas_queued: Optional[float], tx_count: int
) -> MempoolSample:
    return MempoolSample(
        timestamp=time.time(),
        tx_count=tx_count,
        gas_queued=gas_queued,
        fee_histogram=fee_hist,
    )


# ---------------------------------------------------------------------------
# UTXO / Bitcoin-like
# ---------------------------------------------------------------------------


def utxo_block_from_rpc(
    header: Dict[str, Any], tx_count: int, prev_timestamp: Optional[float]
) -> BlockSample:
    ts = header.get("time") or int(time.time())
    height = header.get("height") or 0
    weight = header.get("weight")
    size = header.get("size")
    block_time = float(ts - prev_timestamp) if prev_timestamp else 0.0

    return BlockSample(
        height=int(height),
        timestamp=float(ts),
        block_time_sec=block_time,
        tx_count=int(tx_count),
        size_bytes=int(size) if size is not None else None,
        weight_wu=int(weight) if weight is not None else None,
    )


def utxo_mempool_from_rpc(
    mempool_info: Dict[str, Any], fee_hist: List[Tuple[float, int]]
) -> MempoolSample:
    # mempool_info typical keys: size (tx count), bytes, usage, etc.
    return MempoolSample(
        timestamp=time.time(),
        tx_count=int(mempool_info.get("size", 0)),
        bytes_total=int(mempool_info.get("bytes", 0)),
        vsize_bytes_total=int(mempool_info.get("bytes", 0)),  # proxy
        fee_histogram=fee_hist,
    )


# ---------------------------------------------------------------------------
# Node health helpers (generic)
# ---------------------------------------------------------------------------


def node_health_from_stats(stats: Dict[str, Any]) -> NodeHealth:
    return NodeHealth(
        timestamp=time.time(),
        peers=int(stats.get("peers", 0)),
        sync_lag_blocks=int(stats.get("sync_lag_blocks", 0)),
        cpu_util=float(stats.get("cpu_util", 0.0)),
        mem_util=float(stats.get("mem_util", 0.0)),
        disk_avail_gb=float(stats.get("disk_avail_gb", 0.0)),
        recent_errors_5m=int(stats.get("recent_errors_5m", 0)),
    )


__all__ = [
    "evm_block_from_rpc",
    "evm_mempool_from_fee_hist",
    "utxo_block_from_rpc",
    "utxo_mempool_from_rpc",
    "node_health_from_stats",
]

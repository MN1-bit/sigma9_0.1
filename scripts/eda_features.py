"""
R-4 EDA: Daygainer vs Control 차별화 분석

D-1 + M-n 피처 결합 후 라벨별 피처 분포 비교.

Usage:
    python scripts/eda_features.py
"""

import pandas as pd

# Load merged features
df = pd.read_parquet("scripts/merged_features.parquet")

print("=" * 70)
print("R-4 EDA: Daygainer vs Control 차별화 분석")
print("=" * 70)

# 라벨별 그룹
daygainer = df[df["label"] == "daygainer"]
control_normal = df[df["label"] == "control_normal"]
control_failed = df[df["label"] == "control_failed_pump"]

print("\n샘플 수:")
print(f"  Daygainer: {len(daygainer)}")
print(f"  Control Normal: {len(control_normal)}")
print(f"  Control Failed Pump: {len(control_failed)}")

# 주요 피처 비교
features_to_compare = [
    # D-1 피처
    ("rvol_20d", "D-1 RVOL (20일 평균 대비)"),
    ("price_vs_20ma", "D-1 20MA 대비 %"),
    ("atr_pct", "D-1 ATR%"),
    ("volume_trend_5d", "D-1 거래량 추세 5일"),
    # M-n 피처 (15분 윈도우)
    ("vol_zscore_max_15m", "M-n 거래량 Z-score 최대(15m)"),
    ("vol_accel_15m", "M-n 거래량 가속(15m)"),
    ("rvol_spike_count_15m", "M-n RVOL 스파이크 횟수(15m)"),
    ("price_momentum_15m", "M-n 가격 모멘텀(15m)"),
    # Premarket
    ("premarket_volume", "프리마켓 거래량"),
    ("premarket_change", "프리마켓 변화율%"),
]

print("\n" + "=" * 70)
print("피처별 평균 비교")
print("=" * 70)

results = []

for feat, desc in features_to_compare:
    if feat not in df.columns:
        continue
    
    dg_mean = daygainer[feat].mean()
    n_mean = control_normal[feat].mean()
    f_mean = control_failed[feat].mean()
    
    # 차이 계산 (Daygainer vs Normal)
    if pd.notna(dg_mean) and pd.notna(n_mean) and n_mean != 0:
        diff_pct = ((dg_mean / n_mean) - 1) * 100
    else:
        diff_pct = None
    
    results.append({
        "Feature": feat,
        "Daygainer": dg_mean,
        "Normal": n_mean,
        "Failed": f_mean,
        "DG_vs_N_%": diff_pct,
    })
    
    dg_str = f"{dg_mean:.2f}" if pd.notna(dg_mean) else "NaN"
    n_str = f"{n_mean:.2f}" if pd.notna(n_mean) else "NaN"
    f_str = f"{f_mean:.2f}" if pd.notna(f_mean) else "NaN"
    diff_str = f"{diff_pct:+.0f}%" if diff_pct is not None else "N/A"
    
    print(f"\n{desc}:")
    print(f"  Daygainer: {dg_str}")
    print(f"  Normal:    {n_str}")
    print(f"  Failed:    {f_str}")
    print(f"  DG vs Normal: {diff_str}")

# T0 탐지율 비교
print("\n" + "=" * 70)
print("T0 탐지율 비교")
print("=" * 70)

for method in ["t0_threshold", "t0_accel"]:
    dg_rate = daygainer[method].notna().mean() * 100
    n_rate = control_normal[method].notna().mean() * 100
    f_rate = control_failed[method].notna().mean() * 100
    print(f"\n{method}:")
    print(f"  Daygainer: {dg_rate:.0f}%")
    print(f"  Normal:    {n_rate:.0f}%")
    print(f"  Failed:    {f_rate:.0f}%")

# Premarket 활동 비교
print("\n" + "=" * 70)
print("Premarket 활동 비교")
print("=" * 70)

for label, grp in [("Daygainer", daygainer), ("Normal", control_normal), ("Failed", control_failed)]:
    has_pm = grp["has_premarket"].sum()
    total = len(grp)
    pct = has_pm / total * 100 if total > 0 else 0
    print(f"{label}: {has_pm}/{total} ({pct:.0f}%)")

# 결과 저장
results_df = pd.DataFrame(results)
results_df.to_csv("scripts/eda_feature_comparison.csv", index=False)
print("\n결과 저장: scripts/eda_feature_comparison.csv")

print("\n" + "=" * 70)
print("완료")
print("=" * 70)

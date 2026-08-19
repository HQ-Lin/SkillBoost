#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

        
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

      
output_dir = Path("analysis")
output_dir.mkdir(exist_ok=True)

                                                         
      
                                                         

               
rounds = [0, 1, 2, 3]
livemath_bestofn = []                    
livemath_single = []              

               
alf_bestofn = []
alf_single = []

                                                         
                      
                                                         
fig, ax = plt.subplots(figsize=(10, 6))

      
ax.plot(rounds, livemath_bestofn, 'o-', 
        label='Best-of-N (N=4)', 
        linewidth=3, markersize=10, color='#2ecc71',
        markeredgecolor='white', markeredgewidth=2)

ax.plot(rounds, livemath_single, 's--', 
        label='Single-thread (N=1)', 
        linewidth=2.5, markersize=9, color='#e74c3c',
        markeredgecolor='white', markeredgewidth=2)

         
ax.text(0.5, 45, '3.0× faster\nconvergence', 
        fontsize=14, fontweight='bold', color='#34495e',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3))

       
ax.set_xlabel('Evolution Rounds', fontsize=13, fontweight='bold')
ax.set_ylabel('Accuracy (%)', fontsize=13, fontweight='bold')
ax.set_title('LiveMath: Best-of-N vs Single-thread Convergence', 
             fontsize=15, fontweight='bold', pad=15)

ax.legend(fontsize=12, loc='lower right', framealpha=0.9)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xticks(rounds)
ax.set_xticklabels([f'v{i}' for i in rounds])
ax.set_xlim(-0.2, 3.2)
ax.set_ylim(15, 80)

         
ax.axhline(y=22.9, color='gray', linestyle=':', alpha=0.5, label='Baseline (v0)')

plt.tight_layout()
plt.savefig(output_dir / 'figure_bestofn_convergence_livemath.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'figure_bestofn_convergence_livemath.png', dpi=300, bbox_inches='tight')
print(f"LiveMath convergence curve saved: {output_dir / 'figure_bestofn_convergence_livemath.pdf'}")
plt.close()

                                                         
                      
                                                         
fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(rounds, alf_bestofn, 'o-', 
        label='Best-of-N (N=4)', 
        linewidth=3, markersize=10, color='#2ecc71',
        markeredgecolor='white', markeredgewidth=2)

ax.plot(rounds, alf_single, 's--', 
        label='Single-thread (N=1)', 
        linewidth=2.5, markersize=9, color='#e74c3c',
        markeredgecolor='white', markeredgewidth=2)

ax.set_xlabel('Evolution Rounds', fontsize=13, fontweight='bold')
ax.set_ylabel('Pass Rate (%)', fontsize=13, fontweight='bold')
ax.set_title('ALFWorld: Best-of-N vs Single-thread Convergence', 
             fontsize=15, fontweight='bold', pad=15)

ax.legend(fontsize=12, loc='lower right', framealpha=0.9)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xticks(rounds)
ax.set_xticklabels([f'v{i}' for i in rounds])
ax.set_xlim(-0.2, 3.2)
ax.set_ylim(75, 100)

plt.tight_layout()
plt.savefig(output_dir / 'figure_bestofn_convergence_alfworld.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'figure_bestofn_convergence_alfworld.png', dpi=300, bbox_inches='tight')
print(f"ALFWorld convergence curve saved: {output_dir / 'figure_bestofn_convergence_alfworld.pdf'}")
plt.close()

                                                         
                 
                                                         
fig, ax = plt.subplots(figsize=(8, 5))

datasets = ['LiveMath\n(Low Baseline)', 'ALFWorld\n(High Baseline)']
speedups = []
colors = ['#2ecc71', '#3498db']

bars = ax.bar(datasets, speedups, color=colors, width=0.5, edgecolor='white', linewidth=2)

        
for bar, speedup in zip(bars, speedups):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
            f'{speedup}×',
            ha='center', va='bottom', fontsize=14, fontweight='bold')

ax.set_ylabel('Convergence Speedup', fontsize=13, fontweight='bold')
ax.set_title('Best-of-N vs Single-thread: Expected Speed Ratio (ESR)', 
             fontsize=14, fontweight='bold', pad=15)
ax.set_ylim(0, 4)
ax.grid(True, alpha=0.3, linestyle='--', axis='y')

        
ax.text(0.5, 3.5, 'ESR = (Single-thread Rounds / Best-of-N Rounds) × Success Rate',
        ha='center', fontsize=10, style='italic', color='gray')

plt.tight_layout()
plt.savefig(output_dir / 'figure_bestofn_speedup_comparison.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'figure_bestofn_speedup_comparison.png', dpi=300, bbox_inches='tight')
print(f"speedup comparison figure saved: {output_dir / 'figure_bestofn_speedup_comparison.pdf'}")
plt.close()

                                                         
                   
                                                         
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

                   
ax = axes[0, 0]
ax.plot(rounds, livemath_bestofn, 'o-', label='Best-of-N (N=4)', 
        linewidth=2.5, markersize=8, color='#2ecc71')
ax.plot(rounds, livemath_single, 's--', label='Single-thread (N=1)', 
        linewidth=2, markersize=7, color='#e74c3c')
ax.set_title('LiveMath Convergence', fontsize=12, fontweight='bold')
ax.set_xlabel('Rounds')
ax.set_ylabel('Accuracy (%)')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
ax.set_xticks(rounds)
ax.set_xticklabels([f'v{i}' for i in rounds])

                   
ax = axes[0, 1]
ax.plot(rounds, alf_bestofn, 'o-', label='Best-of-N (N=4)', 
        linewidth=2.5, markersize=8, color='#2ecc71')
ax.plot(rounds, alf_single, 's--', label='Single-thread (N=1)', 
        linewidth=2, markersize=7, color='#e74c3c')
ax.set_title('ALFWorld Convergence', fontsize=12, fontweight='bold')
ax.set_xlabel('Rounds')
ax.set_ylabel('Pass Rate (%)')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
ax.set_xticks(rounds)
ax.set_xticklabels([f'v{i}' for i in rounds])

            
ax = axes[1, 0]
bars = ax.bar(datasets, speedups, color=colors, width=0.5, edgecolor='white')
for bar, speedup in zip(bars, speedups):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.08,
            f'{speedup}×', ha='center', va='bottom', fontsize=12, fontweight='bold')
ax.set_title('Convergence Speedup', fontsize=12, fontweight='bold')
ax.set_ylabel('ESR')
ax.set_ylim(0, 4)
ax.grid(True, alpha=0.3, axis='y')

                 
ax = axes[1, 1]
baselines = []
deltas = []
scatter = ax.scatter(baselines, deltas, s=200, c=colors, edgecolors='white', linewidth=2, zorder=5)
for i, (x, y) in enumerate(zip(baselines, deltas)):
    ax.annotate(f'{y:.1f}pp', (x, y), textcoords="offset points", 
                xytext=(10, 5), fontsize=11, fontweight='bold')
ax.set_title('Single-Round Improvement vs Baseline', fontsize=12, fontweight='bold')
ax.set_xlabel('Baseline Accuracy (%)')
ax.set_ylabel('Improvement Δ (pp)')
ax.grid(True, alpha=0.3)
ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)

plt.suptitle('Best-of-N Group Search: Comprehensive Analysis', 
             fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(output_dir / 'figure_bestofn_comprehensive_analysis.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'figure_bestofn_comprehensive_analysis.png', dpi=300, bbox_inches='tight')
print(f"comprehensive analysis figure saved: {output_dir / 'figure_bestofn_comprehensive_analysis.pdf'}")
plt.close()

print("\n" + "="*70)
print("all figures generated！")
print("="*70)
print(f"\n output directory: {output_dir.absolute()}")
print(f"\n generated figures:")
print(f"  1. figure_bestofn_convergence_livemath.pdf/png")
print(f"  2. figure_bestofn_convergence_alfworld.pdf/png")
print(f"  3. figure_bestofn_speedup_comparison.pdf/png")
print(f"  4. figure_bestofn_comprehensive_analysis.pdf/png")

#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

                                                         
      
                                                         
datasets = ['BFCL-v4', 'ALFWorld', 'LiveMath', 'SpreadsheetBench']
structured = []
scrambled = []

                                       
                                       
                                                         
                                              
                                                          
                                                     
                                                         
diff = np.array(scrambled) - np.array(structured)
                                                             
t_stat, p_two = stats.ttest_rel(scrambled, structured)
                                               
                                                              
p_one = p_two / 2 if t_stat < 0 else 1 - p_two / 2

mean_diff = np.mean(diff)
std_diff = np.std(diff, ddof=1)

print(f"{'='*60}")
print(f"Statistical Test: Paired One-Tailed t-test")
print(f"{'='*60}")
print(f"H0: Scrambled performance >= Structured performance (no degradation)")
print(f"H1: Scrambled performance < Structured performance (degradation exists)")
print(f"")
print(f"Mean difference (scrambled - structured): {mean_diff:+.2f}%")
print(f"Std of differences: {std_diff:.2f}%")
print(f"t-statistic: {t_stat:.4f}")
print(f"One-tailed p-value: {p_one:.4f}")
print(f"")
if p_one > 0.05:
    print(f"Result: p = {p_one:.4f} > 0.05 → FAIL to reject H0")
    print(f"Conclusion: Cannot conclude that scrambled is worse than structured.")
    print(f"The performance drop is NOT statistically significant.")
else:
    print(f"Result: p = {p_one:.4f} < 0.05 → Reject H0")
    print(f"Conclusion: Scrambled is significantly worse than structured.")

                                                         
      
                                                         
fig, ax = plt.subplots(figsize=(8, 5))

x = np.arange(len(datasets))
width = 0.32

                                                        
color_structured = '#5B9BD5'              
color_scrambled  = '#BFBFBF'               

bars1 = ax.bar(x - width/2, structured, width, label='Structured',
               color=color_structured, edgecolor='none', linewidth=0.8,
               zorder=3)
bars2 = ax.bar(x + width/2, scrambled, width, label='Scrambled',
               color=color_scrambled, edgecolor='none', linewidth=0.8,
               zorder=3)

                      
for bar, val in zip(bars1, structured):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.2,
            f'{val:.1f}', ha='center', va='bottom', fontsize=10,
            fontweight='semibold', color=color_structured)
for bar, val in zip(bars2, scrambled):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.2,
            f'{val:.1f}', ha='center', va='bottom', fontsize=10,
            fontweight='semibold', color='#555555')

         
ax.set_xticks(x)
ax.set_xticklabels(datasets, fontsize=12, fontweight='medium')
ax.set_ylabel('Performance', fontsize=12, fontweight='medium')
ax.set_ylim(0, 108)
ax.set_yticks(np.arange(0, 110, 20))
ax.tick_params(axis='y', labelsize=11)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(0.8)
ax.spines['bottom'].set_linewidth(0.8)
ax.yaxis.grid(True, linestyle='--', alpha=0.25, linewidth=0.5, zorder=0)
ax.set_axisbelow(True)

        
ax.legend(loc='upper right', fontsize=11, framealpha=0, edgecolor='none')

plt.tight_layout(pad=1.5)

      
out_pdf = 'figure_structured_vs_scrambled.pdf'
out_png = 'figure_structured_vs_scrambled.png'
fig.savefig(out_pdf, dpi=300, bbox_inches='tight', transparent=False)
fig.savefig(out_png, dpi=300, bbox_inches='tight', transparent=False)
print(f"\nSaved: {out_pdf}, {out_png}")
plt.close()

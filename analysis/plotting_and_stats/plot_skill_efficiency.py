#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

                    
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 11
matplotlib.rcParams['axes.linewidth'] = 1.2
matplotlib.rcParams['axes.labelweight'] = 'bold'
matplotlib.rcParams['pdf.fonttype'] = 42                         
matplotlib.rcParams['ps.fonttype'] = 42

                         
output_dir = Path("analysis")
output_dir.mkdir(exist_ok=True)

                                                         
                  
                                                         

                                                                
COLOR_NO_SKILL = '#7F8C8D'                 
COLOR_SKILL = '#5DADE2'                    
COLOR_ALF = '#E74C3C'                     
COLOR_SHEET = '#3498DB'                      
COLOR_BFCL = '#9B59B6'                       

benchmarks = ['ALFWorld', 'SpreadSheet', 'BFCL']                                                  

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

                                         
x = np.arange(len(benchmarks))
width = 0.35

bars1 = axes[0].bar(x - width/2, no_skill_turns, width, label='Baseline', 
                     color=COLOR_NO_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)
bars2 = axes[0].bar(x + width/2, best_skill_turns, width, label='SkillBoost', 
                     color=COLOR_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)

                  
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontweight='bold', fontsize=10)

axes[0].set_ylabel('Average Interaction Count', fontsize=12, fontweight='bold')
axes[0].set_title('(a)', fontsize=13, fontweight='bold', pad=12)
axes[0].set_xticks(x)
axes[0].set_xticklabels(benchmarks, fontsize=11)
axes[0].legend(fontsize=10, framealpha=0.9)
axes[0].grid(axis='y', alpha=0.3, linestyle='--')
axes[0].set_ylim(0, max(no_skill_turns) * 1.25)

                                             
bars = axes[1].bar(x, reduction_pct, color='gray', edgecolor='black', linewidth=0.5, alpha=0.85)

                       
for bar, val in zip(bars, reduction_pct):
    if val < -25:
        color_bar = COLOR_ALF               
    elif val < -15:
        color_bar = COLOR_BFCL                          
    else:
        color_bar = COLOR_SHEET                     
    bar.set_color(color_bar)
    bar.set_edgecolor('black')
    bar.set_linewidth(0.5)
    bar.set_alpha(0.85)
    
    axes[1].text(bar.get_x() + bar.get_width()/2., val,
                f'{val:.1f}%',
                ha='center', va='bottom',
                fontweight='bold', fontsize=11, color='black')

axes[1].axhline(y=0, color='black', linewidth=1.0)
axes[1].set_ylabel('Interaction Reduction (%)', fontsize=12, fontweight='bold')
axes[1].set_title('(b)', fontsize=13, fontweight='bold', pad=12)
axes[1].set_xticks(x)
axes[1].set_xticklabels(benchmarks, fontsize=11)
axes[1].grid(axis='y', alpha=0.3, linestyle='--')
axes[1].set_ylim(min(reduction_pct) * 1.35, 5)

                                 
width2 = 0.35
bars3 = axes[2].bar(x - width2/2, no_skill_acc, width2, label='Baseline', 
                     color=COLOR_NO_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)
bars4 = axes[2].bar(x + width2/2, best_skill_acc, width2, label='SkillBoost', 
                     color=COLOR_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)

for bars in [bars3, bars4]:
    for bar in bars:
        height = bar.get_height()
        axes[2].text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontweight='bold', fontsize=10)

axes[2].set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
axes[2].set_title('(c)', fontsize=13, fontweight='bold', pad=12)
axes[2].set_xticks(x)
axes[2].set_xticklabels(benchmarks, fontsize=11)
axes[2].legend(fontsize=10, framealpha=0.9)
axes[2].grid(axis='y', alpha=0.3, linestyle='--')
axes[2].set_ylim(0, 110)

                      
plt.tight_layout()
plt.savefig(output_dir / 'skill_efficiency_comparison.png', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'skill_efficiency_comparison.pdf', bbox_inches='tight')
plt.close()

print(f"Combined figure saved: {output_dir / 'skill_efficiency_comparison.pdf'}")

                                             
fig_a, ax_a = plt.subplots(figsize=(6, 4))
bars_a1 = ax_a.bar(x - width/2, no_skill_turns, width, label='Baseline', 
                    color=COLOR_NO_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)
bars_a2 = ax_a.bar(x + width/2, best_skill_turns, width, label='SkillBoost', 
                    color=COLOR_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)
for bars in [bars_a1, bars_a2]:
    for bar in bars:
        height = bar.get_height()
        ax_a.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.1f}',
                 ha='center', va='bottom', fontweight='bold', fontsize=10)
ax_a.set_ylabel('Average Interaction Count', fontsize=12, fontweight='bold')
ax_a.set_xticks(x)
ax_a.set_xticklabels(benchmarks, fontsize=11)
ax_a.legend(fontsize=10, framealpha=0.9)
ax_a.grid(axis='y', alpha=0.3, linestyle='--')
ax_a.set_ylim(0, max(no_skill_turns) * 1.25)
plt.tight_layout()
plt.savefig(output_dir / 'figure_interaction_count.pdf', bbox_inches='tight')
plt.close()
print(f"Subfigure (a) saved: {output_dir / 'figure_interaction_count.pdf'}")

fig_b, ax_b = plt.subplots(figsize=(6, 4))
bars_b = ax_b.bar(x, reduction_pct, color='gray', edgecolor='black', linewidth=0.5, alpha=0.85)
for bar, val in zip(bars_b, reduction_pct):
    if val < -25:
        color_bar = COLOR_ALF
    elif val < -15:
        color_bar = COLOR_BFCL
    else:
        color_bar = COLOR_SHEET
    bar.set_color(color_bar)
    bar.set_edgecolor('black')
    bar.set_linewidth(0.5)
    bar.set_alpha(0.85)
    ax_b.text(bar.get_x() + bar.get_width()/2., val,
             f'{val:.1f}%',
             ha='center', va='bottom',
             fontweight='bold', fontsize=11, color='black')
ax_b.axhline(y=0, color='black', linewidth=1.0)
ax_b.set_ylabel('Interaction Reduction (%)', fontsize=12, fontweight='bold')
ax_b.set_xticks(x)
ax_b.set_xticklabels(benchmarks, fontsize=11)
ax_b.grid(axis='y', alpha=0.3, linestyle='--')
ax_b.set_ylim(min(reduction_pct) * 1.35, 5)
plt.tight_layout()
plt.savefig(output_dir / 'figure_efficiency_gain.pdf', bbox_inches='tight')
plt.close()
print(f"Subfigure (b) saved: {output_dir / 'figure_efficiency_gain.pdf'}")

fig_c, ax_c = plt.subplots(figsize=(6, 4))
bars_c1 = ax_c.bar(x - width2/2, no_skill_acc, width2, label='Baseline', 
                    color=COLOR_NO_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)
bars_c2 = ax_c.bar(x + width2/2, best_skill_acc, width2, label='SkillBoost', 
                    color=COLOR_SKILL, edgecolor='black', linewidth=0.5, alpha=0.85)
for bars in [bars_c1, bars_c2]:
    for bar in bars:
        height = bar.get_height()
        ax_c.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.1f}%',
                 ha='center', va='bottom', fontweight='bold', fontsize=10)
ax_c.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
ax_c.set_xticks(x)
ax_c.set_xticklabels(benchmarks, fontsize=11)
ax_c.legend(fontsize=10, framealpha=0.9)
ax_c.grid(axis='y', alpha=0.3, linestyle='--')
ax_c.set_ylim(0, 110)
plt.tight_layout()
plt.savefig(output_dir / 'figure_accuracy_improvement.pdf', bbox_inches='tight')
plt.close()
print(f"Subfigure (c) saved: {output_dir / 'figure_accuracy_improvement.pdf'}")

                                                         
                                                 
                                                         

fig, ax = plt.subplots(figsize=(10, 7))

acc_improvement = [best - no_skill for best, no_skill in zip(best_skill_acc, no_skill_acc)]

                                                  
bubble_sizes = [n * 50 for n in no_skill_turns]

colors_scatter = [COLOR_ALF, COLOR_SHEET, COLOR_BFCL]
markers = ['o', 's', '^']

for i, (bench, eff, acc_imp, size, color, marker) in enumerate(
    zip(benchmarks, reduction_pct, acc_improvement, bubble_sizes, colors_scatter, markers)):
    ax.scatter(eff, acc_imp, s=size, c=color, marker=marker, 
              edgecolors='black', linewidth=1.5, alpha=0.8, label=bench.split('\n')[0], zorder=5)
    ax.annotate(bench.split('\n')[0], (eff, acc_imp), 
               textcoords="offset points", xytext=(15, 10), 
               fontweight='bold', fontsize=11)

                     
ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
ax.axvline(x=0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)

ax.set_xlabel('Interaction Reduction (%)', fontsize=13, fontweight='bold')
ax.set_ylabel('Accuracy Improvement (pp)', fontsize=13, fontweight='bold')
ax.set_title('Skill Value: Efficiency Gain vs. Accuracy Improvement\n(Bubble size = initial interaction count)', 
            fontsize=14, fontweight='bold', pad=15)
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(fontsize=11, loc='lower right', framealpha=0.9)

plt.tight_layout()
plt.savefig(output_dir / 'skill_value_tradeoff.png', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'skill_value_tradeoff.pdf', bbox_inches='tight')
plt.close()

print(f"Figure 2 saved: {output_dir / 'skill_value_tradeoff.png'}")

                                                         
                                       
                                                         

fig, ax = plt.subplots(figsize=(12, 5))

             
categories = ['Interaction Type', 'Max Turns', 'Skill Impact', 
              'Accuracy Gain', 'Primary Value']

data_matrix = [
    ['Embodied Navigation', '50 steps', '-35.3%', '+11.1pp', 'Efficiency'],
    ['Code Generation', '6 rounds', '-9.1%', '+32.5pp', 'Quality'],
    ['Function Calling', 'Multi-turn', '-14.9%', '+3.3pp', 'Precision']
]

                            
table = ax.table(cellText=data_matrix, 
                colLabels=categories,
                rowLabels=['ALFWorld', 'SpreadSheet', 'BFCL'],
                cellLoc='center',
                loc='center',
                bbox=[0, 0.1, 1, 0.8])

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.6)

             
for (i, j), cell in table.get_celld().items():
    if i == 0:              
        cell.set_facecolor('#2C3E50')
        cell.set_text_props(color='white', fontweight='bold', fontsize=10)
    elif i % 2 == 1:                 
        cell.set_facecolor('#ECF0F1')
    else:                  
        cell.set_facecolor('#FFFFFF')

ax.set_title('Task Characteristics & Skill Engineering Value', fontsize=14, fontweight='bold', pad=15)
ax.axis('off')

plt.tight_layout()
plt.savefig(output_dir / 'task_characteristics_matrix.png', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'task_characteristics_matrix.pdf', bbox_inches='tight')
plt.close()

print(f"Figure 3 saved: {output_dir / 'task_characteristics_matrix.png'}")

                                                         
                       
                                                         

fig = plt.figure(figsize=(10, 8))

                           
categories_radar = ['Interaction\nEfficiency', 'Accuracy\nImprovement', 
                    'Time Savings', 'Robustness']

                 
alfworld_scores = []
                    
spreadsheet_scores = []
             
bfcl_scores = []

                   
angles = np.linspace(0, 2 * np.pi, len(categories_radar), endpoint=False).tolist()
alfworld_scores += alfworld_scores[:1]
spreadsheet_scores += spreadsheet_scores[:1]
bfcl_scores += bfcl_scores[:1]
angles += angles[:1]

ax = fig.add_subplot(111, polar=True)

                     
ax.plot(angles, alfworld_scores, 'o-', linewidth=2.5, label='ALFWorld', color=COLOR_ALF)
ax.fill(angles, alfworld_scores, alpha=0.15, color=COLOR_ALF)

ax.plot(angles, spreadsheet_scores, 's-', linewidth=2.5, label='SpreadSheet', color=COLOR_SHEET)
ax.fill(angles, spreadsheet_scores, alpha=0.15, color=COLOR_SHEET)

ax.plot(angles, bfcl_scores, '^-', linewidth=2.5, label='BFCL', color=COLOR_BFCL)
ax.fill(angles, bfcl_scores, alpha=0.15, color=COLOR_BFCL)

            
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories_radar, fontsize=11)
ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=10)
ax.grid(True)

ax.set_title('Skill Value Profile by Benchmark Type', fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.15), fontsize=11, framealpha=0.9)

plt.tight_layout()
plt.savefig(output_dir / 'skill_value_radar.png', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'skill_value_radar.pdf', bbox_inches='tight')
plt.close()

print(f"Figure 4 saved: {output_dir / 'skill_value_radar.png'}")

                                                         
         
                                                         

print("\n" + "=" * 80)
print("Visualization Complete!")
print("=" * 80)
print(f"\nCharts saved to: {output_dir.absolute()}")
print("\nGenerated Figures:")
print("  1. skill_efficiency_comparison.png - Multi-benchmark efficiency comparison")
print("  2. skill_value_tradeoff.png - Efficiency vs. accuracy tradeoff")
print("  3. task_characteristics_matrix.png - Task characteristics matrix")
print("  4. skill_value_radar.png - Skill value radar chart")
print("\nKey Findings:")
print("  [ALFWorld] Skill reduces interactions by 35.3% (highest efficiency gain)")
print("  [SpreadSheet] Skill improves first-round quality by +32.5pp (accuracy-focused)")
print("  [BFCL] Skill reduces over-exploration by 14.9% (precision improvement)")

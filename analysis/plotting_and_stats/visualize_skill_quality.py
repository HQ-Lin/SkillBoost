#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

                                                        
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
matplotlib.rcParams['axes.linewidth'] = 1.2
matplotlib.rcParams['font.size'] = 10
matplotlib.rcParams['legend.frameon'] = False
matplotlib.rcParams['axes.grid'] = True
matplotlib.rcParams['grid.alpha'] = 0.25
matplotlib.rcParams['grid.linestyle'] = '-'
matplotlib.rcParams['xtick.direction'] = 'in'
matplotlib.rcParams['ytick.direction'] = 'in'
matplotlib.rcParams['xtick.major.size'] = 4
matplotlib.rcParams['ytick.major.size'] = 4

def create_skill_quality_visualization():
    """createSkillqualityanalysiscan visualizationfiguretable"""
    
                                
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle('Skill Quality Analysis: Line Count vs Performance Gain', 
                 fontsize=14, fontweight='bold', y=0.995)
    
                      
    data = [
    ]
    
                                                           
    ax1 = axes[0, 0]
    
                         
    models = {'Qwen3.7-Max': '#D55E00', 'Qwen3.6-Plus': '#0072B2', 'Kimi-K2.6': '#009E73'}
    benchmark_markers = {'ALFWorld': 'o', 'SpreadSheet': 's', 'LiveMath': '^', 'BFCL': 'D'}
    benchmark_labels = {'ALFWorld': 'ALFWorld', 'SpreadSheet': 'SpreadSheet', 
                       'LiveMath': 'LiveMath', 'BFCL': 'BFCL'}
    
    for model, color in models.items():
        model_data = [d for d in data if d['model'] == model]
        x = [d['line_diff'] for d in model_data]
        y = [d['gain'] for d in model_data]
        
        ax1.scatter(x, y, c=color, s=100, alpha=0.85, edgecolors='black', 
                   linewidth=1.0, zorder=5, label=model)
        
                                                
        for d in model_data:
            label = benchmark_labels[d['benchmark']]
            x_pos = d['line_diff']
            y_pos = d['gain']
            
                                                         
            x_offset = 6
            y_offset = 0.5
            
                                                
            if x_pos > 150:
                x_offset = -50
            if y_pos > 15:
                y_offset = -1.5
            
            ax1.annotate(label, (x_pos, y_pos), 
                        textcoords="offset points", xytext=(x_offset, y_offset), 
                        fontsize=7.5, fontweight='bold', alpha=0.9)
    
                    
    x_all = [d['line_diff'] for d in data]
    y_all = [d['gain'] for d in data]
    z = np.polyfit(x_all, y_all, 1)
    p = np.poly1d(z)
    x_line = np.linspace(0, max(x_all), 100)
    ax1.plot(x_line, p(x_line), "k--", alpha=0.5, linewidth=1.5, 
            label=f'Trend (slope={z[0]:.3f})')
    
    ax1.set_xlabel('Skill Line Count Increase', fontsize=10.5, fontweight='bold')
    ax1.set_ylabel('Performance Gain (pp)', fontsize=10.5, fontweight='bold')
    ax1.set_title('(a) Line Count vs Performance Gain', fontsize=11.5, fontweight='bold', pad=8)
    ax1.legend(fontsize=8.5, loc='upper right')
    ax1.axhline(y=0, color='black', linewidth=0.6, alpha=0.4)
    ax1.axvline(x=0, color='black', linewidth=0.6, alpha=0.4)
    
                                                                  
    ax2 = axes[0, 1]
    
    for model, color in models.items():
        model_data = [d for d in data if d['model'] == model]
        x = [d['v0_acc'] for d in model_data]
        y = [d['gain'] for d in model_data]
        
        ax2.scatter(x, y, c=color, s=100, alpha=0.85, edgecolors='black', 
                   linewidth=1.0, zorder=5, label=model)
        
                                                
        for d in model_data:
            label = benchmark_labels[d['benchmark']]
            x_pos = d['v0_acc']
            y_pos = d['gain']
            
            x_offset = 6
            y_offset = 0.5
            
            if x_pos > 90:
                x_offset = -45
            if y_pos > 15:
                y_offset = -1.5
            
            ax2.annotate(label, (x_pos, y_pos), 
                        textcoords="offset points", xytext=(x_offset, y_offset), 
                        fontsize=7.5, fontweight='bold', alpha=0.9)
    
                    
    z2 = np.polyfit([d['v0_acc'] for d in data], y_all, 1)
    p2 = np.poly1d(z2)
    x2_line = np.linspace(min([d['v0_acc'] for d in data]), 
                          max([d['v0_acc'] for d in data]), 100)
    ax2.plot(x2_line, p2(x2_line), "k--", alpha=0.5, linewidth=1.5,
            label='Trend')
    
    ax2.set_xlabel('V0 Baseline Accuracy (%)', fontsize=10.5, fontweight='bold')
    ax2.set_ylabel('Performance Gain (pp)', fontsize=10.5, fontweight='bold')
    ax2.set_title('(b) Baseline Accuracy vs Gain', fontsize=11.5, fontweight='bold', pad=8)
    ax2.legend(fontsize=8.5, loc='upper right')
    ax2.axhline(y=0, color='black', linewidth=0.6, alpha=0.4)
    
                                                                         
    ax3 = axes[1, 0]
    
    categories = ['0 lines\n(Quality Opt.)', '1-30 lines\n(Concise)', 
                  '30-80 lines\n(Moderate)', '80-180 lines\n(Extensive)']
    avg_gains = []
                                        
    colors_bar = ['#CC79A7', '#56B4E9', '#E69F00', '#D55E00']
    
    bars = ax3.bar(range(len(categories)), avg_gains, color=colors_bar, 
                   edgecolor='black', linewidth=0.8, alpha=0.9, width=0.65)
    
                              
    for i, (bar, gain) in enumerate(zip(bars, avg_gains)):
        y_val = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., y_val + 0.4,
                f'+{gain:.1f}', ha='center', va='bottom', 
                fontsize=8.5, fontweight='bold')
    
    ax3.set_xticks(range(len(categories)))
    ax3.set_xticklabels(categories, fontsize=8)
    ax3.set_ylabel('Average Performance Gain (pp)', fontsize=10, fontweight='bold')
    ax3.set_title('(c) Avg Gain by Line Count Range', fontsize=11.5, fontweight='bold', pad=8)
    ax3.set_ylim(0, 16)
    ax3.grid(axis='y', alpha=0.25)
    
                                                                     
    ax4 = axes[1, 1]
    
                                    
    efficiencies = []
    for d in data:
        if d['line_diff'] > 0:
            eff = d['gain'] / d['line_diff']
            efficiencies.append({**d, 'efficiency': eff})
    
                        
    efficiencies.sort(key=lambda x: x['efficiency'], reverse=True)
    
    x_pos = range(len(efficiencies))
    eff_values = [e['efficiency'] for e in efficiencies]
    labels = [f"{e['model']} - {e['benchmark']}" for e in efficiencies]
    colors_eff = [e['color'] for e in efficiencies]
    
    bars_eff = ax4.barh(x_pos, eff_values, color=colors_eff, 
                        edgecolor='black', linewidth=0.8, alpha=0.9, height=0.65)
    
                      
    for i, (bar, eff) in enumerate(zip(bars_eff, eff_values)):
        ax4.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height()/2.,
                f'{eff:.2f}', va='center', fontsize=8, fontweight='bold')
    
    ax4.set_yticks(x_pos)
    ax4.set_yticklabels(labels, fontsize=7.5)
    ax4.set_xlabel('Efficiency (pp/line)', fontsize=10, fontweight='bold')
    ax4.set_title('(d) Line Efficiency Ranking', fontsize=11.5, fontweight='bold', pad=8)
    ax4.grid(axis='x', alpha=0.25)
    
    plt.tight_layout(rect=[0, 0, 1, 0.985])
    
                 
    output_path = Path('/path/to/project/analysis/skill_quality_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"Chart saved: {output_path}")
    print(f"   Resolution: 300 DPI")
    print(f"   Size: 12x9 inches")
    
    return output_path

if __name__ == '__main__':
    create_skill_quality_visualization()

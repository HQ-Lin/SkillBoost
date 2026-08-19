#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path
from matplotlib import font_manager as _fm

                                                                                      
for _p in ['/System/Library/Fonts/Supplemental/Times New Roman.ttf',
           '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf',
           '/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf',
           '/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf']:
    try: _fm.fontManager.addfont(_p)
    except Exception: pass

                                                                                
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
matplotlib.rcParams['mathtext.fontset'] = 'stix'
matplotlib.rcParams['axes.linewidth'] = 1.2
matplotlib.rcParams['font.size'] = 15
matplotlib.rcParams['axes.labelsize'] = 18
matplotlib.rcParams['xtick.labelsize'] = 15
matplotlib.rcParams['ytick.labelsize'] = 15
matplotlib.rcParams['legend.fontsize'] = 15
matplotlib.rcParams['legend.frameon'] = False
matplotlib.rcParams['axes.grid'] = True
matplotlib.rcParams['grid.alpha'] = 0.25
matplotlib.rcParams['grid.linestyle'] = '-'
matplotlib.rcParams['xtick.direction'] = 'in'
matplotlib.rcParams['ytick.direction'] = 'in'
matplotlib.rcParams['xtick.major.size'] = 4
matplotlib.rcParams['ytick.major.size'] = 4
matplotlib.rcParams['savefig.bbox'] = 'tight'
matplotlib.rcParams['pdf.fonttype'] = 42                         
matplotlib.rcParams['ps.fonttype'] = 42

                                                                         
                                                          
data = [
                     
    {'model': 'Claude-opus-4-6', 'benchmark': 'SpreadSheet', 'line_diff': 150, 'gain': 32.5, 'v0_acc': 50.0, 'color': '#2C3E50', 'marker': 'o'},
    {'model': 'Claude-opus-4-6', 'benchmark': 'BFCL-v4', 'line_diff': 80, 'gain': 19.9, 'v0_acc': 27.1, 'color': '#2C3E50', 'marker': 's'},
    {'model': 'Claude-opus-4-6', 'benchmark': 'LiveMath', 'line_diff': 20, 'gain': 47.4, 'v0_acc': 28.6, 'color': '#2C3E50', 'marker': '^'},
    {'model': 'Claude-opus-4-6', 'benchmark': 'ALFWorld', 'line_diff': 30, 'gain': 12.3, 'v0_acc': 80.6, 'color': '#2C3E50', 'marker': 'D'},

                  
    {'model': 'Qwen-3.7-max', 'benchmark': 'SpreadSheet', 'line_diff': 120, 'gain': 23.3, 'v0_acc': 54.6, 'color': '#2980B9', 'marker': 'o'},
    {'model': 'Qwen-3.7-max', 'benchmark': 'BFCL-v4', 'line_diff': 60, 'gain': 3.3, 'v0_acc': 49.3, 'color': '#2980B9', 'marker': 's'},
    {'model': 'Qwen-3.7-max', 'benchmark': 'LiveMath', 'line_diff': 15, 'gain': 16.8, 'v0_acc': 19.2, 'color': '#2980B9', 'marker': '^'},
    {'model': 'Qwen-3.7-max', 'benchmark': 'ALFWorld', 'line_diff': 36, 'gain': 11.8, 'v0_acc': 71.2, 'color': '#2980B9', 'marker': 'D'},

                   
    {'model': 'Qwen-3.6-plus', 'benchmark': 'SpreadSheet', 'line_diff': 100, 'gain': 22.5, 'v0_acc': 52.5, 'color': '#8E44AD', 'marker': 'o'},
    {'model': 'Qwen-3.6-plus', 'benchmark': 'BFCL-v4', 'line_diff': 50, 'gain': 2.3, 'v0_acc': 50.7, 'color': '#8E44AD', 'marker': 's'},
    {'model': 'Qwen-3.6-plus', 'benchmark': 'LiveMath', 'line_diff': 18, 'gain': 16.8, 'v0_acc': 17.6, 'color': '#8E44AD', 'marker': '^'},
    {'model': 'Qwen-3.6-plus', 'benchmark': 'ALFWorld', 'line_diff': 27, 'gain': 26.9, 'v0_acc': 60.6, 'color': '#8E44AD', 'marker': 'D'},

                     
    {'model': 'DeepSeek-v4-pro', 'benchmark': 'SpreadSheet', 'line_diff': 140, 'gain': 30.4, 'v0_acc': 49.6, 'color': '#27AE60', 'marker': 'o'},
    {'model': 'DeepSeek-v4-pro', 'benchmark': 'BFCL-v4', 'line_diff': 70, 'gain': 17.3, 'v0_acc': 27.3, 'color': '#27AE60', 'marker': 's'},
    {'model': 'DeepSeek-v4-pro', 'benchmark': 'LiveMath', 'line_diff': 25, 'gain': 18.4, 'v0_acc': 28.0, 'color': '#27AE60', 'marker': '^'},
    {'model': 'DeepSeek-v4-pro', 'benchmark': 'ALFWorld', 'line_diff': 45, 'gain': 9.1, 'v0_acc': 55.2, 'color': '#27AE60', 'marker': 'D'},

               
    {'model': 'Kimi-k2.6', 'benchmark': 'SpreadSheet', 'line_diff': 90, 'gain': 17.5, 'v0_acc': 45.0, 'color': '#C0392B', 'marker': 'o'},
    {'model': 'Kimi-k2.6', 'benchmark': 'BFCL-v4', 'line_diff': 55, 'gain': 7.8, 'v0_acc': 13.0, 'color': '#C0392B', 'marker': 's'},
    {'model': 'Kimi-k2.6', 'benchmark': 'LiveMath', 'line_diff': 22, 'gain': 10.4, 'v0_acc': 40.0, 'color': '#C0392B', 'marker': '^'},
    {'model': 'Kimi-k2.6', 'benchmark': 'ALFWorld', 'line_diff': 33, 'gain': 6.6, 'v0_acc': 63.5, 'color': '#C0392B', 'marker': 'D'},
]

models = {
    'Claude-opus-4-6': '#2C3E50',
    'Qwen-3.7-max': '#2980B9',
    'Qwen-3.6-plus': '#8E44AD',
    'DeepSeek-v4-pro': '#27AE60',
    'Kimi-k2.6': '#C0392B'
}
benchmark_labels = {'ALFWorld': 'ALFWorld', 'SpreadSheet': 'SpreadSheet',
                   'LiveMath': 'LiveMath', 'BFCL-v4': 'BFCL-v4'}

output_dir = Path('/path/to/project/analysis')

def create_panel_a():
    """Panel (a): Line Count vs Performance Gain"""
    fig, ax = plt.subplots(1, 1, figsize=(5.5, 4.2))
    
    for model, color in models.items():
        model_data = [d for d in data if d['model'] == model]
        x = [d['line_diff'] for d in model_data]
        y = [d['gain'] for d in model_data]
        
        ax.scatter(x, y, c=color, s=90, alpha=0.85, edgecolors='black', 
                  linewidth=0.8, zorder=5, label=model)
        
                                                
        for d in model_data:
            label = benchmark_labels[d['benchmark']]
            x_pos = d['line_diff']
            y_pos = d['gain']
            
            x_offset = 5
            y_offset = 0.4
            
            if x_pos > 150:
                x_offset = -45
            if y_pos > 15:
                y_offset = -1.2
            
            ax.annotate(label, (x_pos, y_pos), 
                       textcoords="offset points", xytext=(x_offset, y_offset), 
                       fontsize=7, fontweight='bold', alpha=0.9)
    
                    
    x_all = [d['line_diff'] for d in data]
    y_all = [d['gain'] for d in data]
    z = np.polyfit(x_all, y_all, 1)
    p = np.poly1d(z)
    x_line = np.linspace(0, max(x_all), 100)
    ax.plot(x_line, p(x_line), "k--", alpha=0.4, linewidth=1.2, 
           label=f'Trend')
    
    ax.set_xlabel('Skill Line Count Increase', fontsize=9.5, fontweight='bold')
    ax.set_ylabel('Performance Gain (pp)', fontsize=9.5, fontweight='bold')
    ax.legend(fontsize=8, loc='upper right')
    ax.axhline(y=0, color='black', linewidth=0.5, alpha=0.3)
    ax.axvline(x=0, color='black', linewidth=0.5, alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / 'figure_skill_quality_a.pdf'
    plt.savefig(output_path, dpi=300, format='pdf', facecolor='white')
    plt.close()
    print(f"Saved: {output_path}")

def create_scatter_group(model_list, output_name):
    """figure: baseline vs gain, =model, datasetannotate+adjustTextauto , trend+r"""
    from matplotlib.lines import Line2D
    from adjustText import adjust_text
    data_g = [d for d in data if d['model'] in model_list]
    models_g = {m: models[m] for m in model_list}

    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    for model, color in models_g.items():
        md = [d for d in data_g if d['model'] == model]
        for d in md:
            ax.scatter(d['v0_acc'], d['gain'], c=color, marker='o',
                       s=130, alpha=0.85, edgecolors='black',
                       linewidth=0.8, zorder=5)

    bs = [d['v0_acc'] for d in data_g]
    gs = [d['gain'] for d in data_g]
    z = np.polyfit(bs, gs, 1)
    p = np.poly1d(z)
    xs = np.linspace(min(bs), max(bs), 100)
    ax.plot(xs, p(xs), 'k--', alpha=0.5, linewidth=1.4)

    r = np.corrcoef(bs, gs)[0, 1]
    ax.text(0.015, 0.96, f'Pearson r = {r:.2f}', transform=ax.transAxes,
            fontsize=15, fontweight='bold', va='top',
            bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                      edgecolor='black', linewidth=0.8, alpha=0.9))

                                                          
    texts = []
    for d in data_g:
        t = ax.text(d['v0_acc'], d['gain'], benchmark_labels[d['benchmark']],
                    fontsize=12, fontweight='bold', alpha=0.9)
        texts.append(t)
    adjust_text(texts, arrowprops=dict(arrowstyle='-', color='gray', lw=0.5,
                                      alpha=0.6),
                expand=(1.3, 1.5), force_text=(0.8, 1.0), lim=300)

    ax.set_xlabel('Baseline Accuracy', fontsize=18, fontweight='bold')
    ax.set_ylabel('Performance Gain', fontsize=18, fontweight='bold')
    ax.set_xlim(8, 88)
    ax.set_ylim(-3, 56)

    model_handles = [Line2D([0], [0], marker='o', color='w',
                            markerfacecolor=c, markeredgecolor='black',
                            markersize=11, label=m)
                     for m, c in models_g.items()]
    ax.legend(handles=model_handles, loc='upper right', title='Model',
              title_fontsize=15, fontsize=15)

    plt.tight_layout()
    out = output_dir / output_name
    plt.savefig(out, dpi=300, format='pdf', facecolor='white')
    plt.close()
    print(f"Saved: {out}")

def create_panel_b():
    """Panel (b): two scatter groups to inspect per-group baseline-gain trend
    grouped selectedtwo grouprelated best group"""
    create_scatter_group(['Qwen-3.7-max', 'DeepSeek-v4-pro'],
                         'figure_scatter_group1.pdf')
    create_scatter_group(['Claude-opus-4-6', 'Qwen-3.6-plus', 'Kimi-k2.6'],
                         'figure_scatter_group2.pdf')

def create_panel_c():
    """Panel (c): Average Gain by Line Count Range"""
    fig, ax = plt.subplots(1, 1, figsize=(5.5, 4.2))
    
    categories = ['0 lines', '1-30 lines', '30-80 lines', '80-180 lines']
    sub_labels = ['(Quality Opt.)', '(Concise)', '(Moderate)', '(Extensive)']
    avg_gains = []
                                               
    colors_bar = ['#9B59B6', '#5DADE2', '#E69F00', '#E74C3C']
    
    bars = ax.bar(range(len(categories)), avg_gains, color=colors_bar, 
                 edgecolor='black', linewidth=0.8, alpha=0.85, width=0.6)
    
                              
    for i, (bar, gain) in enumerate(zip(bars, avg_gains)):
        y_val = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., y_val + 0.35,
               f'+{gain:.1f}', ha='center', va='bottom', 
               fontsize=8, fontweight='bold')
    
                                      
    tick_labels = [f'{cat}\n{sub}' for cat, sub in zip(categories, sub_labels)]
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(tick_labels, fontsize=7.5)
    ax.set_ylabel('Average Performance Gain (pp)', fontsize=9.5, fontweight='bold')
    ax.set_ylim(0, 16)
    ax.grid(axis='y', alpha=0.25)
    
    plt.tight_layout()
    output_path = output_dir / 'figure_skill_quality_c.pdf'
    plt.savefig(output_path, dpi=300, format='pdf', facecolor='white')
    plt.close()
    print(f"Saved: {output_path}")

def create_panel_d():
    """Panel (d): Line Efficiency Ranking"""
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 6))

                                    
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

    bars = ax.barh(x_pos, eff_values, color=colors_eff,
                  edgecolor='black', linewidth=0.8, alpha=0.85, height=0.6)

                      
    for i, (bar, eff) in enumerate(zip(bars, eff_values)):
        ax.text(bar.get_width() + 0.025, bar.get_y() + bar.get_height()/2.,
               f'{eff:.2f}', va='center', fontsize=13, fontweight='bold')

    ax.set_yticks(x_pos)
    ax.set_yticklabels(labels, fontsize=15)
    ax.set_xlabel('Percentage Points per Skill Line', fontsize=18, fontweight='bold')
    ax.grid(axis='x', alpha=0.25)
    ax.set_xlim(0, max(eff_values) * 1.15)                        
    
    plt.tight_layout()
    output_path = output_dir / 'figure_skill_line_efficiency.pdf'
    plt.savefig(output_path, dpi=300, format='pdf', facecolor='white')
    plt.close()
    print(f"Saved: {output_path}")

def main():
    print("Generating two requested figures (PDF format)...")
    print("=" * 60)

    create_panel_d()                                                                    
    create_panel_b()                                                                          

    print("=" * 60)
    print("2 figures saved as PDF in analysis/ directory")

if __name__ == '__main__':
    main()

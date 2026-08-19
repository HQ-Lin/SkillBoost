import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

                                                              
                                                          
                                                              
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'mathtext.fontset': 'stix',
    'font.size': 18,
    'axes.labelsize': 17,
    'axes.titlesize': 20,
    'xtick.labelsize': 15,
    'ytick.labelsize': 15,
    'legend.fontsize': 17,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 3.0,
    'ytick.major.size': 3.0,
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'text.usetex': False,
    'axes.unicode_minus': False,
    'savefig.dpi': 300,
    'figure.dpi': 300,
})

output_dir = Path("analysis")
output_dir.mkdir(exist_ok=True)

                                                              
                                       
                                                              
N = [1, 2, 4, 6, 8]

data = {
    'SpreadsheetBench': {
        'gain': [],                    
        'cost': [],                         
    },
    'ALFWorld': {
        'gain': [],
        'cost': [],
    },
}

STAR_IDX = 2                                                           

                                                             
C_GAIN     = '#E6E6E6'                                               
C_GAIN_ED  = '#8C8C8C'                                              
C_GAIN_HL  = '#CFE2F5'                                            
C_GAIN_HLED = '#4C8DCB'                                              
C_COST     = '#3D405B'                                                

x = np.arange(len(N))
bar_w = 0.58

                                                              
                                              
                                                             
                                                    
                                                              
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

FIGSIZE = (3.0, 2.6)                                           
FNAME = {
    'SpreadsheetBench': 'figure_bestofn_spreadsheetbench',
    'ALFWorld': 'figure_bestofn_alfworld',
}

def make_panel(name, d):
    gain, cost = d['gain'], d['cost']
    fig, ax = plt.subplots(figsize=FIGSIZE)

                                           
    bars = ax.bar(x, cost, width=bar_w, color=C_GAIN,
                  edgecolor=C_GAIN_ED, linewidth=0.8, zorder=3)
    bars[STAR_IDX].set_color(C_GAIN_HL)
    bars[STAR_IDX].set_edgecolor(C_GAIN_HLED)
    bars[STAR_IDX].set_linewidth(1.1)

    ax.set_ylabel('Cost (M tokens)', color='#333333')
    ax.tick_params(axis='y', colors='#333333')
    ax.set_ylim(0, max(cost) * 1.52)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax.set_xlabel(r'$N$')
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in N])
    ax.set_xlim(-0.6, len(N) - 0.4)
    ax.spines['top'].set_visible(False)
    ax.grid(True, axis='y', linestyle='-', alpha=0.14, zorder=0)

                                            
    ax2 = ax.twinx()
    ax2.plot(x, gain, color=C_COST, marker='o', markersize=4.5,
             markeredgecolor='white', markeredgewidth=0.9,
             linewidth=1.9, zorder=4)
    ax2.set_ylabel('Total Gain (pp)', color=C_COST)
    ax2.tick_params(axis='y', colors=C_COST)
    ax2.set_ylim(0, max(gain) * 1.52)
    ax2.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax2.spines['top'].set_visible(False)

                                                                       
    ax.annotate('Gain–Cost\ntrade-off',
                xy=(STAR_IDX, cost[STAR_IDX]),
                xytext=(STAR_IDX, max(cost) * 1.52 * 0.82),
                fontsize=11, color=C_GAIN_HLED, fontweight='bold',
                ha='center', va='center')

                                                                      
                                                       
    h_cost = plt.Rectangle((0, 0), 1, 1, facecolor=C_GAIN,
                           edgecolor=C_GAIN_ED, linewidth=0.8)
    h_gain = Line2D([0], [0], color=C_COST, marker='o', markersize=4.5,
                    markeredgecolor='white', linewidth=1.9)
    ax.legend([h_cost, h_gain], ['Cost (tokens)', 'Total Gain'],
              loc='lower center', frameon=False, fontsize=11, ncol=2,
              handlelength=1.4, columnspacing=1.3, handletextpad=0.5,
              borderpad=0.1, bbox_to_anchor=(0.5, 1.0))

                                                                         
                                                                          
                                                  
    fig.subplots_adjust(left=0.175, right=0.825, top=0.87, bottom=0.175)
    stem = FNAME[name]
    for ext in ('pdf', 'png'):
        out = output_dir / f'{stem}.{ext}'
        fig.savefig(out, pad_inches=0.0)
        print(f"Saved: {out}")
    plt.close(fig)

for name, d in data.items():
    make_panel(name, d)

                                                              
                                                              
                                                              
def draw_axes(ax, d, show_cost_label, show_gain_label):
    """Draw cost-bars + gain-line dual axis; y-axis labels shown selectively
    so the shared metrics are labelled only once across the two panels."""
    gain, cost = d['gain'], d['cost']

    bars = ax.bar(x, cost, width=bar_w, color=C_GAIN,
                  edgecolor=C_GAIN_ED, linewidth=0.8, zorder=3)
    bars[STAR_IDX].set_color(C_GAIN_HL)
    bars[STAR_IDX].set_edgecolor(C_GAIN_HLED)
    bars[STAR_IDX].set_linewidth(1.1)

    if show_cost_label:
        ax.set_ylabel('Cost (M tokens)', color='#333333')
    ax.tick_params(axis='y', colors='#333333')
    ax.set_ylim(0, max(cost) * 1.52)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax.set_xlabel(r'$N$')
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in N])
    ax.set_xlim(-0.6, len(N) - 0.4)
    ax.spines['top'].set_visible(False)
    ax.grid(True, axis='y', linestyle='-', alpha=0.14, zorder=0)

    ax2 = ax.twinx()
    ax2.plot(x, gain, color=C_COST, marker='o', markersize=6.5,
             markeredgecolor='white', markeredgewidth=1.1,
             linewidth=2.6, zorder=4)
    if show_gain_label:
        ax2.set_ylabel('Total Gain (pp)', color=C_COST)
    ax2.tick_params(axis='y', colors=C_COST)
    ax2.set_ylim(0, max(gain) * 1.52)
    ax2.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax2.spines['top'].set_visible(False)

def make_combined():
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.8))
    items = list(data.items())
    draw_axes(axes[0], items[0][1], show_cost_label=True, show_gain_label=True)
    draw_axes(axes[1], items[1][1], show_cost_label=True, show_gain_label=True)

                                    
    labels = ['(a) SpreadsheetBench', '(b) ALFWorld']
    for ax, lab in zip(axes, labels):
        ax.text(0.5, -0.27, lab, transform=ax.transAxes,
                ha='center', va='top', fontsize=18)

                                                                           
                                            
    h_cost = plt.Rectangle((0, 0), 1, 1, facecolor=C_GAIN,
                           edgecolor=C_GAIN_ED, linewidth=0.8)
    h_trade = plt.Rectangle((0, 0), 1, 1, facecolor=C_GAIN_HL,
                            edgecolor=C_GAIN_HLED, linewidth=1.1)
    h_gain = Line2D([0], [0], color=C_COST, marker='o', markersize=6.5,
                    markeredgecolor='white', linewidth=2.6)
    fig.legend([h_cost, h_gain, h_trade],
               ['Cost', 'Total Gain', r'Gain–Cost trade-off ($N{=}4$)'],
               loc='upper center', frameon=False, fontsize=15, ncol=3,
               handlelength=1.4, columnspacing=1.1, handletextpad=0.5,
               bbox_to_anchor=(0.5, 1.0))

    fig.subplots_adjust(left=0.095, right=0.905, top=0.87, bottom=0.28,
                        wspace=0.60)
    for ext in ('pdf', 'png'):
        out = output_dir / f'figure_bestofn_combined.{ext}'
        fig.savefig(out, bbox_inches='tight', pad_inches=0.01)
        print(f"Saved: {out}")
    plt.close(fig)

make_combined()


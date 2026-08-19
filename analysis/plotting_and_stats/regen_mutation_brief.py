#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS = {
    'header': '#2C3E50',
    'bg': '#FFFFFF',
    'text_medium': '#34495E',
}

def create_mutation_brief_list():
    fig, ax = plt.subplots(1, 1, figsize=(6.5, 4.5))
    ax.set_xlim(0, 6.5)
    ax.set_ylim(0, 4.5)
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])
    
                                  
    ax.text(3.25, 4.2, 'Repair Brief (Template)',
            fontsize=13, fontweight='bold', ha='center', va='center',
            color=COLORS['header'], family='Comic Sans MS')
    
    modules = [
        ('1', 'Metadata Header', ['Version, model, dataset, baseline metrics']),
        ('2', 'Baseline Performance Summary', ['Overall success rates (train vs. test)', 'Per-category performance breakdown']),
        ('3', 'Failure Mode Cluster Analysis', ['Grouped failure patterns with root causes', 'Representative case examples']),
        ('4', 'Mutation Strategy (Repair Actions)', ['Concrete modification proposals', 'Exact rule text to be added/modified']),
        ('5', 'Mutation Action Mapping Table', ['Traceability matrix:', r'failure cluster $\rightarrow$ root cause $\rightarrow$ repair action $\rightarrow$ SKILL.md location']),
        ('6', 'Anti-Regression Guardrails', ['Must-maintain strengths', 'Success thresholds and rejection criteria']),
        ('7', 'Back-Testing Results (Post-evolution, optional)', ['Targeted re-test on previously failed cases', 'Full validation set comparison']),
        ('8', 'Execution Plan', ['Workflow checklist with progress tracking']),
    ]
    
    y_start = 3.85
    y_step = 0.58
    
    for i, (num, title, descriptions) in enumerate(modules):
        if i == 0:
            y_title = y_start
        elif i == 1:
            y_title = y_start - 0.36
        else:
            y_title = y_start - 0.36 - (i - 1) * y_step
        
        ax.text(0.3, y_title, num, fontsize=11, fontweight='bold',
                ha='left', va='center', color='#2980B9', family='Comic Sans MS')
        
        ax.text(0.6, y_title, title, fontsize=10, fontweight='bold',
                ha='left', va='center', color=COLORS['header'], family='Comic Sans MS')
        
        line_height = 0.20
        equal_gap = 0.18
        y_desc_start = y_title - equal_gap
        
        for j, desc in enumerate(descriptions):
            ax.text(0.9, y_desc_start - j*line_height, desc, fontsize=8,
                    ha='left', va='center', color=COLORS['text_medium'],
                    family='Comic Sans MS', alpha=0.85)
    
    plt.tight_layout()
    output_path = '/path/to/project/analysis/figure_mutation_brief_modules.pdf'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    
    print(f"✓ Generated: {output_path}")

if __name__ == '__main__':
    create_mutation_brief_list()

#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

                       
COLORS = {
    'header': '#2C3E50',                       
    'baseline': '#2980B9',                       
    'failure': '#C0392B',               
    'strategy': '#27AE60',                        
    'mapping': '#8E44AD',                  
    'guardrails': '#D35400',                
    'backtest': '#16A085',          
    'execution': '#34495E',              
    'arrow': '#7F8C8D',                    
    'bg': '#ECF0F1',                                 
    'text_white': '#FFFFFF',
    'text_dark': '#2C3E50',
}

def create_mutation_brief_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(11, 8.5))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 8.5)
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])
    
           
    ax.text(5.5, 8.1, 'Mutation Brief: Structure and Workflow', 
            fontsize=18, fontweight='bold', ha='center', va='center',
            color=COLORS['header'], family='sans-serif')
    
                                                                            
    modules = [
                                 
        (0.5, 6.5, 3.0, 1.2, 
         '① Metadata Header', 
         ['version, model, dataset', 'train/test success rates'],
         COLORS['header']),
        
        (4.0, 6.5, 3.0, 1.2,
         '② Baseline Performance',
         ['overall metrics (train vs test)', 'per-category breakdown'],
         COLORS['baseline']),
        
        (7.5, 6.5, 3.0, 1.2,
         '③ Failure Mode Clusters',
         ['grouped failure patterns', 'root cause analysis + cases'],
         COLORS['failure']),
        
                                    
        (0.5, 4.6, 3.0, 1.2,
         '④ Mutation Strategy',
         ['concrete repair actions', 'exact rule text proposals'],
         COLORS['strategy']),
        
        (4.0, 4.6, 3.0, 1.2,
         '⑤ Action Mapping Table',
         ['failure → cause → action', 'SKILL.md location trace'],
         COLORS['mapping']),
        
        (7.5, 4.6, 3.0, 1.2,
         '⑥ Anti-Regression Guardrails',
         ['must-maintain strengths', 'rejection criteria'],
         COLORS['guardrails']),
        
                                 
        (2.0, 2.7, 3.0, 1.2,
         '⑦ Back-Testing Results',
         ['targeted re-test on failures', 'full validation comparison'],
         COLORS['backtest']),
        
        (6.0, 2.7, 3.0, 1.2,
         '⑧ Execution Plan',
         ['workflow checklist', 'progress tracking'],
         COLORS['execution']),
    ]
    
                  
    for x, y, w, h, title, content, color in modules:
                  
        box = FancyBboxPatch((x, y), w, h, 
                             boxstyle="round,pad=0.1",
                             facecolor=color, 
                             edgecolor='white',
                             linewidth=2,
                             alpha=0.9)
        ax.add_patch(box)
        
               
        ax.text(x + w/2, y + h - 0.25, title,
                fontsize=10, fontweight='bold', ha='center', va='center',
                color=COLORS['text_white'], family='sans-serif')
        
                 
        for i, line in enumerate(content):
            ax.text(x + w/2, y + h - 0.55 - i*0.25, line,
                    fontsize=8, ha='center', va='center',
                    color=COLORS['text_white'], family='sans-serif', alpha=0.95)
    
                                        
    arrow_style = dict(arrowstyle='->', lw=2.5, color=COLORS['arrow'],
                      connectionstyle='arc3,rad=0.1')
    
                      
    ax.add_patch(FancyArrowPatch((3.5, 7.1), (4.0, 7.1), **arrow_style))
    ax.add_patch(FancyArrowPatch((7.0, 7.1), (7.5, 7.1), **arrow_style))
    
                                 
    ax.add_patch(FancyArrowPatch((9.0, 6.5), (2.0, 5.8), **arrow_style))
    ax.add_patch(FancyArrowPatch((9.0, 6.5), (5.5, 5.8), **arrow_style))
    
                      
    ax.add_patch(FancyArrowPatch((3.5, 5.2), (4.0, 5.2), **arrow_style))
    ax.add_patch(FancyArrowPatch((7.0, 5.2), (7.5, 5.2), **arrow_style))
    
                                 
    ax.add_patch(FancyArrowPatch((5.5, 4.6), (3.5, 3.9), **arrow_style))
    ax.add_patch(FancyArrowPatch((9.0, 4.6), (7.5, 3.9), **arrow_style))
    
                  
    ax.add_patch(FancyArrowPatch((5.0, 3.3), (6.0, 3.3), **arrow_style))
    
                                        
    feedback_style = dict(arrowstyle='->', lw=2, color='#E74C3C',
                         linestyle='--', connectionstyle='arc3,rad=-0.3')
    ax.add_patch(FancyArrowPatch((3.5, 2.7), (9.0, 6.5), **feedback_style))
    
                        
    ax.text(1.5, 4.8, 'If failed:', fontsize=9, fontweight='bold',
            color='#E74C3C', ha='center', va='center', family='sans-serif',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FADBD8', 
                     edgecolor='#E74C3C', alpha=0.8))
    
                      
                      
    ax.annotate('', xy=(0.3, 7.1), xytext=(0.0, 7.1),
                arrowprops=dict(arrowstyle='->', lw=2.5, color='#34495E'))
    ax.text(-0.1, 7.1, ' Input\nExecution Traces', fontsize=9,
            ha='right', va='center', fontweight='bold',
            color='#34495E', family='sans-serif')
    
                        
    ax.annotate('', xy=(10.7, 3.3), xytext=(11.0, 3.3),
                arrowprops=dict(arrowstyle='->', lw=2.5, color='#34495E'))
    ax.text(11.1, 3.3, ' Output\nSKILL.md vN+1', fontsize=9,
            ha='left', va='center', fontweight='bold',
            color='#34495E', family='sans-serif')
    
                            
    principles_y = 1.2
    ax.text(5.5, principles_y + 0.3, 'Core Design Principles:',
            fontsize=11, fontweight='bold', ha='center', va='center',
            color=COLORS['header'], family='sans-serif')
    
    principles = [
        '✓ Data-Driven Attribution: Every modification traces to quantified failure clusters',
        '✓ Actionable Specificity: Exact rule text with target SKILL.md sections',
        '✓ Closed-Loop Validation: Anti-regression guardrails + mandatory back-testing'
    ]
    
    for i, principle in enumerate(principles):
        ax.text(5.5, principles_y - i*0.25, principle,
                fontsize=8.5, ha='center', va='center',
                color=COLORS['text_dark'], family='sans-serif', alpha=0.85)
    
    plt.tight_layout()
    plt.savefig('/path/to/project/analysis/figure_mutation_brief_structure.pdf',
                dpi=300, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    
    print("✓ Generated: figure_mutation_brief_structure.pdf")

if __name__ == '__main__':
    create_mutation_brief_diagram()

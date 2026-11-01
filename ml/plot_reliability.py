"""Render the measured reliability bins; no interpolated accuracy claims."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',default='benchmarks/scientific/results.json');p.add_argument('--output',default='benchmarks/scientific/reliability.svg');a=p.parse_args()
    data=json.loads(Path(a.results).read_text());bins=[b for b in data['reliability'] if b['n']]
    fig,axes=plt.subplots(1,2,figsize=(9,4))
    axes[0].plot([0,1],[0,1],'--',color='gray',label='Perfect calibration')
    axes[0].plot([b['predicted'] for b in bins],[b['observed'] for b in bins],'o-',label='Held-out equipment')
    axes[0].set(xlabel='Mean predicted probability',ylabel='Observed failure frequency',xlim=(0,1),ylim=(0,1),title='Reliability (synthetic only)');axes[0].legend(fontsize=8)
    axes[1].bar([b['lower']+.05 for b in bins],[b['n'] for b in bins],width=.08)
    axes[1].set(xlabel='Probability bin',ylabel='Number of observations',title='Bin support')
    fig.tight_layout();fig.savefig(a.output,metadata={'Date':None});plt.close(fig)

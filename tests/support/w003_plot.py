"""Plot W004 local geometry and distinct support/special scopes, not an oracle."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 spec=json.loads((a.fixture/'spec.json').read_text());ctx=json.loads((a.fixture/'body/context.json').read_text());cut=json.loads((a.fixture/'special/cut_islands/spec.json').read_text())
 colors={'BODY_N':'#c8e4f5','BODY_P':'#f3d5e1','OD':'#64ac8b','POLY':'#b74350','FIN':'#485263','M1':'#5687c0','LI':'#d49c43','CUT':'#d74b4b','BOUNDARY':'#29384a','CONTACT':'#333333','VIA0':'#74529c','GCONTACT':'#74529c','BTAP_N':'#633e8b','BTAP_P':'#633e8b','MARKER':'#777777'}
 fig,axes=plt.subplots(1,4,figsize=(18,6),gridspec_kw={'width_ratios':[1,1,.85,.85]})
 groups=[{'BOUNDARY','BODY_N','BODY_P','OD','POLY','FIN'}, {'BOUNDARY','M1','LI','CONTACT','VIA0','GCONTACT','MARKER'}, {'BODY_N','BODY_P','M1','BTAP_N','BTAP_P'}, {'LI','CUT'}]
 sets=[spec['shapes'],spec['shapes'],ctx['shapes']+[x for x in spec['shapes'] if x['id'] in ['BN','BP','MN','MP']],cut['shapes']]
 for i,(ax,group,shapes) in enumerate(zip(axes,groups,sets)):
  for s in shapes:
   if s['layer'] not in group:continue
   x,y,x1,y1=s['bbox'];ext=s['id'].endswith('.ext')
   ax.add_patch(Rectangle((x,y),x1-x,y1-y,facecolor='none' if s['layer']=='BOUNDARY' else colors[s['layer']],edgecolor=colors[s['layer']],alpha=.55,linewidth=.8,hatch='//' if ext else None))
   if s['layer'] not in ['FIN','BOUNDARY']:
    if i!=2 or s['id'] in ['TN.ext','TP.ext','MN','MP']:ax.text(x,y1+2,s['id'],fontsize=7)
  ax.set_aspect('equal');ax.set_xlabel('x (nominal nm)');ax.set_ylabel('y (nominal nm)');ax.grid(alpha=.12);ax.set_xlim(-5,165);ax.set_ylim(-5,205)
 axes[0].set_title('Local FIN / active / body');axes[0].text(20,45,'N: 5 crossings',fontsize=9);axes[0].text(20,145,'P: 7 crossings',fontsize=9)
 axes[1].set_title('Local routing: 8 connector edges');axes[1].text(15,15,'No local BTAP',fontsize=10)
 axes[2].set_title('Read-only external context');axes[2].set_xlim(-26,50);axes[2].axvline(0,color='black',ls='--',lw=1);axes[2].text(-23,95,'external | local',fontsize=8)
 axes[3].set_title('Separate CUT / island specimen');axes[3].set_xlim(45,155);axes[3].set_ylim(10,40);axes[3].add_patch(Rectangle((128,16),32,16,facecolor='none',edgecolor='black',ls='--'));axes[3].text(50,34,'A_REMOTE     LB.left / LB.right',fontsize=8);axes[3].text(50,12,'Same A label; 3 components; 2 nm gap',fontsize=8)
 fig.suptitle('INV_M1_SYNTH | 40 local shapes / 6 local components | synthetic expected sample',fontsize=14)
 fig.text(.5,.025,'18 static FIN; 12 qualified crossings. External geometry is not exported. No product or production EDA run.',ha='center',fontsize=10)
 fig.tight_layout(rect=[0,.07,1,.94]);a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=150,metadata={'Software':'W004 fixture review helper'});plt.close(fig)
if __name__=='__main__':main()

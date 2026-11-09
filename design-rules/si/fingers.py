import numpy as np
from fd2d import solve, C0
def zd(layers_below, w, s, t=0.035, dx=0.005, mask=False):
    # layers_below: list top->bottom of (thk, er) ending at reference plane
    def run(sc):
        L=[(dx,1,'gnd')]+[(h,(e if sc else 1),'diel') for h,e in reversed(layers_below)]
        y0=dx+sum(h for h,e in layers_below)
        p=w+s; tr=[(-p/2,w,w-0.02,y0,t,1.0),(p/2,w,w-0.02,y0,t,-1.0)]
        return solve(L,tr,width_x=2*w+s+8*sum(h for h,e in layers_below)+1,dx=dx,top_air=0.6,mask=None)
    W=run(True);W0=run(False); return 2/(C0*np.sqrt(W*W0))
# CEM fingers: 0.70 wide on 1.0 pitch -> gap 0.30 (pads are not a coupled pair geometry exactly; adjacent finger is GND in GSSG)
print("CEM finger, L2 solid (h=0.0994):", zd([(0.0994,4.1)],0.70,0.30))
print("CEM finger, L2 void, ref L3:", zd([(0.0994,4.1),(0.0152,4.1),(0.55,4.6)],0.70,0.30))
print("CEM finger, L2+L3 void, ref L4:", zd([(0.0994,4.1),(0.0152,4.1),(0.55,4.6),(0.0152,4.1),(0.1088,4.16)],0.70,0.30))
print("M.2 finger 0.35/0.15 L2 solid:", zd([(0.0994,4.1)],0.35,0.15))
print("M.2 finger L2 void ref L3 (0.8mm 3313):", zd([(0.0994,4.1),(0.0152,4.1),(0.5,4.6)],0.35,0.15))

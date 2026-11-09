import numpy as np
from fd2d import solve, C0
ETCH=0.0  # set per call
def z_micro(h, er, w, s=None, t=0.035, mask=(3.8,0.0305,0.015), dx=0.005, etch=None):
    """outer microstrip over plane; h=dielectric to plane. etch: top width reduction total (mm)."""
    if etch is None: etch=t*0.6
    def run(scale):
        e=lambda v: v if scale else 1.0
        layers=[(dx,1,'gnd'),(h,e(er),'diel')]
        y0=dx+h
        if s is None: tr=[(0,w,w-etch,y0,t,1.0)]
        else:
            p=w+s; tr=[(-p/2,w,w-etch,y0,t,1.0),(p/2,w,w-etch,y0,t,-1.0)]
        m=(e(mask[0]),mask[1],mask[2],y0) if mask else None
        return solve(layers,tr,width_x=max(2.5,(w*2+(s or 0))+12*h), dx=dx, top_air=0.5, mask=m)
    W=run(True); W0=run(False)
    if s is None: C=2*W; Ca=2*W0; return 1/(C0*np.sqrt(C*Ca))
    return 2/(C0*np.sqrt(W*W0))
def z_strip(h1, er1, h2, er2, w, s=None, t=0.0152, dx=0.0025, etch=None, er_fill=None):
    """stripline: plane / h1 (er1, contains trace, trace sits on top of h1? no: trace sits ON the core below) / h2 / plane.
    Model: bottom plane, dielectric h1 (er1) below trace, trace of thickness t embedded in er2 region, h2 above trace bottom (er2) incl. t, top plane."""
    if etch is None: etch=t*0.6
    def run(scale):
        e=lambda v: v if scale else 1.0
        layers=[(dx,1,'gnd'),(h1,e(er1),'diel'),(h2,e(er2),'diel'),(dx,1,'gnd')]
        y0=dx+h1
        if s is None: tr=[(0,w,w-etch,y0,t,1.0)]
        else:
            p=w+s; tr=[(-p/2,w,w-etch,y0,t,1.0),(p/2,w,w-etch,y0,t,-1.0)]
        return solve(layers,tr,width_x=max(2.5,(w*2+(s or 0))+10*(h1+h2)), dx=dx, top_air=0.0)
    W=run(True); W0=run(False)
    if s is None: C=2*W; Ca=2*W0; return 1/(C0*np.sqrt(C*Ca))
    return 2/(C0*np.sqrt(W*W0))
if __name__=='__main__':
    # sanity: classic 50 ohm microstrip h=0.2104 er=4.4 w~0.35 (JLC calc says ~0.34mm for 7628 4L)
    for dx in (0.01,0.005,0.0025):
        print(dx, z_micro(0.2104,4.4,0.35,dx=dx), z_micro(0.2104,4.4,0.2,0.2,dx=dx))

"""Simple 2D finite-difference quasi-static solver for (coupled) microstrip/stripline.
Returns Z0 (single-ended) and Zdiff (odd mode x2). Units: mm."""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
C0=299792458.0; EPS0=8.854187817e-12

def solve(layers, traces, width_x, dx=0.005, top_air=0.6, mode='diff', mask=None):
    """layers: list from bottom up of (thickness, eps, kind) kind in {'diel','gnd'}.
    traces: list of (xc, w_bottom, w_top, y_bottom, t, volt) (y from bottom of stack).
    mask: (eps, t_over_substrate, t_over_trace, y_surface) or None."""
    H=sum(l[0] for l in layers)+ top_air
    nx=int(round(width_x/dx))+1; ny=int(round(H/dx))+1
    x=np.linspace(-width_x/2,width_x/2,nx); y=np.linspace(0,H,ny)
    X,Y=np.meshgrid(x,y,indexing='ij')
    eps=np.ones((nx,ny)); fixed=np.zeros((nx,ny),bool); V=np.zeros((nx,ny))
    yb=0.0
    for t,e,k in layers:
        sel=(Y>=yb-1e-9)&(Y<=yb+t+1e-9)
        if k=='gnd': fixed|=sel; V[sel]=0
        else: eps[sel]=e
        yb+=t
    if mask is not None:
        me,ts,tt,ys=mask
        sel=(Y>=ys)&(Y<=ys+ts)&(eps==1); eps[sel]=me
    for (xc,wb,wt,y0,t,v) in traces:
        frac=(Y-y0)/t
        half=(wb+(wt-wb)*np.clip(frac,0,1))/2
        sel=(Y>=y0-1e-9)&(Y<=y0+t+1e-9)&(np.abs(X-xc)<=half+1e-9)
        if mask is not None:
            # conformal mask over trace
            me,ts,tt,ys=mask
            if abs(y0-ys)<1e-6:
                hb=half+tt
                sel2=(Y>=y0)&(Y<=y0+t+tt)&(np.abs(X-xc)<=np.maximum(hb,wb/2+tt))&(~sel)&(eps==1)
                eps[sel2]=me
        fixed|=sel; V[sel]=v
    # boundaries grounded (box)
    fixed[0,:]=fixed[-1,:]=True; fixed[:,0]=True; fixed[:,-1]=True
    return _lap(eps,fixed,V,dx)

def _lap(eps,fixed,V,dx):
    nx,ny=eps.shape
    # edge permittivities: average of adjacent cells
    idx=-np.ones((nx,ny),int); free=~fixed; n=free.sum(); idx[free]=np.arange(n)
    rows=[];cols=[];vals=[]; b=np.zeros(n)
    def add(i,j,ii,jj,ex):
        nonlocal rows,cols,vals
    diag=np.zeros(n)
    I,J=np.nonzero(free)
    k=idx[I,J]
    for di,dj in((1,0),(-1,0),(0,1),(0,-1)):
        I2=I+di;J2=J+dj
        e=0.5*(eps[I,J]+eps[I2,J2])
        diag+=e
        f2=free[I2,J2]
        rows.append(k[f2]);cols.append(idx[I2,J2][f2]);vals.append(-e[f2])
        b[~f2]+=e[~f2]*V[I2,J2][~f2]
    rows.append(k);cols.append(k);vals.append(diag)
    A=sp.csr_matrix((np.concatenate(vals),(np.concatenate(rows),np.concatenate(cols))),shape=(n,n))
    sol=spl.spsolve(A.tocsc(),b)
    Vf=V.copy(); Vf[free]=sol
    # energy per unit length: 0.5*eps*|grad V|^2 summed over edges
    ex=0.5*(eps[1:,:]+eps[:-1,:]); ey=0.5*(eps[:,1:]+eps[:,:-1])
    W=0.5*EPS0*(np.sum(ex*np.diff(Vf,axis=0)**2)+np.sum(ey*np.diff(Vf,axis=1)**2))
    return W

def impedance(build, **kw):
    """build(eps_scale) -> (layers,traces,mask); returns Z"""
    pass

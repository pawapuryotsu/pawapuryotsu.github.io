import sys,numpy as np
from tablecmp import dist
def vals(P,W):   # W[n-1][a][x][c][d]
    sr45=0;lv40=P[1:].sum()
    for a in range(7):
        for s in range(1,25):
            x=s-1
            sr45+= P[a,s].sum() if a+x>=5 else (P[a,s]*W[4,a,x]).sum()
            if a==0: lv40+= P[0,s].sum() if x>=3 else (P[0,s]*W[2,0,x]).sum()
    return sr45,lv40
Ps=dist(5)
S=np.fromfile('srtab.bin').reshape(5,35,61)
W0=np.ones((5,5,5,35,61))
for n in range(1,6):
    for a in range(5):
        for x in range(5):
            if n-a-x>0: W0[n-1,a,x]=S[n-a-x-1]
r=np.fromfile(sys.argv[2],dtype=np.float32).reshape(5,5,5,35,61)
e=np.fromfile(sys.argv[1],dtype=np.float32).reshape(35,61,5,5,5).transpose(4,2,3,0,1)
for i,P in enumerate(Ps):
    print(i+1,'周 SR45 なし/方式/検算 %.2f %.2f %.2f | LV40 %.2f %.2f %.2f'%tuple(100*v for T in (0,1) for v in [vals(P,W)[T] for W in (W0,e,r)]))

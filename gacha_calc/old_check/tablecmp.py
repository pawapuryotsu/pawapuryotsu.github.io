# ガチャ（シャンプー）の周回ごとの PSR Lv50 確率を、旧カードなし／ブラウザ用の方式／検算用の計算 で比べる
import json,sys,numpy as np
g=json.load(open('/home/user/pawapuryotsu.github.io/src/gacha/2026_1111_shampoo.json'))
S,C,D=24,34,60
AX={"PSR":0,"SR":1,"PR":2,"R":3}
def shift(P,ax):
    R=np.zeros_like(P);a=[slice(None)]*4;b=[slice(None)]*4;e=[slice(None)]*4
    a[ax]=slice(1,None);b[ax]=slice(None,-1);e[ax]=-1
    R[tuple(a)]+=P[tuple(b)];R[tuple(e)]+=P[tuple(e)];return R
def dist(loops):
    P=np.zeros((7,S+1,C+1,D+1));P[0,0,1,0]=1;out=[]
    for st in range(loops*3):
        for slot in g["steps"][st%3]["slots"]:
            pr={r:p/100*(1 if slot["target"]=="only" else g["share"][r]/100) for r,p in slot["rarity"].items()}
            for _ in range(slot["n"]):
                Q=P*(1-sum(pr.values()))
                for k,p in pr.items(): Q+=p*shift(P,AX[k])
                P=Q
        if st%3==2: out.append(P)
    return out
def val(P,T):
    return P[6].sum()+sum((P[a]*T[5-(a-1)-1]).sum() for a in range(1,6))
if __name__=="__main__":
    Ps=dist(12)
    V0=np.load('p000.npy')
    tabs={'なし':V0}
    for name,f in zip(sys.argv[1::2],sys.argv[2::2]):
        a=np.fromfile(f,dtype=np.float32)
        tabs[name]=a.reshape(5,S+1,C+1,D+1) if 'ref' in f else a.reshape(C+1,D+1,S+1,5).transpose(3,2,0,1)
    print('周',*tabs.keys())
    for i,P in enumerate(Ps): print(i+1,*['%.2f'%(100*val(P,T)) for T in tabs.values()])

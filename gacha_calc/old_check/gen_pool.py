import sys,json
# 旧カードの状態（全部の組み合わせ。育てる旧カードの枚数の制限なし）を列挙して pool.h を書く
pool=json.loads(sys.argv[1]); goal=int(sys.argv[2]); S,C,D=map(int,sys.argv[3:6])
start=tuple(sorted(map(tuple,pool)))
idx={start:0};lst=[start]
def get(P):
    P=tuple(sorted(P))
    if P not in idx: idx[P]=len(lst);lst.append(P)
    return idx[P]
i=0;REM=[];UP=[]
while i<len(lst):
    P=lst[i];rem=[];up=[]
    for j,c in enumerate(P):
        rem.append(get(P[:j]+P[j+1:]))
        up.append([0]+[get(P[:j]+((c[0],min(5,c[1]+d)),)+P[j+1:]) for d in (1,2,3)])
    REM.append(rem);UP.append(up);i+=1
n=len(lst);mc=max(1,max(len(P) for P in lst))
pad=lambda a,z: a+[z]*(mc-len(a))
h=f"#define NPI {n}\n#define S {S}\n#define C {C}\n#define D {D}\n#define GOAL {goal}\n"
h+="static const int NC[NPI]={"+",".join(str(len(P)) for P in lst)+"};\n"
h+=f"static const int CR[NPI][{mc}]={{"+",".join("{"+",".join(map(str,pad([c[0] for c in P],0)))+"}" for P in lst)+"};\n"
h+=f"static const int CL[NPI][{mc}]={{"+",".join("{"+",".join(map(str,pad([c[1] for c in P],0)))+"}" for P in lst)+"};\n"
h+=f"static const int REM[NPI][{mc}]={{"+",".join("{"+",".join(map(str,pad(r,0)))+"}" for r in REM)+"};\n"
h+=f"static const int UP[NPI][{mc}][4]={{"+",".join("{"+",".join("{"+",".join(map(str,u))+"}" for u in pad(up,[0,0,0,0]))+"}" for up in UP)+"};\n"
open('pool.h','w').write(h);print("pool states",n)

# 厳密解（検算用）：手持ちのカード全部（新・旧）を、どの順番・どの組み合わせでも合成できるとして最大の成功確率を求める
import sys
from functools import lru_cache
sys.setrecursionlimit(100000)
LOW=[.3,.33,.36,.39,.42];PP=[.05,.07,.09,.11,.13,.15];DIFF=[.5,.55,.6,.65,1]
SAMEUP=True
def merge(m,t):
    (mv,mr,ml),(tv,tr,tl)=m,t
    if mr==tr:
        if mv==tv: return [(1,1)] if ml==0 or (mv>0 and SAMEUP) else None
        return [(DIFF[ml],1)] if ml<5 else [(.75,3),(.25,2)]
    if mr==tr-1: return [(LOW[ml],1)] if ml<5 else [(.45,2),(.55,1)]
    if tr==3 and mr==1: return [(PP[ml],1)]
    if tr==3 and mr==0: return [(.005,1)]
    if mr==tr+1 and ml==0: return [(1,1)]
    return None
GOAL=None
def done(P):
    if GOAL=='PSR50': return any(c[0]==0 and c[1]==3 and c[2]>=5 for c in P)
    if GOAL=='SR45': return any(c[0]==0 and c[1]==2 and c[2]>=5 for c in P)
    if GOAL=='LV40': return any(c[0]==0 and (c[1]==3 or (c[1]==2 and c[2]>=3)) for c in P)
@lru_cache(None)
def V(P,K):
    if done(P): return 1.0
    best=0.0
    n=len(P)
    for i in range(n):
        if i and P[i]==P[i-1]: continue
        m=P[i]; rest=P[:i]+P[i+1:]
        for j in range(len(rest)):
            if j and rest[j]==rest[j-1]: continue
            t=rest[j]; r=merge(m,t)
            if not r: continue
            v=0; ps=0
            for p,d in r:
                r2=list(rest); r2[j]=(t[0],t[1],min(5,t[2]+d)); v+=p*V(tuple(sorted(r2)),K); ps+=p
            if ps<1: v+=(1-ps)*V(rest,K)
            if v>best: best=v
    for rk in range(4):   # 博士像：同じレアリティを100%で+1
        if K[rk]==0: continue
        K2=list(K); K2[rk]-=1; K2=tuple(K2)
        for j in range(n):
            if (j and P[j]==P[j-1]) or P[j][1]!=rk or P[j][2]>=5: continue
            r2=list(P); r2[j]=(P[j][0],rk,P[j][2]+1); v=V(tuple(sorted(r2)),K2)
            if v>best: best=v
    return best
def solve(goal,new,old,K=(0,0,0,0)):
    """new: dict rank->count (+0). old: list of (rank,lvl). K: 博士像 (PSR,SR,PR,R)"""
    global GOAL; GOAL=goal; V.cache_clear()
    P=[(0,r,0) for r,c in new.items() for _ in range(c)]+[(1,r,l) for r,l in old]
    return V(tuple(sorted(P)),tuple(K))
if __name__=="__main__":
    print(solve('PSR50',{3:1,2:2,1:1},[(3,5)]))

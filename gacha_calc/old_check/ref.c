/* 検算用：今までの計算（上限開放済みの新カードは同じレアリティで1枚だけ育てる）に、旧カードを「いつでも・どこにでも」合成できる手を足した計算。
   PSR目標・博士像なし。旧カードの状態は pool.h（gen_pool.py が作る）。 */
#include <stdio.h>
#include <stdlib.h>
#include "pool.h"   /* NPI, NC[pi], CR[pi][i], CL[pi][i], REM[pi][i], UP[pi][i][d] (d=1..3), S,C,D, GOAL */
static const double LOW[5]={.30,.33,.36,.39,.42};
static const double PP[6]={.05,.07,.09,.11,.13,.15};
static const double DIFF[5]={.5,.55,.6,.65,1};
#define M5(x) ((x)>5?5:(x))
static float *M[NPI];
#if GOAL==3
#define LSZ ((size_t)5*(S+1)*6*(C+1)*6*(D+1)*6)
#define IDX(s) (((((((size_t)(s.n-1)*(S+1)+s.x[2])*6+s.t[2])*(C+1)+s.x[1])*6+s.t[1])*(D+1)+s.x[0])*6+s.t[0])
#else   /* SR目標：x[3]＝新PSRの枚数、x[2]＝ベース以外の新SRの枚数（どちらも0〜4。合計がn以上なら完成） */
#define LSZ ((size_t)5*5*5*(C+1)*6*(D+1)*6)
#define IDX(s) (((((((size_t)(s.n-1)*5+s.x[3])*5+s.x[2])*(C+1)+s.x[1])*6+s.t[1])*(D+1)+s.x[0])*6+s.t[0])
#endif
/* 合成の結果：np 個の (確率, 段階)。0 個なら合成できない */
static int merge(int mr,int mv,int ml,int tr,int tv,int base,double *p,int *dl){
  if(mr==tr){
    if(mv==tv){ if(ml==0||mv>0){p[0]=1;dl[0]=1;return 1;} return 0; }
    if(ml<5){p[0]=DIFF[ml];dl[0]=1;return 1;} p[0]=.75;dl[0]=3;p[1]=.25;dl[1]=2;return 2;
  }
  if(mr==tr-1){ if(ml<5){p[0]=LOW[ml];dl[0]=1;return 1;} p[0]=.45;dl[0]=2;p[1]=.55;dl[1]=1;return 2; }
  if(tr==3&&mr==1){p[0]=PP[ml];dl[0]=1;return 1;}
  if(tr==3&&mr==0){p[0]=.005;dl[0]=1;return 1;}
  if(mr==tr+1&&ml==0&&(mv>0||tv>0||base)){p[0]=1;dl[0]=1;return 1;}   /* 新カード同士の「上のランクを下に」は今までの計算に無いので入れない */
  return 0;
}
typedef struct { int pi,n,x[4],t[4]; } St;   /* x[r], t[r]：r=0 R,1 PR,2 SR,3 PSR の +0 の枚数と育成中のレベル */
static double V(St s){
  if(s.n<=0) return 1.0;
#if GOAL==2
  if(s.x[2]+s.x[3]>=s.n) return 1.0;
#endif
  size_t k=IDX(s);
  if(M[s.pi][k]>=0) return M[s.pi][k];
  double best=0;
  int nc=NC[s.pi];
  /* 素材：0..3 +0の新カード(r)、4..7 育成中の新カード(r)、8.. 旧カード */
  for(int mi=0;mi<8+nc;mi++){
    int mr,mv,ml; St a=s;
    if(mi<4){ mr=mi;mv=0;ml=0; if(s.x[mr]==0) continue; a.x[mr]--; }
    else if(mi<8){ mr=mi-4;mv=0;ml=s.t[mr]; if(ml==0) continue; a.t[mr]=0; }
    else { int i=mi-8; mr=CR[s.pi][i];mv=1;ml=CL[s.pi][i]; a.pi=REM[s.pi][i]; }
    /* 相手：0 ベース、1..3 新カード(r=ti-1：育成中があればそれ、無ければ+0の1枚)、4.. 旧カード */
    int nc2=NC[a.pi];
    for(int ti=0;ti<4+nc2;ti++){
      int tr,tv; double p[2]; int dl[2];
      if(ti==0){ tr=GOAL;tv=0; }
      else if(ti<4){ tr=ti-1;tv=0;
        if(tr>=GOAL) continue;
        if(a.t[tr]==0&&a.x[tr]==0) continue;
        if(a.t[tr]>=5) continue; }
      else { tr=CR[a.pi][ti-4];tv=1; }
      int np=merge(mr,mv,ml,tr,tv,ti==0,p,dl);
      if(!np) continue;
      double v=0,ps=0;
      for(int q=0;q<np;q++){
        St b=a; ps+=p[q];
        if(ti==0) b.n-=dl[q];
        else if(ti<4){ if(b.t[tr]==0) b.x[tr]--; b.t[tr]=M5(b.t[tr]+dl[q]); }
        else b.pi=UP[a.pi][ti-4][dl[q]];
        v+=p[q]*V(b);
      }
      if(ps<1-1e-12) v+=(1-ps)*V(a);
      if(v>best) best=v;
    }
  }
  M[s.pi][k]=(float)best; return best;
}
int main(int argc,char**argv){
  for(int i=0;i<NPI;i++){ M[i]=malloc(LSZ*sizeof(float)); if(!M[i]){fprintf(stderr,"mem\n");return 1;} for(size_t j=0;j<LSZ;j++) M[i][j]=-1; }
  FILE*f=fopen(argv[1],"wb");
  /* 出力：[n-1][SR][PR][R]（最初の旧カードの状態 pi=0、育成中なし） float32 */
#if GOAL==3
  for(int n=1;n<=5;n++)for(int s=0;s<=S;s++)for(int c=0;c<=C;c++)for(int d=0;d<=D;d++){
    St st={0,n,{d,c,s,0},{0,0,0,0}}; float v=(float)V(st); fwrite(&v,4,1,f);
  }
#else   /* [n-1][PSR 0..4][SR 0..4][PR][R] */
  for(int n=1;n<=5;n++)for(int a=0;a<5;a++)for(int s=0;s<5;s++)for(int c=0;c<=C;c++)for(int d=0;d<=D;d++){
    St st={0,n,{d,c,s,a},{0,0,0,0}}; float v=(float)V(st); fwrite(&v,4,1,f);
  }
#endif
  fclose(f); return 0;
}

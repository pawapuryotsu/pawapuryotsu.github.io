/* 上限開放の「完成確率の表」を作る（博士像つき）。
   使い方：
     vtable sr  <out> <KP> <KR>        … SR目標。float64 [kP][kR][n-1][PR 0..C][R 0..D]
     vtable psr <out> <KS> <KP> <KR>   … PSR目標。float32 [kS][kP][kR][n-1][SR 0..S][PR 0..C][R 0..D]
   n＝あと何段階。値＝手持ちを一番成功率が高い順番で合成したときに n 段階以上進む確率。
   博士像（kS,kP,kR＝SR像・PR像・R像の残り枚数）は、そのレアリティのカードを100%で+1する。
   前提：上限開放済みのカードは同じレアリティで同時に1枚だけ育てる。 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#define S 24
#define C 34
#define D 60
static const double LOW[5]={.30,.33,.36,.39,.42};
static const double PP[6]={.05,.07,.09,.11,.13,.15};
static int KS,KP,KR;
#define UP(x) do{ double _v=(x); if(_v>b) b=_v; }while(0)
#define M5(x) ((x)>5?5:(x))

/* ---------- SR目標 ---------- */
static double *MS;
static inline size_t sidx(int n,int c0,int t,int d0,int u,int kp,int kr){
  return (((((((size_t)(n-1)*(C+1)+c0)*6+t)*(D+1)+d0)*6+u)*(KP+1)+kp)*(KR+1)+kr);
}
static double VS(int n,int c0,int t,int d0,int u,int kp,int kr){
  if(n<=0) return 1.0;
  size_t k=sidx(n,c0,t,d0,u,kp,kr);
  if(MS[k]>=0) return MS[k];
  double b=0,p;
  /* PR -> SR */
  if(c0>0) UP(.3*VS(n-1,c0-1,t,d0,u,kp,kr)+.7*VS(n,c0-1,t,d0,u,kp,kr));
  if(t>0){ if(t==5) UP(.45*VS(n-2,c0,0,d0,u,kp,kr)+.55*VS(n-1,c0,0,d0,u,kp,kr));
           else { p=LOW[t]; UP(p*VS(n-1,c0,0,d0,u,kp,kr)+(1-p)*VS(n,c0,0,d0,u,kp,kr)); } }
  /* PR -> 育成中のPR */
  if(c0>0&&t>0&&t<5) UP(VS(n,c0-1,t+1,d0,u,kp,kr));
  if(c0>1&&t==0) UP(VS(n,c0-2,1,d0,u,kp,kr));
  /* PR像 */
  if(kp>0){ if(t>0&&t<5) UP(VS(n,c0,t+1,d0,u,kp-1,kr)); if(t==0&&c0>0) UP(VS(n,c0-1,1,d0,u,kp-1,kr)); }
  /* R -> PR（育成中のPRがあればそれに、無ければPR+0に） */
  if(t<5&&(t>0||c0>0)){
    int base=t, cc=t>0?c0:c0-1;
    #define SRES(g) ( (base+(g))>0 ? VS(n,cc,M5(base+(g)),dd,uu,kp,kr) : VS(n,cc+1,0,dd,uu,kp,kr) )
    if(d0>0){ int dd=d0-1,uu=u; UP(.3*SRES(1)+.7*SRES(0)); }
    if(u>0){ int dd=d0,uu=0; if(u==5) UP(.45*SRES(2)+.55*SRES(1)); else { p=LOW[u]; UP(p*SRES(1)+(1-p)*SRES(0)); } }
  }
  /* R -> 育成中のR */
  if(d0>0&&u>0&&u<5) UP(VS(n,c0,t,d0-1,u+1,kp,kr));
  if(d0>1&&u==0) UP(VS(n,c0,t,d0-2,1,kp,kr));
  /* R像 */
  if(kr>0){ if(u>0&&u<5) UP(VS(n,c0,t,d0,u+1,kp,kr-1)); if(u==0&&d0>0) UP(VS(n,c0,t,d0-1,1,kp,kr-1)); }
  MS[k]=b; return b;
}

/* ---------- PSR目標 ---------- */
static float **LY;
#define LSZ ((size_t)5*(S+1)*6*(C+1)*6*(D+1)*6)
/* 計算する順番：PR像 → R像 → SR像（SR像がいちばん内側）。保持する層を (R像+1)×(SR像+1) 枚にしてディスクを節約する */
static inline int lid(int ks,int kp,int kr){ return (kp*(KR+1)+kr)*(KS+1)+ks; }
static inline size_t pidx(int n,int s0,int ts,int c0,int tp,int d0,int u){
  return ((((((size_t)(n-1)*(S+1)+s0)*6+ts)*(C+1)+c0)*6+tp)*(D+1)+d0)*6+u;
}
static double VP(int n,int s0,int ts,int c0,int tp,int d0,int u,int ks,int kp,int kr){
  if(n<=0) return 1.0;
  float *M=LY[lid(ks,kp,kr)];
  size_t k=pidx(n,s0,ts,c0,tp,d0,u);
  if(M[k]>=0) return M[k];
  double b=0,p;
  #define W(n_,s_,ts_,c_,tp_,d_,u_) VP(n_,s_,ts_,c_,tp_,d_,u_,ks,kp,kr)
  /* -> PSR */
  if(s0>0) UP(.3*W(n-1,s0-1,ts,c0,tp,d0,u)+.7*W(n,s0-1,ts,c0,tp,d0,u));
  if(ts>0){ if(ts==5) UP(.45*W(n-2,s0,0,c0,tp,d0,u)+.55*W(n-1,s0,0,c0,tp,d0,u));
            else { p=LOW[ts]; UP(p*W(n-1,s0,0,c0,tp,d0,u)+(1-p)*W(n,s0,0,c0,tp,d0,u)); } }
  if(c0>0) UP(.05*W(n-1,s0,ts,c0-1,tp,d0,u)+.95*W(n,s0,ts,c0-1,tp,d0,u));
  if(tp>0){ p=PP[tp]; UP(p*W(n-1,s0,ts,c0,0,d0,u)+(1-p)*W(n,s0,ts,c0,0,d0,u)); }
  if(d0>0) UP(.005*W(n-1,s0,ts,c0,tp,d0-1,u)+.995*W(n,s0,ts,c0,tp,d0-1,u));
  if(u>0) UP(.005*W(n-1,s0,ts,c0,tp,d0,0)+.995*W(n,s0,ts,c0,tp,d0,0));
  /* SR -> 育成中のSR */
  if(s0>0&&ts>0&&ts<5) UP(W(n,s0-1,ts+1,c0,tp,d0,u));
  if(s0>1&&ts==0) UP(W(n,s0-2,1,c0,tp,d0,u));
  /* SR像 */
  if(ks>0){ if(ts>0&&ts<5) UP(VP(n,s0,ts+1,c0,tp,d0,u,ks-1,kp,kr)); if(ts==0&&s0>0) UP(VP(n,s0-1,1,c0,tp,d0,u,ks-1,kp,kr)); }
  /* PR -> SR（育成中のSRがあればそれに、無ければSR+0に） */
  if(ts<5&&(ts>0||s0>0)){
    int base=ts, ss=ts>0?s0:s0-1;
    #define PSRES(g) ( (base+(g))>0 ? W(n,ss,M5(base+(g)),cc,tt,d0,u) : W(n,ss+1,0,cc,tt,d0,u) )
    if(c0>0){ int cc=c0-1,tt=tp; UP(.3*PSRES(1)+.7*PSRES(0)); }
    if(tp>0){ int cc=c0,tt=0; if(tp==5) UP(.45*PSRES(2)+.55*PSRES(1)); else { p=LOW[tp]; UP(p*PSRES(1)+(1-p)*PSRES(0)); } }
  }
  /* PR -> 育成中のPR */
  if(c0>0&&tp>0&&tp<5) UP(W(n,s0,ts,c0-1,tp+1,d0,u));
  if(c0>1&&tp==0) UP(W(n,s0,ts,c0-2,1,d0,u));
  /* PR像 */
  if(kp>0){ if(tp>0&&tp<5) UP(VP(n,s0,ts,c0,tp+1,d0,u,ks,kp-1,kr)); if(tp==0&&c0>0) UP(VP(n,s0,ts,c0-1,1,d0,u,ks,kp-1,kr)); }
  /* R -> PR */
  if(tp<5&&(tp>0||c0>0)){
    int base=tp, cc=tp>0?c0:c0-1;
    #define PPRES(g) ( (base+(g))>0 ? W(n,s0,ts,cc,M5(base+(g)),dd,uu) : W(n,s0,ts,cc+1,0,dd,uu) )
    if(d0>0){ int dd=d0-1,uu=u; UP(.3*PPRES(1)+.7*PPRES(0)); }
    if(u>0){ int dd=d0,uu=0; if(u==5) UP(.45*PPRES(2)+.55*PPRES(1)); else { p=LOW[u]; UP(p*PPRES(1)+(1-p)*PPRES(0)); } }
  }
  /* R -> 育成中のR */
  if(d0>0&&u>0&&u<5) UP(W(n,s0,ts,c0,tp,d0-1,u+1));
  if(d0>1&&u==0) UP(W(n,s0,ts,c0,tp,d0-2,1));
  /* R像 */
  if(kr>0){ if(u>0&&u<5) UP(VP(n,s0,ts,c0,tp,d0,u+1,ks,kp,kr-1)); if(u==0&&d0>0) UP(VP(n,s0,ts,c0,tp,d0-1,1,ks,kp,kr-1)); }
  M[k]=(float)b; return b;
}

int main(int argc,char**argv){
  if(argc<5){ fprintf(stderr,"usage: vtable sr out KP KR | vtable psr out KS KP KR\n"); return 1; }
  FILE*f=fopen(argv[2],"wb"); if(!f){ perror("open"); return 1; }
  if(!strcmp(argv[1],"sr")){
    KP=atoi(argv[3]); KR=atoi(argv[4]);
    size_t tot=(size_t)5*(C+1)*6*(D+1)*6*(KP+1)*(KR+1);
    MS=malloc(tot*sizeof(double)); for(size_t i=0;i<tot;i++) MS[i]=-1;
    for(int kp=0;kp<=KP;kp++)for(int kr=0;kr<=KR;kr++)for(int n=1;n<=5;n++)for(int c=0;c<=C;c++)for(int d=0;d<=D;d++){
      double v=VS(n,c,0,d,0,kp,kr); fwrite(&v,8,1,f);
    }
    fclose(f);
    int n,c0,t,d0,u,kp,kr;   /* 標準入力から個別に問い合わせ：n c0 t d0 u kp kr */
    while(scanf("%d %d %d %d %d %d %d",&n,&c0,&t,&d0,&u,&kp,&kr)==7) printf("%.9f\n",VS(n,c0,t,d0,u,kp,kr));
    return 0;
  }
  KS=atoi(argv[3]); KP=atoi(argv[4]); KR=atoi(argv[5]);
  int NL=(KS+1)*(KP+1)*(KR+1), keep=(KR+1)*(KS+1);
  const size_t OUT=(size_t)5*(S+1)*(C+1)*(D+1);   /* 1層ぶんの出力の個数。出力は [SR像][PR像][R像] の順に並べる */
  LY=calloc(NL,sizeof(float*));
  for(int kp=0;kp<=KP;kp++)for(int kr=0;kr<=KR;kr++)for(int ks=0;ks<=KS;ks++){
    int id=lid(ks,kp,kr);
    if(id-keep-1>=0 && LY[id-keep-1]){ LY[id]=LY[id-keep-1]; LY[id-keep-1]=NULL; }   /* もう使わない層の領域を再利用 */
    else {   /* 一時ファイルに割り付ける（メモリが足りないときはディスクに逃がせるように） */
      char fn[1024]; snprintf(fn,sizeof fn,"%s.ring%d",argv[2],id);
      int fd=open(fn,O_RDWR|O_CREAT|O_TRUNC,0600);
      if(fd<0||ftruncate(fd,LSZ*sizeof(float))){ perror("ring"); return 1; }
      LY[id]=mmap(NULL,LSZ*sizeof(float),PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
      close(fd); unlink(fn);
      if(LY[id]==MAP_FAILED){ perror("mmap"); return 1; }
    }
    float *M=LY[id]; for(size_t i=0;i<LSZ;i++) M[i]=-1;
    for(int n=1;n<=5;n++)for(int s0=0;s0<=S;s0++)for(int ts=0;ts<6;ts++)for(int c0=0;c0<=C;c0++)for(int tp=0;tp<6;tp++)for(int d0=0;d0<=D;d0++)for(int u=0;u<6;u++)
      VP(n,s0,ts,c0,tp,d0,u,ks,kp,kr);
    fseeko(f,(off_t)(((size_t)ks*(KP+1)+kp)*(KR+1)+kr)*OUT*4,SEEK_SET);
    for(int n=1;n<=5;n++)for(int s=0;s<=S;s++)for(int c=0;c<=C;c++)for(int d=0;d<=D;d++){
      float v=M[pidx(n,s,0,c,0,d,0)]; fwrite(&v,4,1,f);
    }
    fflush(f);
    fprintf(stderr,"layer %d/%d (SR像%d PR像%d R像%d)\n",id+1,NL,ks,kp,kr);
  }
  fclose(f);
  return 0;
}

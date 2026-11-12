#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define S 24
#define C 34
#define D 60
static float *M;
static const double LOW[5]={.30,.33,.36,.39,.42};
static const double PP[6]={.05,.07,.09,.11,.13,.15};
static inline size_t idx(int n,int s0,int ts,int c0,int tp,int d0,int u){
  return ((((((size_t)(n-1)*(S+1)+s0)*6+ts)*(C+1)+c0)*6+tp)*(D+1)+d0)*6+u;
}
int NOR=0; /* 1: R同士の合成を禁止(比較用) */
double V(int n,int s0,int ts,int c0,int tp,int d0,int u){
  if(n<=0) return 1.0;
  size_t k=idx(n,s0,ts,c0,tp,d0,u);
  if(M[k]>=0) return M[k];
  double b=0,v,p;
  /* into PSR */
  if(s0>0){ v=.3*V(n-1,s0-1,ts,c0,tp,d0,u)+.7*V(n,s0-1,ts,c0,tp,d0,u); if(v>b)b=v; }
  if(ts>0){ if(ts==5) v=.45*V(n-2,s0,0,c0,tp,d0,u)+.55*V(n-1,s0,0,c0,tp,d0,u);
            else { p=LOW[ts]; v=p*V(n-1,s0,0,c0,tp,d0,u)+(1-p)*V(n,s0,0,c0,tp,d0,u);} if(v>b)b=v; }
  if(c0>0){ v=.05*V(n-1,s0,ts,c0-1,tp,d0,u)+.95*V(n,s0,ts,c0-1,tp,d0,u); if(v>b)b=v; }
  if(tp>0){ p=PP[tp]; v=p*V(n-1,s0,ts,c0,0,d0,u)+(1-p)*V(n,s0,ts,c0,0,d0,u); if(v>b)b=v; }
  if(d0>0){ v=.005*V(n-1,s0,ts,c0,tp,d0-1,u)+.995*V(n,s0,ts,c0,tp,d0-1,u); if(v>b)b=v; }
  if(u>0){ v=.005*V(n-1,s0,ts,c0,tp,d0,0)+.995*V(n,s0,ts,c0,tp,d0,0); if(v>b)b=v; }
  /* SR copy -> training SR */
  if(s0>0&&ts>0&&ts<5){ v=V(n,s0-1,ts+1,c0,tp,d0,u); if(v>b)b=v; }
  if(s0>1&&ts==0){ v=V(n,s0-2,1,c0,tp,d0,u); if(v>b)b=v; }
  /* PR -> SR (target: training SR if exists else an SR+0) */
  if(ts<5 && (ts>0||s0>0)){
    int base=ts, ss=ts>0?s0:s0-1;
    #define SRRES(g) ( (base+(g))>0 ? V(n,ss,(base+(g))>5?5:base+(g),cc,tt,d0,u) : V(n,ss+1,0,cc,tt,d0,u) )
    if(c0>0){ int cc=c0-1,tt=tp; v=.3*SRRES(1)+.7*SRRES(0); if(v>b)b=v; }
    if(tp>0){ int cc=c0,tt=0; if(tp==5) v=.45*SRRES(2)+.55*SRRES(1); else { p=LOW[tp]; v=p*SRRES(1)+(1-p)*SRRES(0);} if(v>b)b=v; }
  }
  /* PR copy -> training PR */
  if(c0>0&&tp>0&&tp<5){ v=V(n,s0,ts,c0-1,tp+1,d0,u); if(v>b)b=v; }
  if(c0>1&&tp==0){ v=V(n,s0,ts,c0-2,1,d0,u); if(v>b)b=v; }
  /* R -> PR */
  if(tp<5 && (tp>0||c0>0)){
    int base=tp, cc=tp>0?c0:c0-1;
    #define PRRES(g) ( (base+(g))>0 ? V(n,s0,ts,cc,(base+(g))>5?5:base+(g),dd,uu) : V(n,s0,ts,cc+1,0,dd,uu) )
    if(d0>0){ int dd=d0-1,uu=u; v=.3*PRRES(1)+.7*PRRES(0); if(v>b)b=v; }
    if(u>0){ int dd=d0,uu=0; if(u==5) v=.45*PRRES(2)+.55*PRRES(1); else { p=LOW[u]; v=p*PRRES(1)+(1-p)*PRRES(0);} if(v>b)b=v; }
  }
  /* R copy -> training R */
  if(!NOR){
  if(d0>0&&u>0&&u<5){ v=V(n,s0,ts,c0,tp,d0-1,u+1); if(v>b)b=v; }
  if(d0>1&&u==0){ v=V(n,s0,ts,c0,tp,d0-2,1); if(v>b)b=v; }
  }
  M[k]=(float)b; return b;
}
int main(int argc,char**argv){
  if(argc>2) NOR=atoi(argv[2]);
  size_t tot=(size_t)5*(S+1)*6*(C+1)*6*(D+1)*6;
  M=malloc(tot*sizeof(float)); for(size_t i=0;i<tot;i++) M[i]=-1;
  FILE*f=fopen(argv[1],"wb");
  for(int n=1;n<=5;n++)for(int s=0;s<=S;s++)for(int c=0;c<=C;c++)for(int d=0;d<=D;d++){
    float v=(float)V(n,s,0,c,0,d,0); fwrite(&v,4,1,f);
  }
  fclose(f);
  /* interactive queries from stdin: n s0 ts c0 tp d0 u */
  int n,s0,ts,c0,tp,d0,u;
  while(scanf("%d %d %d %d %d %d %d",&n,&s0,&ts,&c0,&tp,&d0,&u)==7) printf("%.5f\n",V(n,s0,ts,c0,tp,d0,u));
  return 0;
}

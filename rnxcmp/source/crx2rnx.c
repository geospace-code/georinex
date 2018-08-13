/****************************************************************************/
/*     program name : CRX2RNX                                               */
/*                                                                          */
/*     Program to recover the RINEX file from Compact RINEX file            */
/*     Created by Yuki HATANAKA / Geospatial Information Authority of Japan */
/*                                                                          */
/*     ver.                                                                 */
/*     4.0.0       2007.01.31 test version   Y. Hatanaka                    */
/*                  - CRINEX 1/3 for RINEX 2.x/3.x                          */
/*     4.0.1       2007.05.08                Y. Hatanaka                    */
/*                  - elimination of supports for VMS and SUN OS 4.1.x      */
/*                  - output not to the current directory but the same      */
/*                    directory as the input file.                          */
/*                  - the same code for DOS and UNIX                        */
/*     4.0.2       2007.06.07                Y. Hatanaka                    */
/*                  - fixing incompatibility of argument and format         */
/*                    string of printf.                                     */
/*     4.0.3       2007.06.21                Y. Hatanaka                    */
/*                  - fixing a bug on lack of carrying the number           */
/*                    between lower and upper digits                        */
/*     4.0.4       2009.06.31                Y. Hatanaka                    */
/*                  - check null pointer in macro CHOP_LF                   */
/*                  - increase MAXTYPE from 30 to 50                        */
/*                  - correct typos in error messages                       */
/*     4.0.5       2012.07.1x                Y. Hatanaka                    */
/*                  - Fixing a bug in displaying error message(#16)         */
/*                  - minor changes to suppress warning messages            */
/*                    at compilation.                                       */
/*                  - check length of input file name                       */
/*     4.0.6       2014.03.24                Y. Hatanaka                    */
/*                  - Fixing a bug in outputting epoch lines in case there  */
/*                    are skipped epochs when a corrupted Compact RINEX     */
/*                    ver. 3 files are processed with the option "-s".      */
/*                  - "include" statements are moved to the top.            */
/*                  - check and stop with an error if value of data         */
/*                    exceed the range allowed in RINEX format. An hidden   */
/*                    option to keep output in such a case is also added.   */
/*                  - Manipulation of file names in the new file naming     */
/*                    convention (*.rnx/crx) is added.                      */
/*     4.0.7       2015.XX.XX                Y. Hatanaka                    */
/*                  - increase the following constants                      */
/*                       MAXSAT        90     -> 100                        */
/*                       MAXTYPE       50     -> 100                        */
/*                       MAXCLM        1024   -> 2048                       */
/*                       MAX_BUFF_SIZE 131072 -> 204800                     */
/*     Copyright (c) 2007 Geospatial Information Authority of Japan         */
/*     All rights reserved.                                                 */
/*                                                                          */
/****************************************************************************/

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#define VERSION  "ver.4.0.7"

/**** Exit codes are defined here. ****/
#ifndef EXIT_SUCCESS
#define EXIT_SUCCESS 0
#endif

#ifndef EXIT_FAILURE
#define EXIT_FAILURE 1
#endif

#define EXIT_WARNING 2

/*** define macros ***/
/* #define CHOP_LF(q,p) p = strchr(q,'\n'); *p = '\0'; */
#define CHOP_LF(q,p) p = strchr(q,'\n'); if(p != NULL){if( *(p-1) == '\r' && p>q )p--;*p = '\0';}
#define CHOP_BLANK(q,p) p = strchr(q,'\0');while(*--p == ' ' && p>q);*++p = '\0'

/* define global constants */
#define PROGNAME "CRX2RNX"
#define MAXSAT    100         /* Maximum number of satellites observed at one epoch */
#define MAXTYPE   100         /* Maximum number of data types   */
#define MAXCLM   2048         /* Maximum columns in one line   (>MAXTYPE*19+3)  */
#define MAX_BUFF_SIZE 204800  /* Maximum size of output buffer (>MAXSAT*(MAXTYPE*19+4)+60 */
#define MAX_DIFF_ORDER 5      /* Maximum order of difference to be dealt with */

/* define data structure for fields of clock offset and observation records */
typedef struct clock_format{
    long u[MAX_DIFF_ORDER+1];      /* upper X digits for each difference order */
    long l[MAX_DIFF_ORDER+1];      /* lower 8 digits */
} clock_format;

typedef struct data_format{
    long u[MAX_DIFF_ORDER+1];      /* upper X digits for each difference order */
    long l[MAX_DIFF_ORDER+1];      /* lower 5 digits */
    int  order;
    int  arc_order;
} data_format;

/* define global variables */
clock_format clk1,clk0;
data_format dy1[MAXSAT][MAXTYPE],dy0[MAXSAT][MAXTYPE];
char flag1[MAXSAT][MAXTYPE*2+1],flag[MAXSAT][MAXTYPE*2+1];

int rinex_version,crinex_version;
int nsat,ntype,ntype_gnss[UCHAR_MAX],ntype_record[MAXSAT],clk_order = 0, clk_arc_order = 0;
char ep_top_from,ep_top_to;
long nl_count = 0;
int skip = 0;
int output_overflow = 0;
int exit_status = EXIT_SUCCESS;
size_t C1 = sizeof("");               /* size of one character */
size_t C2 = sizeof(" ");              /* size of 2-character string */
size_t C3 = sizeof("  ");             /* size of 3-character string */

char out_buff[MAX_BUFF_SIZE],*p_buff;

/* declaration of functions */
void fileopen(int argc, char *argv[]);
void header(void);
int  put_event_data(char *dline, char *p_event);
void skip_to_next(char *dline);
void process_clock(void);
void set_sat_table(char *p_new, char *p_old, int nsat1, int *sattbl);
void data(char *p_sat_lst, int *sattbl, char dflag[][MAXTYPE*2]);
void repair(char *s, char *ds);
int  getdiff(data_format *y, data_format *dy0, int i0, char *dflag);
void putfield(data_format *y, char *flag);
void read_clock(char *dline ,long *yu, long *yl);
void print_clock(long yu, long yl, int shift_clk);
int  read_chk_line(char *line);
void error_exit(int error_no, char *string);

/*---------------------------------------------------------------------*/
int main(int argc, char *argv[]){
    static char line[MAXCLM] = "", sat_lst_old[MAXSAT*3];
    static int nsat1 = 0, n;

    char dline[MAXCLM],*p;
    int sattbl[MAXSAT],i,j,*i0;
    size_t offset;
    char dflag[MAXSAT][MAXTYPE*2];
    char *p_event,*p_nsat,*p_satlst,shift_clk;
       /* sattbl[i]: order (at the previous epoch) of i-th satellite */
       /* (at the current epoch). -1 is set for the new satellites   */

    fileopen(argc,argv);
    for(i=0;i<UCHAR_MAX;i++)ntype_gnss[i]=-1;  /** -1 unless GNSS type is defined **/
    header();
    if (rinex_version==2){
        ep_top_from = '&';
        ep_top_to   = ' ';
        p_event   = &dline[28];  /** pointer to event flug **/
        p_nsat    =  &line[29];  /** pointer to n_sat **/
        p_satlst  =  &line[32];  /** pointer to address to add satellite list **/
        shift_clk = 1;
        offset=3;
    }else{
        ep_top_from = '>';
        ep_top_to =   '>';
        p_event   = &dline[31];
        p_nsat    =  &line[32];
        p_satlst  =  &line[41];
        shift_clk = 4;
        offset=6;
    }

    while( fgets(dline,MAXCLM,stdin) != NULL ){      /*** exit program successfully ***/
        nl_count++;
        CHOP_LF(dline,p);
        SKIP:
        if(crinex_version == 3) { /*** skip escape lines of CRINEX version 3 ***/
            while(dline[0] == '&'){
                nl_count++;
                if( fgets(dline,MAXCLM,stdin) == NULL ) return exit_status;
                CHOP_LF(dline,p);
            }
        }
        if(dline[0] == ep_top_from){
            dline[0] = ep_top_to;
            if(*p_event!='0' && *p_event!='1' ){
                if(put_event_data(dline,p_event)!=0) skip_to_next(dline);
                goto SKIP;
            }
            line[0] = '\0';          /**** initialize arc for epoch data ***/
            nsat1 = 0;               /**** initialize the all satellite arcs ****/
        }else if( dline[0] == '\032' ){
            return exit_status;   /** DOS EOF **/
        }
        /****  read, repair the line  ****/
        repair(line,dline);
        p = &line[offset];  /** pointer to the space between year and month **/
        if(line[0] != ep_top_to || strlen(line)<(26+offset) || *(p+23) != ' '
                             || *(p+24) != ' ' || ! isdigit(*(p+25)) ) {
            skip_to_next(dline);
            goto SKIP;
        }
        CHOP_BLANK(line,p);

        nsat = atoi(p_nsat);
        if(nsat > MAXSAT) error_exit(6,p_nsat);

        set_sat_table(p_satlst,sat_lst_old,nsat1,sattbl); /****  set satellite table  ****/
        if(read_chk_line(dline) != 0) {skip_to_next(dline);goto SKIP;}
        read_clock(dline,clk1.u,clk1.l);
        for(i=0,i0=sattbl ; i<nsat ; i++,i0++){
            ntype = ntype_record[i];
            if( getdiff(dy1[i],dy0[*i0],*i0,dflag[i]) != 0 ) {skip_to_next(dline);goto SKIP;}
        }

        /*************************************/
        /**** print the recovered line(s) ****/
        /*************************************/
        if(dline[0] != '\0') process_clock();
        p_buff = out_buff;

        if(rinex_version == 2){
            if(clk_order >= 0){
                p_buff += sprintf(p_buff,"%-68.68s",line);
                print_clock(clk1.u[clk_order],clk1.l[clk_order],shift_clk);
            }else{
                p_buff += sprintf(p_buff,"%.68s\n",line);
            }
            for(p = &line[68],n=nsat-12; n>0; n-=12,p+=36) p_buff += sprintf(p_buff,"%32.s%.36s\n"," ",p);
        }else{
            if(clk_order >= 0){
                p_buff += sprintf(p_buff,"%.41s",line);
                print_clock(clk1.u[clk_order],clk1.l[clk_order],shift_clk);
            }else{
                sprintf(p_buff,"%.41s",line);
                CHOP_BLANK(p_buff,p);*p++ = '\n';p_buff=p;
            }
        }

        data(p_satlst,sattbl,dflag);

        *p_buff = '\0'; printf("%s",out_buff);
        /****************************/
        /**** save current epoch ****/
        /****************************/
        nsat1 = nsat;
        clk0 = clk1;
        strncpy(sat_lst_old,p_satlst,nsat*C3);
        for(i=0;i<nsat;i++){
            strncpy(flag1[i],flag[i],ntype_record[i]*C2);
            for(j=0;j<ntype_record[i];j++) dy0[i][j] = dy1[i][j];
        }
    }
    return exit_status;
}
/*---------------------------------------------------------------------*/
void fileopen(int argc, char *argv[]){
    char *p,infile[MAXCLM],outfile[MAXCLM],*progname;
    int nfile = 0, force = 0, help = 0;
    int nfout = 0;  /*** =0 default output file name ***/
                    /*** =1 standard output          ***/
    FILE *ifp;

    progname = argv[0];
    argc--;argv++;
    for(;argc>0;argc--,argv++){
        if((*argv)[0] != '-'){
            strncpy(infile,*argv,C1*MAXCLM);
            nfile++;
        }else if(strcmp(*argv,"-")   == 0){
            nfout = 1;
        }else if(strcmp(*argv,"-f")  == 0){
            force = 1;
        }else if(strcmp(*argv,"-s")  == 0){
            skip  = 1;
        }else if(strcmp(*argv,"--output_overflow")  == 0){
            /* output the data without stopping with an error even if  */
            /* digits of an output data exceed the limit of the format */
            /* (a hidden option for checking)                          */
            output_overflow = 1;
        }else if(strcmp(*argv,"-h")  == 0){
            help = 1;
        }else{
            help = 1;
        }
    }

    if(strlen(infile) == MAXCLM)error_exit(14,infile);
    if(help == 1 || nfile > 1  || nfile < 0) error_exit(2,progname);
    if(nfile == 0) return;       /*** stdin & stdout will be used ***/

    /***********************/
    /*** open input file ***/
    /***********************/
    p = strrchr(infile,'.');
    if(p == NULL || *(p+4) != '\0' 
                 || ( toupper(*(p+3)) != 'D'
                      && strcmp(p+1,"CRX") != 0
                      && strcmp(p+1,"crx") != 0 )
    ) error_exit(3,p);

    if((ifp = fopen(infile,"r")) == NULL) error_exit(4,infile);

    /************************/
    /*** open output file ***/
    /************************/
    if(nfout == 0) {
        strcpy(outfile,infile);
        p = strrchr(outfile,'.');
        if     (*(p+3) == 'd') { *(p+3) = 'o';}
        else if(*(p+3) == 'D') { *(p+3) = 'O';}
        else if( strcmp(p+1,"crx") == 0) { strcpy((p+1),"rnx");}
        else if( strcmp(p+1,"CRX") == 0) { strcpy((p+1),"RNX");}
        
        if((freopen(outfile,"r",stdout)) != NULL && force == 0){
            fprintf(stderr,"The file %s already exists. Overwrite?(n)",outfile);
            if(getchar() != 'y') exit(EXIT_SUCCESS);
        }
        freopen(outfile,"w",stdout);
    }
    fclose(ifp);
    freopen(infile,"r",stdin);
}
/*---------------------------------------------------------------------*/
void header(void){
    char line[MAXCLM],*p;
    if( read_chk_line(line) == 1 ) error_exit(5,"1.0-2.0");
    crinex_version = atoi(line);
    if( (strncmp(&line[0],"1.0",C3) != 0 && strncmp(&line[0],"3.0",C3) != 0) ||
         strncmp(&line[60],"CRINEX VERS   / TYPE",C1*19) != 0 ) error_exit(5,"1.0-2.0");
    if( read_chk_line(line) == 1 ) error_exit(8,line);

    if( read_chk_line(line) == 1 ) error_exit(8,line);
    CHOP_BLANK(line,p);
    printf("%s\n",line);
    if(strncmp(&line[60],"RINEX VERSION / TYPE",C1*20) != 0 ||
       (line[5]!='2' && line[5]!='3') ) error_exit(15,"2.x or 3.x");
    rinex_version=atoi(line);

    do {
        read_chk_line(line);
        CHOP_BLANK(line,p);
        printf("%s\n",line);
        if       (strncmp(&line[60],"# / TYPES OF OBSERV",C1*19) == 0 && line[5] != ' '){
             ntype = atoi(line);                                        /** for RINEX2 **/
        } else if(strncmp(&line[60],"SYS / # / OBS TYPES",C1*19) == 0){ /** for RINEX3  **/
             if (line[0] != ' ') ntype_gnss[(unsigned int)line[0]] = atoi(&line[3]);
             if (ntype_gnss[(unsigned int)line[0]] > MAXTYPE) error_exit(16,line);
        }
    }while(strncmp(&line[60],"END OF HEADER",C1*13) != 0);
}
/*---------------------------------------------------------------------*/
void read_clock(char *dline, long *yu, long *yl){
    char *p,*s,*p1;

    p = dline;

    if(*p == '\0'){
        clk_order = -1;
    }else{
        if(*(p+1) == '&') {        /**** for the case of arc initialization ****/
            sscanf(p,"%d&",&clk_arc_order);
            if(clk_arc_order > MAX_DIFF_ORDER) error_exit(7,dline);
            clk_order = -1;
            p += 2;
        }
        p1 = p; if(*p == '-') p1++;
        s = strchr(p1,'\0');
        if((s-p1) < 9 ){                /** s-p1 == strlen(p1) ***/
            *yu = 0;
            *yl = atol(p);
        }else{
            s -= 8;
            *yl = atol(s);
            *s = '\0';
            *yu = atol(p);
            if(*yu < 0) *yl = -*yl;
        }
    }
}
/*---------------------------------------------------------------------*/
void process_clock(void){
    int i,j;
    /****************************************/
    /**** recover the clock offset value ****/
    /****************************************/
    if(clk_order < clk_arc_order){
        clk_order++;
        for(i=0,j=1 ; i<clk_order ; i++,j++){
            clk1.u[j] = clk1.u[i]+clk0.u[i];
            clk1.l[j] = clk1.l[i]+clk0.l[i];
            clk1.u[j] += clk1.l[j]/100000000;  /*** to avoid overflow of dy1.l ***/
            clk1.l[j] %= 100000000;
        }
    }else{
        for(i=0,j=1 ; i<clk_order ; i++,j++){
            clk1.u[j] = clk1.u[i]+clk0.u[j];
            clk1.l[j] = clk1.l[i]+clk0.l[j];
            clk1.u[j] += clk1.l[j]/100000000;
            clk1.l[j] %= 100000000;
        }
    }
    /* Signs of py1->u and py1->l can be different at this stage */
    /*   and will be adjustied before outputting */
}
/*---------------------------------------------------------------------*/
int  put_event_data(char *dline, char *p_event){
/***********************************************************************/
/*  - Put event data for one event.                                    */
/*  - This function is called when the event flag > 1.                 */
/***********************************************************************/
    int i,n;
    char *p;
    do {
        dline[0] = ep_top_to;
        CHOP_BLANK(dline,p);
        printf("%s\n",dline);
        if( strlen(dline) > 29 ){
            n = atoi((p_event+1));
            for(i=0;i<n;i++){
                read_chk_line(dline);
                CHOP_BLANK(dline,p);
                printf("%s\n",dline);
                if       (strncmp(&dline[60],"# / TYPES OF OBSERV",C1*19) == 0 && dline[5] != ' ' ){
                     ntype = atoi(dline);                                        /** for RINEX2 **/
                } else if(strncmp(&dline[60],"SYS / # / OBS TYPES",C1*19) == 0){ /** for RINEX3 **/
                     if (dline[0] != ' ') ntype_gnss[(unsigned int)dline[0]]=atoi(&dline[3]);
                     if (ntype_gnss[(unsigned int)dline[0]] > MAXTYPE) error_exit(16,dline);
                }
            }
        }

        do {
            nl_count++;
            if(fgets(dline,MAXCLM,stdin) == NULL) exit(exit_status);  /*** eof: exit program successfully ***/
        } while (crinex_version == 3 && dline[0] == '&');
        CHOP_LF(dline,p);

        if(dline[0] != ep_top_from || strlen(dline)<29   || ! isdigit(*p_event) ) {
            if( ! skip ) error_exit(9,dline);
            fprintf(stderr,"WARNING :  The epoch should be initialized, but not.\n");
            return 1;
        }
    }while(*p_event != '0' && *p_event != '1');
    return 0;
}
/*---------------------------------------------------------------------*/
void skip_to_next(char *dline){
    char *p;
    exit_status=EXIT_WARNING;
    fprintf(stderr,"    line %ld : skip until an initialized epoch is found.",nl_count);
    if(rinex_version == 2) {
        p = dline+3;    /** pointer to the space between year and month **/
    }else{
        p = dline+6;
    }

    do {
        nl_count++;
        if(fgets(dline,MAXCLM,stdin) == NULL) {
            fprintf(stderr,"  .....next epoch not found before EOF.\n");
            if(rinex_version == 2) {
                printf("%29d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
            }else{
                printf(">%31d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
            }
            exit(exit_status);
        }
    }while(dline[0] != ep_top_from || strlen(dline) < 29   || *p != ' ' 
              || *(p+3)  != ' ' || *(p+6)  != ' ' || *(p+9)  != ' ' 
              || *(p+12) != ' ' || *(p+23) != ' ' || *(p+24) != ' ' 
              || ! isdigit(*(p+25)) );

    CHOP_LF(dline,p);
    fprintf(stderr,"  .....next epoch found at line %ld.\n",nl_count);
    if(rinex_version == 2) {
        printf("%29d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
    }else{
        printf(">%31d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
    }

}
/*---------------------------------------------------------------------*/
void set_sat_table(char *p_new, char *p_old, int nsat1, int *sattbl){
/***********************************************************************/
/*  - Read number of satellites (nsat)                                 */
/*  - Compare the satellite list at the epoch (*p_new) and that at the */
/*    previous epoch(*p_old), and make index (*sattbl) for the         */
/*    corresponding order of the satellites.                           */
/*    *sattbl is set to -1 for new satellites.                         */
/***********************************************************************/
    int i,j;
    char *ps;

    /*** set # of data types for each satellite ***/
    if(rinex_version == 2 ) {             /** for RINEX2 **/
        for (i=0 ; i<nsat ; i++){ ntype_record[i]=ntype; }
    }else{                                /** for RINEX3 **/
        for (i=0,ps=p_new ; i<nsat ; i++,ps+=3){
            ntype_record[i] = ntype_gnss[(unsigned int)*ps];  /*** # of data type for the GNSS system ***/
            if(ntype_record[i]<0)error_exit(20,p_new);
        }
    }
    for (i=0; i<nsat ; i++,p_new+=3){
        *sattbl = -1;
        for(j=0,ps=p_old ; j<nsat1 ; j++,ps+=3){
            if(strncmp(p_new,ps,C3) == 0){
                *sattbl = j;
                break;
            }
        }
        sattbl++;
    }
}
/*---------------------------------------------------------------------*/
void data(char *p_sat_lst, int *sattbl, char dflag[][MAXTYPE*2]){
/********************************************************************/
/*  Functions                                                       */
/*      (1) compose the original data from 3rd order difference     */
/*      (2) repair the flags                                        */
/*  sattbl : previous column on which the satellites are set        */
/*           new satellites are set to -1                           */
/*       u : upper X digits of the data                             */
/*       l : lower 5 digits of the data                             */
/*            ( y = u*100 + l/1000)                                 */
/*   date of previous epoch are set to dy0                           */
/********************************************************************/
    data_format *py1,*py0;
    int  i,j,k,k1,*i0;
    char *p;

    for(i=0,i0=sattbl,p=p_sat_lst ; i<nsat ; i++,i0++,p+=3){
        /**** set # of data types for the GNSS type    ****/
        /**** and write satellite ID in case of RINEX3 ****/
        /**** ---------------------------------------- ****/
        if(rinex_version == 3 ){
            ntype = ntype_record[i];
            strncpy(p_buff,p,C3);
            p_buff += 3;
        }
        /**** repair the data flags ****/
        /**** ----------------------****/
        if(*i0 < 0){       /* new satellite */
            if(rinex_version == 3 ){
                *flag[i] = '\0';
            }else{
                sprintf(flag[i],"%-*s",ntype*2,dflag[i]);
            }
        }else{
            strncpy(flag[i],flag1[*i0],ntype*C2);
        }
        repair(flag[i],dflag[i]);

        /**** recover the date, and output ****/
        /**** ---------------------------- ****/
        for(j=0,py1=dy1[i] ; j<ntype ; j++,py1++){
            if(py1->arc_order >= 0){
                py0 = &(dy0[*i0][j]);
                if(py1->order < py1->arc_order){
                    (py1->order)++;
                    for(k=0,k1=1; k<py1->order; k++,k1++){
                        py1->u[k1] = py1->u[k] + py0->u[k];
                        py1->l[k1] = py1->l[k] + py0->l[k];
                        py1->u[k1] += py1->l[k1]/100000;  /*** to avoid overflow of dy1.l ***/
                        py1->l[k1] %= 100000;
                    }
                }else{
                    for(k=0,k1=1; k<py1->order; k++,k1++){
                        py1->u[k1] = py1->u[k] + py0->u[k1];
                        py1->l[k1] = py1->l[k] + py0->l[k1];
                        py1->u[k1] += py1->l[k1]/100000;
                        py1->l[k1] %= 100000;
                    }
                }
                /* Signs of py1->u and py1->l can be different at this stage */
                /*   and will be adjusted before outputting                 */
                putfield(py1,&flag[i][j*2]);
            }else{
                if (crinex_version == 1 ) {                       /*** CRINEX 1 assumes that flags are always ***/
                    p_buff += sprintf(p_buff,"                "); /*** blank if data field is blank           ***/
                    flag[i][j*2] = flag[i][j*2+1] = ' ';
                }else{                                            /*** CRINEX 3 evaluate flags independently **/
                    p_buff += sprintf(p_buff,"              %c%c",flag[i][j*2],flag[i][j*2+1]);
                }
            }
            if((j+1) == ntype || (rinex_version==2 && (j+1)%5 == 0 ) ){
                while(*--p_buff == ' '){}; p_buff++;  /*** cut spaces ***/
                *p_buff++ = '\n';
            }
        }
    }
}
/*---------------------------------------------------------------------*/
void repair(char *s, char *ds){
    for(; *s != '\0' && *ds != '\0' ; ds++,s++){
        if(*ds == ' ')continue;
        if(*ds == '&')
            *s = ' ';
        else
            *s = *ds;
    }
    if(*ds != '\0') {
        sprintf(s,"%s",ds);
        for(; *s != '\0' ;s++) {
            if(*s == '&') *s = ' ';
        }
    }
}
/*---------------------------------------------------------------------*/
int  getdiff(data_format *y, data_format *dy0, int i0, char *dflag){
    int j,length;
    char *s,*s1,*s2,line[MAXCLM];

    /******************************************/
    /****  separate the fields with '\0'   ****/
    /******************************************/
    if(read_chk_line(line)!=0) return 1;
    for(j=0,s=line; j<ntype; s++){
        if(*s == '\0') {
            j++;
            *(s+1) = '\0';
        }else if(*s == ' '){
            j++;
            *s = '\0';
        }
    }
    strcpy(dflag,s);

    /************************************/
    /*     read the differenced data    */
    /************************************/
    s1 = line;
    for(j=0;j<ntype;j++,y++,dy0++){
        if(*s1 == '\0'){
            y->arc_order = -1;      /**** arc_order < 0 means that the field is blank ****/
            y->order = -1;
            s1++;
        }else{
            if(*(s1+1) == '&'){     /**** arc initialization ****/
                y->order = -1;
                y->arc_order = atoi(s1);
                s1 += 2;
                if(y->arc_order > MAX_DIFF_ORDER) error_exit(7,line);
            }else if(i0 < 0){
                if( ! skip ) error_exit(11,line);
                fprintf(stderr,"WARNING : New satellite, but data arc is not initialized.\n");
                return 1;
            }else if(dy0->arc_order < 0){
                if( ! skip ) error_exit(12,line);
                fprintf(stderr,"WARNING : New data sequence but without initialization.\n");
                return 1;
            }else{
                y->order = dy0->order;
                y->arc_order = dy0->arc_order;
            }
            length = (s2=strchr(s1,'\0'))-s1;
            if(*s1 == '-') length--;
            if(length < 6){ 
                y->u[0] = 0;
                y->l[0] = atol(s1);
            }else{
                s = s2-5;
                y->l[0] = atol(s); *s = '\0';
                y->u[0] = atol(s1);
                if(y->u[0] < 0) y->l[0] = -y->l[0];
            }
            s1 = s2+1;
        }
    }
    return 0;
}
/*---------------------------------------------------------------------*/
void putfield(data_format *y, char *flag){
    int  i;

    i = y->order;

    if(y->u[i]<0 && y->l[i]>0){
        y->u[i]++ ; y->l[i] -= 100000 ;
    }else if(y->u[i]>0 && y->l[i]<0){
        y->u[i]-- ; y->l[i] += 100000 ;
    }
    /* The signs of y->u and y->l are the same (or zero) at this stage */

    if(y->u[i]!=0){                                    /* ex) 123.456  -123.456 */
       p_buff += sprintf(p_buff,"%8ld %5.5ld%c%c",y->u[i],labs(y->l[i]),*flag,*(flag+1));
       p_buff[-8] = p_buff[-7];
       p_buff[-7] = p_buff[-6];
       if( y->u[i] > 99999999 || y->u[i] < -9999999 ){
          if( output_overflow ) {
             fprintf(stderr,"Warning: line %ld. : Data record becomes out of range allowed in the RINEX format. The output is corrupted.\n",nl_count);
             exit_status=EXIT_WARNING;
          }else{
             error_exit(17,"Data record");
          }
       }
    }else{
       p_buff += sprintf(p_buff,"         %5.5ld%c%c",labs(y->l[i]),*flag,*(flag+1));
       if (p_buff[-7] != '0' ){                        /* ex)  12.345    -2.345 */
           p_buff[-8] = p_buff[-7];
           p_buff[-7] = p_buff[-6];
           if(y->l[i] <0) p_buff[-9]='-';
       }else if (p_buff[-6] != '0' ){                  /* ex)   1.234    -1.234 */
           p_buff[-7] = p_buff[-6];
           p_buff[-8] = (y->l[i] <0)? '-':' ';
       }else{                                          /* ex)    .123     -.123 */
           p_buff[-7] = (y->l[i] <0)? '-':' ';
       }
    }
    p_buff[-6] = '.';
}
/*---------------------------------------------------------------------*/
void print_clock(long yu, long yl, int shift_clk){
    char tmp[8],*p_tmp,*p;
    int n,sgn;

    if(yu<0 && yl>0){
        yu++ ; yl -= 100000000;
    }else if(yu>0 && yl<0){
        yu-- ; yl += 100000000;
    }
    /* The signs of yu and yl are the same (or zero) at this stage */

    /** add ond more digit to handle '-0'(RINEX2) or '-0000'(RINEX3) **/
    sgn = (yl<0) ? -1:1;
    n = sprintf(tmp,"%.*ld",shift_clk+1,yu*10+sgn); /** AT LEAST fractional parts are filled with 0 **/
    n--;                           /** n: number of digits excluding the additional digit **/
    p_tmp = &tmp[n];
    *p_tmp = '\0';
    p_tmp -= shift_clk;       /** pointer to the top of last "shift_clk" digits **/
    p_buff += sprintf(p_buff,"  .%s",p_tmp);  /** print last "shift_clk" digits.  **/
    if( n > shift_clk ){
        p_tmp--;
        p = p_buff-shift_clk-2;
        *p = *p_tmp;

        if( n > shift_clk+1 ){
             *(p-1) =* (p_tmp-1);
             if( n > shift_clk+2 ){
                 if( output_overflow ) {
                    fprintf(stderr,"Warning: line %ld. : Clock offset becomes out of range allowed in the RINEX format. The output is corrupted.\n",nl_count);
                    exit_status=EXIT_WARNING;
                 }else{
                    error_exit(17,"Clock offset");
                 }
             }
        }
    }

    p_buff += sprintf(p_buff,"%8.8ld\n",labs(yl));
}
/*---------------------------------------------------------------------*/
int  read_chk_line(char *line){
    char *p;
 
    nl_count++;
    if( fgets(line,MAXCLM,stdin) == NULL ) error_exit(8,line);
    if( (p = strchr(line,'\n')) == NULL) {
        if( fgetc(stdin) == EOF ) {     /** check if EOF is there **/
            error_exit(8,line);
        }else{
            if( ! skip ) error_exit(13,line);
            return 1;
        }
    }
    if( *(p-1) == '\n' )p--;
    if( *(p-1) == '\r' )p--;   /*** check DOS CR/LF ***/
    *p = '\0';
    return 0;
}
/*---------------------------------------------------------------------*/
void error_exit(int error_no, char *string){
    if(error_no == 1 ){
        fprintf(stderr,"Usage: %s input file [-o output file] [-f] [-s] [-h]\n",string);
        fprintf(stderr,"    output file name can be omitted if input file name is *.[yy]d\n");
    }else if(error_no == 2 ){
        fprintf(stderr,"Usage: %s [file] [-] [-f] [-s] [-h]\n",string);
        fprintf(stderr,"    stdin and stdout are used if input file name is not given.\n");
    }
    if(error_no == 1 || error_no == 2){
        fprintf(stderr,"    -  : output to stdout\n");
        fprintf(stderr,"    -f : force overwrite of output file\n");
        fprintf(stderr,"    -s : skip strange epochs (default:stop with error)\n");
        fprintf(stderr,"           This option may be used for salvaging usable data when middle of\n");
        fprintf(stderr,"           the Compact RINEX file is missing. The data after the missing part,\n");
        fprintf(stderr,"           are, however, useless until the compression operation of all data\n");
        fprintf(stderr,"           are initialized at some epoch. Combination with use of -e option\n");
        fprintf(stderr,"           of RNX2CRX (ver.4.0 or after) may be effective.\n");
        fprintf(stderr,"           Caution : It is assumed that no change in # of data types\n");
        fprintf(stderr,"                     happens in the lost part of the data.\n");
        fprintf(stderr,"    -h : display help message\n\n");
        fprintf(stderr,"    exit code = %d (success)\n",EXIT_SUCCESS);
        fprintf(stderr,"              = %d (error)\n",  EXIT_FAILURE);
        fprintf(stderr,"              = %d (warning)\n",EXIT_WARNING);
        fprintf(stderr,"    [version : %s]\n",VERSION);
        exit(EXIT_FAILURE);
    }
    if(error_no == 3 ){
        fprintf(stderr,"ERROR : invalid file name  %s\n",string);
        fprintf(stderr,"The extension of the input file name should be [.xxd] or [.crx].\n");
        fprintf(stderr,"To convert the files whose name is not fit to the above conventions,\n");
        fprintf(stderr,"use of this program as a filter is also possible. \n");
        fprintf(stderr,"    for example)  cat file.in | %s - > file.out\n",PROGNAME);
        exit(EXIT_FAILURE);
    }
    if(error_no == 4 ){
        fprintf(stderr,"ERROR : can't open %s\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 5 ){
        fprintf(stderr,"ERROR : The file format is not Compact RINEX or the version of\n");
        fprintf(stderr,"        the format is not valid. This software can deal with\n");
        fprintf(stderr,"        only Compact RINEX format ver.%s.\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 6 ){
        fprintf(stderr,"ERROR at line %ld : exceed maximum number of satellites(%d)\n",nl_count,MAXSAT);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 7 ){
        fprintf(stderr,"ERROR at line %ld : exceed maximum order of difference (%d)\n",nl_count,MAX_DIFF_ORDER);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 8 ){
        fprintf(stderr,"ERROR : The file seems to be truncated in the middle.\n");
        fprintf(stderr,"        The conversion is interrupted after reading the line %ld :\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 9 ){
        fprintf(stderr,"ERROR at line %ld : The arc should be initialized, but not.\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 11){
        fprintf(stderr,"ERROR at line %ld : New satellite, but data arc is not initialized.\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 12){
        fprintf(stderr,"ERROR at line %ld : The data field in previous epoch is blank, but the arc is not initialized.\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 13){
        fprintf(stderr,"ERROR at line %ld : null character is found in the line or the line is too long (>%d) at line.\n",nl_count,MAXCLM);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 14 ){
        fprintf(stderr,"ERROR at line %ld. : Length of file name exceed MAXCLM(%d).\n",nl_count,MAXCLM);
        fprintf(stderr,"     start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 15 ){
        fprintf(stderr,"ERROR : The format version of the original RINEX file is not valid.\n");
        fprintf(stderr,"         This software can deal with only (compressed) RINEX format ver.%s.\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 16 ){
        fprintf(stderr,"ERROR at line %ld. : Number of data types exceed MAXTYPE(%d).\n",nl_count,MAXTYPE);
        fprintf(stderr,"     start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 17 ){
        fprintf(stderr,"ERROR at line %ld. : %s becomes out of range allowed in the RINEX format.\n",nl_count,string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 20 ){
        fprintf(stderr,"ERROR at line %ld. : A GNSS type not defined in the header is found.\n",nl_count);
        fprintf(stderr,"     start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }

}

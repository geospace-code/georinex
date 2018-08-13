/*********************************************************************/
/***  program : splname                                            ***/
/***  print batch file to split the file name into basename and    ***/
/***               and last character                              ***/
/***                                                               ***/
/***                         11 Dec. 1996 created by HATANAKA Y.   ***/
/***                         04 Jul. 2001 bug fixed  H. Y.         ***/
/*********************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

main(int argc, char *argv[]){

    char *filename,last,*p;

    if (argc != 2) {
        fprintf(stderr, "usage: %s failename",argv[1]);
        exit(1);
    }

    filename = argv[1];

    p = filename + strlen(filename) - 1;
    last = *p;
    *p = '\0';

    printf("set base=%s\n",filename);
    printf("set last=%c\n",last);
}

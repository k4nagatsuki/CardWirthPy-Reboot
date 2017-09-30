/*
 * Specialized bundle main for CardWirthPy
 */

#include <unistd.h>
#include <stdlib.h>
#include <locale.h>
#include <Python.h>

int
main(int argc, char *argv[])
{
    char *curlocale;
    FILE *boot;

    argv++;
    argc--;
    
    Py_SetProgramName(getenv("_PYTHON_EXEC"));
    Py_Initialize();
    PySys_SetArgv(argc, argv);
    PyEval_InitThreads();
    
    curlocale = setlocale(LC_ALL, NULL);
    if (curlocale != NULL) {
	curlocale = strdup(curlocale);
	if (curlocale == NULL) {
	    fprintf(stderr, "Cannot save current locale\n");
	    return -1;
	}
    }
    setlocale(LC_ALL, "ja_JP.UTF-8");
    if (getenv("LC_CTYPE")) {
	setenv("LC_CTYPE", "ja_JP.UTF-8", 1);
    }

    Py_Initialize();
    boot = fopen(argv[0], "r");
    if (boot == NULL) {
	fprintf(stderr, "Cannot open %s\n", argv[0]);
	return -1;
    }
    PyRun_SimpleFile(boot, argv[0]);
    Py_Finalize();
    fclose(boot);
    return 0;
}

#include <stdio.h>
#include <stdlib.h>

static int fib(int n) {
    if (n < 2) return n;
    return fib(n - 1) + fib(n - 2);
}

int main(int argc, char **argv) {
    int upto = (argc > 1) ? atoi(argv[1]) : 20;
    for (int i = 0; i < upto; i++) {
        printf("fib(%d) = %d\n", i, fib(i));
    }
    return 0;
}

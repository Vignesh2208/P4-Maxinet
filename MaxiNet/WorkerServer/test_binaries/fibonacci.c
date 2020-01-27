#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <math.h>
#include <unistd.h>



unsigned long fibonacci(unsigned long curr, unsigned long prev) {

  return prev + curr;
}

void main() {
  int i = 1;
  unsigned long prev = 0, curr = 1;
  int delay = 1000;
  struct timeval start_tv, end_tv;
  gettimeofday(&start_tv, NULL);

  long StartTS = start_tv.tv_sec * 1000000 + start_tv.tv_usec;
  unsigned long ret = 1;
  while (i < 1000000) {
    ret = fibonacci(curr, prev);
    prev = curr;
    curr = ret;
    i++;
  }
  gettimeofday(&end_tv, NULL);
  long EndTS = end_tv.tv_sec * 1000000 + end_tv.tv_usec;
  printf("Start Time (sec) : %lu, Event Compute Time: %lu, Elapsed: %lu\n", StartTS, EndTS, EndTS - StartTS);
  fflush(stdout);

  while (1){
  	sleep(1);
  }
}

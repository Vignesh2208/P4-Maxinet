#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <math.h>
#include <unistd.h>



unsigned long fibonacci(unsigned long curr, unsigned long prev) {

  return prev + curr;
}

unsigned long compute_millionth_fibonacci() {
  volatile int i = 1;
  volatile unsigned long prev = 0, curr = 1;
  volatile unsigned long ret = 1;
  while (i < 1000000) {
    ret = fibonacci(curr, prev);
    prev = curr;
    curr = ret;
    i++;
  }
  return curr;
}

void main() {
  volatile struct timeval start_tv, end_tv;
  volatile long threshold;
  volatile int n_computations  = 100, n_alerts = 0;
  volatile long StartTS;
  volatile long EndTS;
  volatile int i = 0;
  volatile long ElapsedTimes[100];

/*
  gettimeofday(&start_tv, NULL);
  compute_millionth_fibonacci();
  gettimeofday(&end_tv, NULL);
  StartTS = start_tv.tv_sec * 1000000 + start_tv.tv_usec;
  EndTS = end_tv.tv_sec * 1000000 + end_tv.tv_usec;

  threshold = EndTS - StartTS;
*/
  for(i = 0; i < 10; i++) {
  	compute_millionth_fibonacci();
  }

  for(i = 0; i < n_computations; i++) {
	  
	 
	  gettimeofday(&start_tv, NULL);
	  compute_millionth_fibonacci();
	  gettimeofday(&end_tv, NULL);
	  StartTS = start_tv.tv_sec * 1000000 + start_tv.tv_usec;
	  EndTS = end_tv.tv_sec * 1000000 + end_tv.tv_usec;

        if (i ==0 )
		threshold = (EndTS - StartTS);

	if((EndTS - StartTS) > threshold && (EndTS - StartTS) - threshold > 50)
		n_alerts ++;
	ElapsedTimes[i] = (EndTS - StartTS);

        //printf("Fib Computation No : %d, Elapsed: %lu, threshold: %lu\n", i, EndTS - StartTS, threshold);
        //fflush(stdout);
 	
  }

  printf("NAlerts : %d\n", n_alerts);
  for(i = 0; i < n_computations; i++) {
	printf("Fib Computation No : %d, Elapsed: %lu, threshold: %lu\n", i, ElapsedTimes[i], threshold);
        fflush(stdout);
  }
  fflush(stdout);

  while (1) {
	sleep(1);
  }
}

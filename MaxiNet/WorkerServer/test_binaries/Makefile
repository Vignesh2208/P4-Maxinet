current_dir=$(shell pwd)
EXTRA_CFLAGS += 
SUBDIR= $(shell pwd)
GCC:=gcc
RM:=rm

all:
	@gcc  client_n.c -o greeter_client -lm
	@gcc  server_n.c -o greeter_server
	@gcc  fibonacci.c -o fibonacci
	@gcc  fibonacci_new.c -O0 -o fibonacci_new
clean:
	@rm -f greeter_client
	@rm -f greeter_server
	@rm -f fibonacci
	@rm -f fibonacci_new

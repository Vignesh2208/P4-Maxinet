current_dir=$(shell pwd)
EXTRA_CFLAGS += 
SUBDIR= $(shell pwd)
GCC:=gcc
RM:=rm

all:
	@gcc  client_n.c -o greeter_client -lm
	@gcc  server_n.c -o greeter_server
clean:
	@rm -f greeter_client
	@rm -f greeter_server
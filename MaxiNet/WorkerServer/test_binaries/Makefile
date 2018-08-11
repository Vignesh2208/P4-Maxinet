current_dir=$(shell pwd)
EXTRA_CFLAGS += 
SUBDIR= $(shell pwd)
GCC:=gcc
RM:=rm

all:
	@gcc  client_n.c -o client_n -lm
	@gcc  server_n.c -o server_n
clean:
	@rm -f client_n
	@rm -f server_n
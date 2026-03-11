# -*- coding: utf-8-unix -*-

# Common makefile

# Parameters

UNIX_COMMANDS ?= ls ln cp mkdir touch false true cat grep echo

# UNAME

ifeq '$(findstring ;,$(PATH))' ';'
	UNAME := Windows
	MSYS_ROOT := $(or $(wildcard $(USERPROFILE)/scoop/apps/msys2/current),c:/msys64)
endif

ifneq ($(UNAME),Windows)
	UNAME := $(shell uname -s 2>/dev/null || echo Unknown)
	UNAME := $(patsubst CYGWIN%,Cygwin,$(UNAME))
	UNAME := $(patsubst MSYS%,MSYS,$(UNAME))
	UNAME := $(patsubst MINGW%,MSYS,$(UNAME))
endif

# Unix commands

uc = $(subst a,A,$(subst b,B,$(subst c,C,$(subst d,D,$(subst e,E,$(subst f,F,$(subst g,G,$(subst h,H,$(subst i,I,$(subst j,J,$(subst k,K,$(subst l,L,$(subst m,M,$(subst n,N,$(subst o,O,$(subst p,P,$(subst q,Q,$(subst r,R,$(subst s,S,$(subst t,T,$(subst u,U,$(subst v,V,$(subst w,W,$(subst x,X,$(subst y,Y,$(subst z,Z,$1))))))))))))))))))))))))))
ifeq ($(UNAME),Windows)
	defcmd = $(call uc,$1) := $(MSYS_ROOT)/usr/bin/$1
else
	defcmd = $(call uc,$1) := $1
endif
$(foreach p,$(UNIX_COMMANDS), $(eval $(call defcmd,$(p))))

# OS Specific

ifeq ($(UNAME),MINGW)
	MSYS := winsymlinks:nativestrict
	export MSYS
endif

ifeq ($(UNAME),Windows)
	MSYS := winsymlinks:nativestrict
	export MSYS
	RM := $(MSYS_ROOT)/usr/bin/rm.exe -f
endif

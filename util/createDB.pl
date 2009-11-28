#!/usr/bin/perl -w -I..
use strict;
use NoteSys 'createDB';

if (!@ARGV) {
 print STDERR "Usage: $0 database\n";
 exit 2;
} elsif (-e $ARGV[0]) {
 print STDERR "$0: file \"$ARGV[0]\" already exists\n";
 exit 2;
} else { createDB $ARGV[0] }

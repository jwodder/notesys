#!/usr/bin/perl -w -I..
use strict;
use NoteSys;

if (!@ARGV) {
 print STDERR "Usage: $0 database\n";
 exit 2;
}

binmode STDOUT, ':encoding(UTF-8)';
connectDB $ARGV[0];
for (getAllNoteIDs) {
 my $note = fetchNote $_;
 print "Title: ", $note->title, "\nTags: ", join(', ', @{$note->tags}), "\n";
 my($created, $edited) = getInternalDates $note->idno;
 print "Created: $created\nEdited: $edited\n";
 map { print ">$_\n" } split /\r?\n/, $note->contents if $note->contents ne '';
 print "\n";
}
disconnectDB;

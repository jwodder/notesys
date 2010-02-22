#!/usr/bin/perl -w -I..
use strict;
use NoteSys;

if (!@ARGV) {print STDERR "Usage: $0 database\n"; exit 2; }

binmode STDOUT, ':encoding(UTF-8)';
my $db = NoteSys::connect $ARGV[0];
for ($db->getAllNoteIDs) {
 my $note = $db->fetchNote($_);
 print "Title: ", $note->title, "\nTags: ", join(', ', $note->tagList), "\n";
 my($created, $edited) = $db->getInternalDates($note->idno);
 print "Created: $created\nEdited: $edited\n";
 map { print ">$_\n" } split /\r?\n/, $note->contents if $note->contents ne '';
 print "\n";
}
$db->disconnect;

#!/usr/bin/perl -Wnl
use strict;
use NoteSys qw< :DEFAULT createDB >;

BEGIN {
# my $dbfile = '/Library/WebServer/Documents/db/notes.db';
# -e $dbfile and unlink($dbfile) || die "$0: couldn't delete $dbfile: $!\n";
# createDB $dbfile;
 connect;
 $/ = '';
}

my $note = new Note title => 'Untitled', contents => '';
/^Title: (.*?)$/m && $note->title($1);
/^Tags: (.*?)$/m && $note->tags([ split ' ', $1 ]);
if (/((?:^>.*?\n?)+)$/m) {
 (my $str = $1) =~ s/^>//gm;
 $note->contents($str);
}
createNote $note;
sleep 1;

END { $? ? abandon : disconnect }

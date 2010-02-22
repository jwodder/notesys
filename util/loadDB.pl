#!/usr/bin/perl -wnl -I..
use strict;
use NoteSys;
use NoteSys::Note;

our $db;

BEGIN {
 if (!@ARGV || @ARGV == 1 && $ARGV[0] eq '-C') {
  print STDERR "Usage: $0 [-C] database [file ...]\n";
  exit 2;
 }
 if ($ARGV[0] eq '-C') {
  shift;
  if (-e $ARGV[0]) {
   print STDERR "$0: file \"$ARGV[0]\" already exists\n";
   exit 2;
  } else { NoteSys::create $ARGV[0] }
 }
 $db = NoteSys::connect shift;
 $/ = '';
}

my $note = new NoteSys::Note title => 'Untitled', contents => '';
/^Title:\s*(.*)$/im && $note->title($1);
/^Tags:\s*(.+?)\s*$/im && $note->tags([ grep {$_ ne ''} split /\s*,\s*/, $1 ]);
/^Created:\s*(.+)$/im && $note->created($1);
/^Edited:\s*(.+)$/im && $note->edited($1);
if (/((?:^>.*?\n?)+)$/m) {
 (my $str = $1) =~ s/^>//gm;
 $note->contents($str);
}
$db->createNote($note);

END { $? ? $db->abandon : $db->disconnect if defined $db }

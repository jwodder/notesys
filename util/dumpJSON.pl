#!/usr/bin/perl -w -I..
use strict;
use JSON::Syck;
use NoteSys;

$JSON::Syck::ImplicitUnicode = 1;

if (!@ARGV) {print STDERR "Usage: $0 database\n"; exit 2; }

binmode STDOUT, ':encoding(UTF-8)';
my $db = NoteSys::connect $ARGV[0];
print JSON::Syck::Dump([ map { toJSONStruct($db->fetchNote($_)) }
 $db->getAllNoteIDs ]);
$db->disconnect;

sub toJSONStruct {
 my $note = shift;
 my($created, $edited) = $db->getInternalDates($note->idno);
 return {title => $note->title, contents => $note->contents,
  created => $created, edited => $edited, tags => $note->tags,
  children => [ map { toJSONStruct($_) } $db->fetchChildren($note->idno) ]};
}

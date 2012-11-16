#!/usr/bin/perl -w -I.. -CO
use strict;
use POSIX 'strftime';
use Regexp::Common 'URI';
use NoteSys;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';

sub txt2xml($) {
 my $str = shift;
 $str =~ s/&/&amp;/g;
 $str =~ s/</&lt;/g;
 $str =~ s/>/&gt;/g;
 return $str;
}

print <<EOT;
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-export SYSTEM "http://xml.evernote.com/pub/evernote-export.dtd">
<en-export>

EOT
connectDB $dbfile;
my @notes = getAllNoteIDs;
for (@notes) {
 my $note = fetchNote($_);
 print "<note>\n";
 print " <title>", txt2xml($note->title), "</title>\n";
 print " <content><![CDATA[<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
 print "<!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\">\n";
 print "<en-note>";
 my($level, $enclist) = (-1, 0);
 for my $line (split /\r?\n/, $note->contents) {
  if ($line =~ s/^(\s*)- //) {
   $enclist = 1 if !$level;
   print STDERR "Unindented list in note #", $note->idno, "\n"
    if $level == 0 && length($1) == 0;
   my $lev2 = length($1) + !$enclist;
   if ($lev2 > $level) {
    print STDERR "Too much indentation in note #", $note->idno, "\n"
     if $lev2 > ($level == -1 ? 1 : $level + 1);
    print "<ul><li>"
   } else { print "</li></ul>" x ($level - $lev2), "</li><li>" }
   $level = $lev2;
  } else {
   print STDERR "Indented non-list item in note #", $note->idno, "\n"
    if $line =~ /^\s+/;
   print "</li></ul>" x $level if $level > 0;
   print "</div>" if $enclist || !$level;
   ($level, $enclist) = (0, 0);
   print "<div>"
  }
  $line =~ s:\G(.*?)($RE{URI})|\G(.+)$
   :if (defined $1) {
     my($pre, $url) = (txt2xml $1, txt2xml $2);
     (my $href = $url) =~ s!"!&quot;!g;
     "$pre<a href=\"$href\">$url</a>";
    } else { txt2xml $3 }
   :gex;
  if ($line eq '') {print "<br/></div>"; $level = -1; }
  else { print $line }
 }
 print "</li></ul>" x $level if $level > 0;
 print "</div>" if $enclist || !$level;
 print "</en-note>]]></content>\n";
 my($created, $edited) = getEpochDates($_);
 print " <created>", strftime('%Y%m%dT%H%M%SZ', gmtime $created),
  "</created>\n";
 print " <updated>", strftime('%Y%m%dT%H%M%SZ', gmtime $edited),
  "</updated>\n" if $created ne $edited;
 print " <tag>", txt2xml($_), "</tag>\n" for $note->tagList;
 print "</note>\n\n";
}
print "</en-export>\n";

END { $? ? abandonDB : disconnectDB }

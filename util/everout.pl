#!/usr/bin/perl -w
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

binmode STDOUT, ':encoding(UTF-8)';
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
 for my $line (split /\r?\n/, $note->contents) {
  if ($line eq '') { print "<div><br/></div>" }
  else {
   $line =~ s:\G(.*?)($RE{URI})|\G(.+)$
    :if (defined $1) {
      my($pre, $url) = (txt2xml $1, txt2xml $2);
      (my $href = $url) =~ s!"!&quot;!g;
      "$pre<a href=\"$href\">$url</a>";
     } else { txt2xml $3 }
    :gex;
   print "<div>$line</div>";
  }
 }
 print "</en-note>]]></content>";
 my($created, $edited) = getEpochDates($_);
 print " <created>", strftime('%Y%m%dT%H%M%SZ', gmtime $created),
  "</created>\n";
 print " <updated>", strftime('%Y%m%dT%H%M%SZ', gmtime $edited),
  "</updated>\n" if $created ne $edited;
 print " <tag>", txt2xml($_), "</tag>\n" for $note->tagList;
 print "</note>\n";
}
print "</en-export>\n";

END { $? ? abandonDB : disconnectDB }
